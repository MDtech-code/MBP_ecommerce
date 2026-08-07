from __future__ import annotations

import logging
import time
from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in,user_logged_out
from django.middleware.csrf import get_token


from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework.exceptions import ErrorDetail
from apps.accounts.auth_strategies.registry import auth_strategy_registry
from apps.accounts.services.social_auth import login_or_register_social_user
from apps.core.error_codes import ErrorCode
from apps.core.api.views import BaseAPIView
from apps.core.permissions import IsNotAuthenticated


from apps.accounts.utils.ip_utils import (
    get_client_ip,
    get_user_agent)
from apps.accounts.utils.cookie_utils import (
    REFRESH_COOKIE_NAME,
    set_refresh_cookie,
    clear_refresh_cookie,
    set_email_cookie,
    clear_email_cookie
)
from apps.core.utils.csrf_cookie import clear_csrf_cookie
from .models import User, EmailVerificationToken, PasswordResetToken,UserProfile,UserAddress
from apps.accounts.serializers import (
    SendPhoneOTPSerializer,
    VerifyPhoneOTPSerializer,
)
from apps.accounts.services.otp_service import send_phone_otp, verify_phone_otp
from django.utils import timezone
from .services import (
    register_user,
    verify_email,
    resend_verification,
    delete_user_account,
    request_email_change,
    request_password_reset,
    confirm_password_reset,login_user,
    logout_user,
    refresh_access_token,
    get_user_profile,
    update_user_profile,
    update_user_avatar,
    get_user_addresses,
    create_user_address,
    update_user_address,
    delete_user_address,
    set_default_address,
    
    
    
    
    
    
)
from .services.security_otp import verify_security_otp,send_security_otp
from .services.change_password import change_user_password
from .services.account_deletion import delete_user_account
from apps.core.exceptions import DomainError

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
    UserAddressSerializer,
    DeleteAccountSerializer,
    EmailChangeRequestSerializer,
    EmailChangeConfirmSerializer,
    VerifySecurityOTPSerializer,
    SendSecurityOTPSerializer
)



logger = logging.getLogger("apps.accounts")


# ─── Register ──────────────────────────────────────────────────────────────────

class RegisterView(BaseAPIView):
    """
    POST /api/accounts/register/

    Permissions:
        IsNotAuthenticated — authenticated users cannot re-register.

    Throttling:
        AnonRateThrottle — guards against registration spam.

    Success (201):
        Returns registered email address.
        Verification email dispatched async via Celery.

    Errors:
        400 — Validation failure.
        409 — Email already exists (race condition).
    """

    permission_classes = [IsNotAuthenticated]
    throttle_classes = [AnonRateThrottle]
    serializer_class = RegisterSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}
        start=time.monotonic()

        serializer = self.get_serializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Registration validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Registration failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = register_user(**serializer.validated_data)
        except DomainError as exc:
            elapsed = time.monotonic() - start
            min_response_time = 0.5  # 500ms minimum
            if elapsed < min_response_time:
                time.sleep(min_response_time - elapsed)
            return self.app_error_response(exc=exc)

        logger.info(
            "New user registered successfully",
            extra={**log_context, "user_id": user.id, "email": user.email},
        )

        response= self.created_response(
            #data={"email": user.email},
            message=_(
                "Account created successfully. "
                "Please check your email to verify your account."
            ),
        )
        set_email_cookie(response,user.email)
        return response

        


# ─── Verify Email ──────────────────────────────────────────────────────────────

class VerifyEmailView(BaseAPIView):
    """
    POST /api/accounts/verify-email/

    Permissions:
        AllowAny — token itself is the authentication mechanism.

    Success (200):
        Email verified — "Email verified successfully. You can now log in."
        Already verified — "Email already verified. You can log in."

    Errors:
        400 — Invalid format, token not found, expired, already used.
    """

    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Email verification failed — invalid token format",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid token."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        token_value = serializer.validated_data["token"]

        # Service raises DomainError for all invalid token states.
        # Global exception handler converts it to the correct response.
        # Returns True (verified now) or False (already verified).
        just_verified = verify_email(token_value=token_value)

        if just_verified:
            return self.success_response(
                message=_("Email verified successfully. You can now log in."),
            )

        response=self.success_response(
            message=_("Email already verified. You can log in."),
        )
        clear_email_cookie(response)
        clear_csrf_cookie(response)
        return response


