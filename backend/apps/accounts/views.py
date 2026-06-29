from __future__ import annotations

import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from apps.core.api.views import BaseAPIView
from apps.core.permissions import IsNotAuthenticated, IsVerified
from .models import User, EmailVerificationToken, PasswordResetToken
from .serializers import (
    RegisterSerializer,
    LoginSerializer,
    UserSerializer,
    EmailVerificationSerializer,
    ResendVerificationSerializer,
    PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer,
    ChangePasswordSerializer,
    ProfileUpdateSerializer,
    AvatarUploadSerializer,
)
from .tasks import (
    send_verification_email_task,
    send_password_reset_email_task,
    send_welcome_email_task,
)

logger = logging.getLogger("apps.accounts")

# ─── Cookie configuration ─────────────────────────────────────────────────────
REFRESH_COOKIE_NAME = "refresh_token"
COOKIE_SETTINGS = {
    "httponly": True,
    # "secure": not settings.DEBUG,
    "secure": True,
    "samesite": "Lax",
    "max_age": 7 * 24 * 60 * 60,  # 7 days
    "path": "/api/accounts/token/refresh/",
}


def set_refresh_cookie(response, refresh_token: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        str(refresh_token),
        **COOKIE_SETTINGS,
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=COOKIE_SETTINGS["path"],
    )


# ─── Register ─────────────────────────────────────────────────────────────────