# ─── Resend Verification ───────────────────────────────────────────────────────

class ResendVerificationView(BaseAPIView):
    """
    POST /api/accounts/resend-verification/

    Security:
        Always returns the same 200 response regardless of whether
        the email exists or is already verified.
        Prevents email enumeration attacks.

    Permissions:
        AllowAny — unauthenticated users need this to recover
        from lost or expired verification emails.

    Success (200):
        Always returned. See security note above.

    Errors:
        400 — Invalid email format only.
    """

    permission_classes = [AllowAny]
    serializer_class = ResendVerificationSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Resend verification failed — invalid request data",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid request."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        resend_verification(email=serializer.validated_data["email"])

        return self.success_response(
            message=_(
                "If this email is registered and unverified, "
                "a new verification link has been sent."
            ),
        )
    


# ─── Login ─────────────────────────────────────────────────────────────────────

class LoginView(BaseAPIView):
    """
    POST /api/accounts/login/

    Authenticate user and issue JWT tokens.

    Token delivery:
        Access token:  returned in response body (short-lived).
        Refresh token: set in HttpOnly Secure SameSite=Lax cookie
                       scoped to /api/accounts/token/refresh/
                       — never accessible to JavaScript.

    Permissions:
        IsNotAuthenticated — already-authenticated users are blocked.

    Success (200):
        Returns access token + serialized user data.

    Errors:
        400 — Invalid credentials, inactive account, unverified email.
        403 — Already authenticated.
    """

    permission_classes = [IsNotAuthenticated]
    serializer_class = LoginSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Login validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid email or password."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Extract IP and user agent here — view owns request object.
        # Passed as plain strings to service — service stays transport-agnostic.
        ip_address = get_client_ip(request)
        user_agent = get_user_agent(request)

        # Service raises DomainError for all failure conditions.
        # Global exception handler converts to correct response.
        result = login_user(
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
            ip_address=ip_address,
            user_agent=user_agent,
        )

        user = result["user"]

        
        user_logged_in.send(
            sender=user.__class__,
            request=request,
            user=user,
        )

        logger.info(
            "User logged in successfully",
            extra={**log_context, "user_id": user.id},
        )

        response = self.success_response(
            data={
                "access": result["access"],
                "user": UserSerializer(user).data,
            },
            message=_("Login successful."),
        )

        set_refresh_cookie(response, result["refresh"])
        return response


# ─── Logout ────────────────────────────────────────────────────────────────────

class LogoutView(BaseAPIView):
    """
    POST /api/accounts/logout/

    Blacklist the refresh token and clear the HttpOnly cookie.

    Idempotent — always returns 200 regardless of cookie state.

    Permissions:
        IsAuthenticated — must be logged in to log out.

    Success (200):
        Cookie cleared, token blacklisted if present and valid.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        # Service handles all token blacklist logic — never raises.
        logout_user(
            refresh_token=refresh_token,
            user=request.user,
        )

        # Django auth signal — HTTP context signal, belongs in view.
        user_logged_out.send(
            sender=request.user.__class__,
            request=request,
            user=request.user,
        )

        logger.info(
            "User logged out successfully",
            extra=log_context,
        )

        response = self.success_response(
            message=_("Logged out successfully."),
        )
        clear_refresh_cookie(response)
        clear_csrf_cookie(response)
        return response


# ─── Token Refresh ─────────────────────────────────────────────────────────────

class TokenRefreshView(BaseAPIView):
    """
    POST /api/accounts/token/refresh/

    Issue a new access token using the refresh token from the HttpOnly cookie.

    Rotation behaviour (controlled by SIMPLE_JWT.ROTATE_REFRESH_TOKENS):
        Enabled:  old token blacklisted, new one set in cookie.
        Disabled: same token remains valid until natural expiry.

    Permissions:
        AllowAny — auth state determined by cookie itself.

    Success (200):
        Returns new access token in response body.

    Errors:
        400 — No cookie, token invalid, token expired, user deleted.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        # Service raises DomainError for all invalid states.
        # Global exception handler converts to correct response.
        result = refresh_access_token(refresh_token=refresh_token)

        response = self.success_response(
            data={"access": result["access"]},
            message=_("Token refreshed successfully."),
        )

        # If rotation happened — set new refresh cookie.
        # If rotation disabled — cookie unchanged.
        if result["rotation_enabled"] and result["new_refresh"]:
            set_refresh_cookie(response, result["new_refresh"])
        elif result["rotation_enabled"] and not result["new_refresh"]:
            # Rotation was attempted but failed (user deleted etc.)
            # Cookie already cleared by service raising DomainError.
            # This branch is unreachable in normal flow but guards
            # against future logic changes.
            clear_refresh_cookie(response)
            clear_csrf_cookie(response)

        logger.info(
            "Token refreshed successfully",
            extra=log_context,
        )

        return response