class RegisterView(BaseAPIView):
    """
    POST /api/accounts/register/
    Create new user account and send verification email.
    """
    permission_classes = [IsNotAuthenticated]
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer= self.serializer_class(data=request.data)
        
        if not serializer.is_valid():
            return self.error_response(
                message=_("Registration failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.save()

        # create verification token and send email async
        token_obj = EmailVerificationToken.create_for_user(user)
        send_verification_email_task.delay(user.id, str(token_obj.token))

        return self.created_response(
            data={"email": user.email},
            message=_(
                "Account created successfully. "
                "Please check your email to verify your account."
            ),
        )


# ─── Email Verification ───────────────────────────────────────────────────────

class VerifyEmailView(BaseAPIView):
    """
    POST /api/accounts/verify-email/
    Verify email address using token from email link.
    """
    permission_classes = [AllowAny]
    serializer_class=EmailVerificationSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
          
        if not serializer.is_valid():
            return self.error_response(
                message=_("Invalid token."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        token_value = serializer.validated_data["token"]

        try:
            token_obj = EmailVerificationToken.objects.select_related("user").get(
                token=token_value
            )
        except EmailVerificationToken.DoesNotExist:
            return self.error_response(
                message=_("Invalid or expired verification token."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if token_obj.is_expired:
            return self.error_response(
                message=_("Verification token has expired. Request a new one."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        if user.is_verified:
            return self.success_response(
                message=_("Email already verified. You can log in."),
            )

        user.is_verified = True
        user.save(update_fields=["is_verified"])
        token_obj.delete()

        # send welcome email async
        send_welcome_email_task.delay(user.id)

        logger.info("Email verified for user: %s", user.email)

        return self.success_response(
            message=_("Email verified successfully. You can now log in."),
        )


# ─── Resend Verification ──────────────────────────────────────────────────────

class ResendVerificationView(BaseAPIView):
    """
    POST /api/accounts/resend-verification/
    Resend verification email if previous token expired.
    """
    permission_classes = [AllowAny]
    serializer_class=ResendVerificationSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
          
        if not serializer.is_valid():
            return self.error_response(
                message=_("Invalid request."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]

        # Always return success to prevent email enumeration
        try:
            user = User.objects.get(email=email)
            if not user.is_verified:
                token_obj = EmailVerificationToken.create_for_user(user)
                send_verification_email_task.delay(user.id, str(token_obj.token))
                logger.info("Verification email resent to: %s", email)
        except User.DoesNotExist:
            pass  # don't reveal if email exists

        return self.success_response(
            message=_(
                "If this email is registered and unverified, "
                "a new verification link has been sent."
            ),
        )


# ─── Login ────────────────────────────────────────────────────────────────────

class LoginView(BaseAPIView):
    """
    POST /api/accounts/login/
    Authenticate user and return JWT tokens.
    Access token in response body.
    Refresh token in HttpOnly cookie.
    """
    permission_classes = [IsNotAuthenticated]
    serializer_class=LoginSerializer
    def post(self, request):
      
        serializer = self.serializer_class(data=request.data,context={"request":request})
          
        if not serializer.is_valid():
            return self.error_response(
                message=_("Login failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        response = self.success_response(
            data={
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            message=_("Login successful."),
        )

        set_refresh_cookie(response, refresh)
        logger.info("User logged in: %s", user.email)
        return response


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutView(BaseAPIView):
    """
    POST /api/accounts/logout/
    Blacklist refresh token and clear cookie.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                logger.info("User logged out: %s", request.user.email)
            except TokenError:
                pass  # token already invalid — still clear cookie

        response = self.success_response(
            message=_("Logged out successfully."),
        )
        clear_refresh_cookie(response)
        return response


# ─── Token Refresh ────────────────────────────────────────────────────────────
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator
from rest_framework import serializers

class EmptySerializer(serializers.Serializer):
    pass
@method_decorator(ensure_csrf_cookie, name="dispatch")  
class TokenRefreshView(BaseAPIView):
    """
    POST /api/accounts/token/refresh/
    Issue new access token using refresh token from cookie.
    """
    permission_classes = [AllowAny]
    serializer_class=EmptySerializer

    def post(self, request):
        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if not refresh_token:
            return self.error_response(
                message=_("Refresh token not found."),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)

            response = self.success_response(
                data={"access": new_access},
                message=_("Token refreshed successfully."),
            )

            # rotate refresh token
            if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
                token.blacklist()
                from django.contrib.auth import get_user_model
                User = get_user_model()

                user_id = token["user_id"]
                user = User.objects.get(id=user_id)
                new_refresh = RefreshToken.for_user(user)
                set_refresh_cookie(response, new_refresh)

            return response

        except TokenError as e:
            return self.error_response(
                message=_("Invalid or expired refresh token."),
                errors=str(e),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )


# ─── Password Reset Request ───────────────────────────────────────────────────

class PasswordResetRequestView(BaseAPIView):
    """
    POST /api/accounts/password-reset/
    Send password reset email.
    """
    permission_classes = [AllowAny]
    serializer_class=PasswordResetRequestSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
          
        if not serializer.is_valid():
            return self.error_response(
                message=_("Invalid request."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        email = serializer.validated_data["email"]

        # Always return success — prevent email enumeration
        try:
            user = User.objects.get(email=email, is_active=True)
            token_obj = PasswordResetToken.create_for_user(user)
            send_password_reset_email_task.delay(user.id, str(token_obj.token))
            logger.info("Password reset requested for: %s", email)
        except User.DoesNotExist:
            pass

        return self.success_response(
            message=_(
                "If this email is registered, "
                "a password reset link has been sent."
            ),
        )


# ─── Password Reset Confirm ───────────────────────────────────────────────────

class PasswordResetConfirmView(BaseAPIView):
    """
    POST /api/accounts/password-reset/confirm/
    Reset password using token from email.
    """
    permission_classes = [AllowAny]
    serializer_class=PasswordResetConfirmSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
          
        if not serializer.is_valid():
            return self.error_response(
                message=_("Password reset failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["password"]

        try:
            token_obj = PasswordResetToken.objects.select_related("user").get(
                token=token_value
            )
        except PasswordResetToken.DoesNotExist:
            return self.error_response(
                message=_("Invalid or expired reset token."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        if not token_obj.is_valid:
            return self.error_response(
                message=_("Reset token has expired or already been used."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user
        user.set_password(new_password)
        user.save(update_fields=["password"])
        token_obj.mark_used()

        logger.info("Password reset completed for: %s", user.email)

        return self.success_response(
            message=_("Password reset successfully. You can now log in."),
        )


# ─── Profile ──────────────────────────────────────────────────────────────────

class ProfileView(BaseAPIView):
    """
    GET  /api/accounts/profile/  → get own profile
    PUT  /api/accounts/profile/  → update own profile
    """
    permission_classes = [IsAuthenticated]
    serializer_class=UserSerializer
    def get(self, request):
       
        serializer = self.serializer_class(request.user)  
        # if not serializer.is_valid():
        #     return self.error_response(
        #         message=_("Invalid request."),
        #         errors=serializer.errors,
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #     )

        return self.success_response(
            data=serializer.data,
            message=_("Profile retrieved successfully."),
        )

    def put(self, request):
        profile = request.user.profile
        serializer = ProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return self.error_response(
                message=_("Profile update failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        return self.success_response(
            data=UserSerializer(request.user).data,
            message=_("Profile updated successfully."),
        )


# ─── Change Password ──────────────────────────────────────────────────────────

class ChangePasswordView(BaseAPIView):
    """
    POST /api/accounts/change-password/
    Change password for authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class=ChangePasswordSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
              
        if not serializer.is_valid():
            return self.error_response(
                message=_("Password change failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = request.user
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        if not user.check_password(current_password):
            return self.error_response(
                message=_("Current password is incorrect."),
                errors={"current_password": _("Incorrect password.")},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        logger.info("Password changed for user: %s", user.email)

        return self.success_response(
            message=_("Password changed successfully. Please log in again."),
        )


# ─── Avatar Upload ────────────────────────────────────────────────────────────

class AvatarUploadView(BaseAPIView):
    """
    POST /api/accounts/profile/avatar/
    Upload or replace profile avatar.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class=AvatarUploadSerializer
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
          
        if not serializer.is_valid():
            return self.error_response(
                message=_("Avatar upload failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        profile = request.user.profile

        # delete old avatar from storage
        if profile.avatar:
            profile.avatar.delete(save=False)

        profile.avatar = serializer.validated_data["avatar"]
        profile.save(update_fields=["avatar"])

        logger.info("Avatar updated for user: %s", request.user.email)

        return self.success_response(
            data={"avatar_url": request.build_absolute_uri(profile.avatar.url)},
            message=_("Avatar uploaded successfully."),
        )