# ─── Password Reset Request ────────────────────────────────────────────────────

class PasswordResetRequestView(BaseAPIView):
    """
    POST /api/accounts/password-reset/

    Permissions:
        AllowAny — unauthenticated users need this to recover access.

    Security:
        Always returns same 200 response regardless of email existence.
        Prevents email enumeration attacks.

    Success (200):
        Always returned.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetRequestSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Password reset request failed — invalid data",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid request."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        request_password_reset(email=serializer.validated_data["email"])

        return self.success_response(
            message=_(
                "If this email is registered, "
                "a password reset link has been sent."
            ),
        )


# ─── Password Reset Confirm ────────────────────────────────────────────────────

class PasswordResetConfirmView(BaseAPIView):
    """
    POST /api/accounts/password-reset/confirm/

    Permissions:
        AllowAny — token itself is the authentication mechanism.

    Success (200):
        Password reset. All existing sessions invalidated.

    Errors:
        400 — Invalid token, expired, already used.
    """

    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Password reset confirm failed — validation error",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Password reset failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError for all invalid token states.
        # Global exception handler converts it to correct response.
        confirm_password_reset(
            token_value=serializer.validated_data["token"],
            new_password=serializer.validated_data["password"],
        )

        return self.success_response(
            message=_("Password reset successfully. Please log in again."),
        )

'''
# ─── Change Password ───────────────────────────────────────────────────────────

class ChangePasswordView(BaseAPIView):
    """
    POST /api/accounts/change-password/

    Permissions:
        IsAuthenticated — must be logged in.

    Success (200):
        Password changed. All existing sessions invalidated.

    Errors:
        400 — Validation failure, incorrect current password.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Password change failed — validation error",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Password change failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError if current password is wrong.
        # Global exception handler converts it to correct response.
        change_user_password(
            user=request.user,
            current_password=serializer.validated_data["current_password"],
            new_password=serializer.validated_data["new_password"],
        )

        return self.success_response(
            message=_("Password changed successfully. Please log in again."),
        )


# ─── Email Change Request ──────────────────────────────────────────────────────

class EmailChangeRequestView(BaseAPIView):
    """
    POST /api/accounts/update-email/

    Permissions:
        IsAuthenticated — must be logged in.
        # NOTE: IsVerified not enforced here.
        # Add IsVerified later if business rules require it.

    Flow:
        1. Validate new email and password format.
        2. Service verifies password, checks email availability.
        3. Service creates PendingEmailChange record.
        4. Verification email sent to new address.
        5. Security notification sent to old address.

    Success (200):
        Verification email dispatched to new address.

    Errors:
        400 — Validation failure, wrong password.
        409 — New email already taken.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = EmailChangeRequestSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Email change request failed — validation error",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Email change request failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError for wrong password or taken email.
        # Global exception handler converts it to correct response.
        request_email_change(
            user=request.user,
            new_email=serializer.validated_data["new_email"],
            password=serializer.validated_data["password"],
        )

        return self.success_response(
            message=_(
                "Verification email sent to your new address. "
                "Please verify it to complete the change."
            ),
        )


# ─── Email Change Confirm ──────────────────────────────────────────────────────

class EmailChangeConfirmView(BaseAPIView):
    """
    POST /api/accounts/update-email/confirm/

    Permissions:
        AllowAny — token itself is the authentication mechanism.

    Success (200):
        Email updated. All existing sessions invalidated.

    Errors:
        400 — Invalid token, expired, already used.
    """

    permission_classes = [AllowAny]
    serializer_class = EmailChangeConfirmSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Email change confirm failed — invalid token format",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid token."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError for all invalid token states.
        # Global exception handler converts it to correct response.
        confirm_email_change(
            token_value=serializer.validated_data["token"],
        )

        return self.success_response(
            message=_(
                "Email updated successfully. "
                "Please log in again with your new email address."
            ),
        )

'''





# ─── Profile ───────────────────────────────────────────────────────────────────

class ProfileView(BaseAPIView):
    """
    GET   /api/accounts/profile/ — Retrieve own profile.
    PATCH /api/accounts/profile/ — Partially update own profile.

    Permissions:
        IsAuthenticated — profile is private to the owner.

    GET Success (200):
        Returns full user + nested profile + addresses.

    PATCH Success (200):
        Returns full user + updated nested profile data.

    Errors:
        400 — Validation failure or profile not found.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        user = get_user_profile(user_id=request.user.id)

        logger.info("Profile retrieved", extra=log_context)

        return self.success_response(
            data=UserSerializer(user).data,
            message=_("Profile retrieved successfully."),
        )

    def patch(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = ProfileUpdateSerializer(data=request.data, partial=True)

        if not serializer.is_valid():
            logger.warning(
                "Profile update validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Profile update failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError for not found.
        # Global exception handler converts to correct response.
        user = update_user_profile(
            user_id=request.user.id,
            data=serializer.validated_data,
        )

        logger.info("Profile updated successfully", extra=log_context)

        return self.success_response(
            data=UserSerializer(user).data,
            message=_("Profile updated successfully."),
        )

    # PUT as alias for PATCH — both do partial update
    put = patch


# ─── Avatar Upload ─────────────────────────────────────────────────────────────

class AvatarUploadView(BaseAPIView):
    """
    POST /api/accounts/profile/avatar/

    Permissions:
        IsAuthenticated — only the owner can upload their avatar.

    Parsers:
        MultiPartParser + FormParser — required for file upload.

    Success (200):
        Returns absolute URL of the newly uploaded avatar.

    Errors:
        400 — File missing, invalid type, exceeds size limit.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = AvatarUploadSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Avatar upload validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Avatar upload failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service handles old avatar deletion + new avatar save.
        # Returns URL string of new avatar.
        avatar_url = update_user_avatar(
            user_id=request.user.id,
            new_avatar=serializer.validated_data["avatar"],
        )

        logger.info("Avatar updated successfully", extra=log_context)

        return self.success_response(
            data={"avatar": avatar_url},
            message=_("Avatar uploaded successfully."),
        )


# ─── Address List + Create ─────────────────────────────────────────────────────

class AddressListCreateView(BaseAPIView):
    """
    GET  /api/accounts/addresses/ — list all user addresses.
    POST /api/accounts/addresses/ — create new address.

    Permissions:
        IsAuthenticated — addresses are private to the owner.

    GET Success (200):
        Returns list of all addresses.

    POST Success (201):
        Returns newly created address.

    Errors:
        400 — Validation failure on create.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        addresses = get_user_addresses(user_id=request.user.id)
        return self.success_response(
            data=UserAddressSerializer(addresses, many=True).data,
            message=_("Addresses retrieved successfully."),
        )

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = UserAddressSerializer(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Address creation validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Address creation failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError on failure.
        # Global exception handler converts to correct response.
        address = create_user_address(
            user_id=request.user.id,
            data=serializer.validated_data,
        )

        logger.info(
            "Address created successfully",
            extra={**log_context, "address_id": address.id},
        )

        return self.created_response(
            data=UserAddressSerializer(address).data,
            message=_("Address added successfully."),
        )


# ─── Address Detail ────────────────────────────────────────────────────────────

class AddressDetailView(BaseAPIView):
    """
    PUT    /api/accounts/addresses/<id>/ — update address.
    DELETE /api/accounts/addresses/<id>/ — delete address.

    Permissions:
        IsAuthenticated — ownership enforced in service layer.

    Errors:
        400 — Address not found, validation failure.
    """

    permission_classes = [IsAuthenticated]

    def put(self, request: Request, pk: int) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = UserAddressSerializer(data=request.data, partial=True)

        if not serializer.is_valid():
            logger.warning(
                "Address update validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Address update failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError if not found or not owned.
        # Global exception handler converts to correct response.
        address = update_user_address(
            user_id=request.user.id,
            address_id=pk,
            data=serializer.validated_data,
        )

        logger.info(
            "Address updated successfully",
            extra={**log_context, "address_id": pk},
        )

        return self.success_response(
            data=UserAddressSerializer(address).data,
            message=_("Address updated successfully."),
        )

    def delete(self, request: Request, pk: int) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        # Service raises DomainError if not found or not owned.
        delete_user_address(
            user_id=request.user.id,
            address_id=pk,
        )

        logger.info(
            "Address deleted successfully",
            extra={**log_context, "address_id": pk},
        )

        return self.success_response(
            message=_("Address deleted successfully."),
        )


# ─── Address Set Default ───────────────────────────────────────────────────────

class AddressSetDefaultView(BaseAPIView):
    """
    PATCH /api/accounts/addresses/<id>/set-default/

    Permissions:
        IsAuthenticated — ownership enforced in service layer.

    Success (200):
        Returns updated address with is_default=True.

    Errors:
        400 — Address not found or not owned.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        # Service raises DomainError if not found or not owned.
        address = set_default_address(
            user_id=request.user.id,
            address_id=pk,
        )

        logger.info(
            "Default address set successfully",
            extra={**log_context, "address_id": pk},
        )

        return self.success_response(
            data=UserAddressSerializer(address).data,
            message=_("Default address updated."),
        )

# ─── Delete Account ────────────────────────────────────────────────────────────
'''
class DeleteAccountView(BaseAPIView):
    """
    DELETE /api/accounts/me/delete/

    Hard delete the authenticated user's own account.

    Permissions:
        IsAuthenticated — user must be logged in.
        # NOTE: IsVerified not enforced here by design.
        # Unverified users should also be able to delete their account.
        # Add IsVerified here later if business rules change.

    Flow:
        1. Validate password confirmation format.
        2. Service validates password correctness.
        3. Service hard deletes user (CASCADE handles related data).
        4. Service dispatches goodbye email task.
        5. Return 200 confirmation.

    Success (200):
        Account deleted. Goodbye email dispatched async.

    Errors:
        400 — Password field missing or blank.
        400 — Incorrect password confirmation.
    """

    permission_classes = [IsAuthenticated]
    serializer_class = DeleteAccountSerializer

    def delete(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            logger.warning(
                "Account deletion failed — invalid request data",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Password confirmation is required."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Service raises DomainError if password is incorrect.
        # Global exception handler converts it to correct response.
        delete_user_account(
            user=request.user,
            password=serializer.validated_data["password"],
        )

        logger.info(
            "User account deleted successfully",
            extra=log_context,
        )

        return self.success_response(
            message=_(
                "Your account has been permanently deleted. "
                "We are sad to see you go. "
                "You are always welcome back."
            ),
        )
    
'''

# ─── Social login ─────────────────────────────────────────────────────









class SocialAuthView(BaseAPIView):
    """
    POST /api/accounts/auth/social/

    Universal social authentication endpoint.
    One URL handles all providers — provider determined by request body.

    Request:
        {
            "provider": "google" | "facebook",
            "token":    "<token_from_frontend>"
        }

    Success 200:
        {
            "access":  "<jwt_access_token>",
            "refresh": "<jwt_refresh_token>"
        }

    Errors:
        400 — Missing fields, invalid token, unsupported provider,
              email not provided by Facebook, account inactive.
    """

    permission_classes = [IsNotAuthenticated]
    throttle_classes   = [AnonRateThrottle]

    def post(self, request: Request):
        log_context = {"request_id": getattr(request, "id", None)}

        provider = request.data.get("provider", "").strip().lower()
        token    = request.data.get("token", "").strip()

        if not provider or not token:
            return self.error_response(
                message=_("Both 'provider' and 'token' fields are required."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        
        strategy    = auth_strategy_registry.get(provider)
        social_data = strategy.authenticate(token)
        user        = login_or_register_social_user(social_data)
        refresh = RefreshToken.for_user(user)

        logger.info(
            "Social auth success",
            extra={
                **log_context,
                "provider": provider,
                "user_id":  user.id,
            },
        )

        # ── Build response — mirrors email/password login exactly ──────────────
        response = self.success_response(
            data={"access": str(refresh.access_token),"user": UserSerializer(user).data,},
            
            message=_("Authentication successful."),
        )

        # Refresh token in HttpOnly cookie — never in response body
        set_refresh_cookie(response, str(refresh))

        return response
    


# apps/accounts/views.py — security views section

from apps.accounts.services.security_otp import (
    send_security_otp,
    verify_security_otp,
)
from apps.accounts.services.email_change import (
    request_email_change,
    confirm_email_change_otp,
)
from apps.accounts.services.change_password import change_user_password
from apps.accounts.services.account_deletion import delete_user_account


# ─── Send Security OTP ────────────────────────────────────────────────────────

class SendSecurityOTPView(BaseAPIView):
    """
    POST /api/accounts/security/send-otp/

    Sends 6-digit OTP to user's current email.
    Enforces 60-second resend cooldown.

    Permissions: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    throttle_classes   = [AnonRateThrottle]
    serializer_class   = SendSecurityOTPSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message=_("Invalid request."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        masked_email = send_security_otp(
            user    = request.user,
            purpose = serializer.validated_data["purpose"],
        )

        logger.info(
            "Security OTP sent",
            extra={**log_context, "purpose": serializer.validated_data["purpose"]},
        )

        return self.success_response(
            data    = {"masked_email": masked_email},
            message = _("Verification code sent to your email address."),
        )


# ─── Verify Security OTP ──────────────────────────────────────────────────────

class VerifySecurityOTPView(BaseAPIView):
    """
    POST /api/accounts/security/verify-otp/

    Verifies OTP and returns verification_token for sensitive action.

    Permissions: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = VerifySecurityOTPSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message=_("Invalid request."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        verification_token = verify_security_otp(
            user     = request.user,
            purpose  = serializer.validated_data["purpose"],
            otp_code = serializer.validated_data["otp_code"],
        )

        logger.info(
            "Security OTP verified",
            extra={**log_context, "purpose": serializer.validated_data["purpose"]},
        )

        return self.success_response(
            data    = {"verification_token": verification_token},
            message = _("Identity verified successfully."),
        )


# ─── Change Password ───────────────────────────────────────────────────────────

class ChangePasswordView(BaseAPIView):
    """
    POST /api/accounts/change-password/

    Requires verification_token from OTP gate.
    No current_password needed — identity proven via OTP.

    Permissions: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = ChangePasswordSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Password change failed — validation error",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Password change failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        change_user_password(
            user               = request.user,
            new_password       = serializer.validated_data["new_password"],
            verification_token = str(serializer.validated_data["verification_token"]),
        )

        return self.success_response(
            message=_("Password changed successfully. Please log in again."),
        )


# ─── Email Change Request ──────────────────────────────────────────────────────

class EmailChangeRequestView(BaseAPIView):
    """
    POST /api/accounts/update-email/

    Requires verification_token from OTP gate.
    Sends OTP to new email address.

    Permissions: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = EmailChangeRequestSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Email change request failed — validation error",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Email change request failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        masked_new_email = request_email_change(
            user               = request.user,
            new_email          = serializer.validated_data["new_email"],
            verification_token = str(serializer.validated_data["verification_token"]),
        )

        return self.success_response(
            data    = {"masked_new_email": masked_new_email},
            message = _(
                "Verification code sent to your new email address. "
                "Enter the code to complete the change."
            ),
        )


# ─── Email Change Confirm ──────────────────────────────────────────────────────

class EmailChangeConfirmView(BaseAPIView):
    """
    POST /api/accounts/update-email/confirm/

    User enters OTP received at new email address.
    IsAuthenticated — user still has valid JWT here.
    Tokens blacklisted AFTER confirmation inside service.

    Permissions: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = EmailChangeConfirmSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Email change confirm failed — invalid input",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid verification code."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        confirm_email_change_otp(
            user     = request.user,
            otp_code = serializer.validated_data["otp_code"],
        )

        return self.success_response(
            message=_(
                "Email updated successfully. "
                "Please log in again with your new email address."
            ),
        )


# ─── Delete Account ────────────────────────────────────────────────────────────

class DeleteAccountView(BaseAPIView):
    """
    DELETE /api/accounts/me/delete/

    Requires verification_token from OTP gate.
    No password field — identity proven via OTP.

    Permissions: IsAuthenticated
    """
    permission_classes = [IsAuthenticated]
    serializer_class   = DeleteAccountSerializer

    def delete(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Account deletion failed — invalid request data",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Verification token is required."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        delete_user_account(
            user               = request.user,
            verification_token = str(serializer.validated_data["verification_token"]),
        )

        logger.info("User account deleted successfully", extra=log_context)

        return self.success_response(
            message=_(
                "Your account has been permanently deleted. "
                "We are sad to see you go. "
                "You are always welcome back."
            ),
        )




class SendPhoneOTPView(BaseAPIView):
    """
    POST /api/accounts/profile/phone/send-otp/

    Send a 6-digit OTP to the given phone number.
    Stores OTP in cache — valid for 5 minutes.

    Permissions: IsAuthenticated
    """

    permission_classes = [IsAuthenticated]
    serializer_class   = SendPhoneOTPSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Send OTP failed — invalid input",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid phone number."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        phone = serializer.validated_data["phone"]

        result = send_phone_otp(user_id=request.user.pk, phone=phone)

        logger.info(
            "OTP sent successfully",
            extra={**log_context, "phone": phone},
        )

        return self.success_response(
            data=result,
            message=_("OTP sent successfully."),
        )


class VerifyPhoneOTPView(BaseAPIView):
    """
    POST /api/accounts/profile/phone/verify-otp/

    Verify the OTP and mark phone as verified on the profile.
    On success — writes phone, is_phone_verified=True, phone_verified_at.

    Permissions: IsAuthenticated
    """

    permission_classes = [IsAuthenticated]
    serializer_class   = VerifyPhoneOTPSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id, "user_id": request.user.id}

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Verify OTP failed — invalid input",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Invalid request data."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        phone = serializer.validated_data["phone"]
        otp   = serializer.validated_data["otp"]

        success, error_msg = verify_phone_otp(
            user_id=request.user.pk,
            phone=phone,
            otp=otp,
        )

        if not success:
            # OTP expired / wrong code / phone mismatch — domain rule, not input error
            raise DomainError(
                error_msg,
                code=ErrorCode.OTP_INVALID,
                status_code=400,
            )

        UserProfile.objects.filter(user=request.user).update(
            phone=phone,
            is_phone_verified=True,
            phone_verified_at=timezone.now(),
        )

        logger.info(
            "Phone verified successfully",
            extra={**log_context, "phone": phone},
        )

        return self.success_response(
            message=_("Phone number verified successfully."),
        )