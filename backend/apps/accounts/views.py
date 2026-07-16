from __future__ import annotations

import logging

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
    set_csrf_cookie,
    clear_csrf_cookie,
)
from .models import User, EmailVerificationToken, PasswordResetToken,UserProfile,UserAddress

from .services import (
    register_user,
    verify_email,
    resend_verification,
    delete_user_account,
    request_email_change,
    request_password_reset,
    confirm_email_change,confirm_password_reset,change_password,login_user,
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
    EmailChangeConfirmSerializer
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

    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]
    serializer_class = RegisterSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(data=request.data)

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

        user = register_user(**serializer.validated_data)

        logger.info(
            "New user registered successfully",
            extra={**log_context, "user_id": user.id, "email": user.email},
        )

        return self.created_response(
            data={"email": user.email},
            message=_(
                "Account created successfully. "
                "Please check your email to verify your account."
            ),
        )


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

        return self.success_response(
            message=_("Email already verified. You can log in."),
        )


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
        set_csrf_cookie(request, response)
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
        change_password(
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





# ─── Profile ──────────────────────────────────────────────────────────────────



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
class ProfileView(BaseAPIView):
    """
    GET   /api/accounts/profile/ → Retrieve own profile.
    PATCH /api/accounts/profile/ → Partially update own profile.

    Why PATCH not PUT:
        All profile fields are optional on update — clients send only
        what they want to change. PUT semantics require all fields.
        PATCH is the correct verb for partial updates.

    Why select_related("profile"):
        UserSerializer accesses user.profile (OneToOne).
        Without select_related, every GET/PATCH causes a separate
        DB query for the profile — avoidable N+1 per request.

    Permissions:
        IsAuthenticated — profile is private to the owner.

    GET Success (200):
        Returns full user + nested profile data.

    PATCH Success (200):
        Returns full user + updated nested profile data.

    Errors:
        400 — Validation failure on update.
        500 — Unexpected DB failure on save (logged, sanitized).
    """

    permission_classes = [IsAuthenticated]


    def _get_user_with_profile_address(self, user_id: int) -> User:
        """
        Fetch user with profile and address in a single JOIN query.

        Args:
            user_id: PK of the user to fetch.

        Returns:
            ``User`` instance with ``profile`` & ``useraddress`` pre-fetched.
        """
        return (
            User.objects
            .select_related("profile")
            .prefetch_related("addresses")
            .get(pk=user_id)
        )
    def _get_user_with_profile(self, user_id: int) -> User:
        """
        Fetch user with profile  in a single JOIN query.

        Args:
            user_id: PK of the user to fetch.

        Returns:
            ``User`` instance with ``profile``  pre-fetched.
        """
        return (
            User.objects
            .select_related("profile")
            .get(pk=user_id)
        )

    

    def get(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        try:
            user = self._get_user_with_profile_address(request.user.id)
        except Exception:
            logger.exception(
                "Unexpected error fetching profile",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Profile retrieved",
            extra=log_context,
        )

        serializer = UserSerializer(user)
        return self.success_response(
            data=serializer.data,
            message=_("Profile retrieved successfully."),
        )

    def patch(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        # ── Fetch profile safely ──────────────────────────────────────────────
        try:
            user = self._get_user_with_profile(request.user.id)
            profile = user.profile
        except UserProfile.DoesNotExist:
            # Should never happen — signal creates profile on user creation.
            # If it does, the signal failed silently — log at ERROR level.
            logger.error(
                "Profile not found for authenticated user — "
                "signal may have failed on account creation.",
                extra=log_context,
            )
            return self.error_response(
                message=_("Profile not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )
        except Exception:
            logger.exception(
                "Unexpected error fetching profile for update",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Validate input ────────────────────────────────────────────────────
        serializer = ProfileUpdateSerializer(
            profile,
            data=request.data,
            partial=True,
        )

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

        # ── Save ──────────────────────────────────────────────────────────────
        try:
            serializer.save()

        except Exception:
            logger.exception(
                "Unexpected error saving profile update",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Profile updated successfully",
            extra=log_context,
        )

        # Re-fetch to ensure response reflects saved state
        user = self._get_user_with_profile_address(request.user.id)
        return self.success_response(
            data=UserSerializer(user).data,
            message=_("Profile updated successfully."),
        )

    # Support PUT as alias for PATCH — both do partial update
    put = patch







class AddressListCreateView(BaseAPIView):
    """
    GET  /api/accounts/addresses/        — list all user addresses
    POST /api/accounts/addresses/        — create new address
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        addresses = request.user.addresses.all()
        serializer = UserAddressSerializer(addresses, many=True)
        return self.success_response(data=serializer.data)

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = UserAddressSerializer(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            return self.error_response(
                message=_("Address creation failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save(user=request.user)

        logger.info(
            "Address created",
            extra={**log_context, "user_id": request.user.id},
        )

        return self.success_response(
            data=serializer.data,
            message=_("Address added successfully."),
            status_code=status.HTTP_201_CREATED,
        )


class AddressDetailView(BaseAPIView):
    """
    PUT    /api/accounts/addresses/<id>/   — update address
    DELETE /api/accounts/addresses/<id>/   — delete address
    PATCH  /api/accounts/addresses/<id>/set-default/ — set as default
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        """
        Fetch address — enforce ownership.
        User can only touch their own addresses.
        """
        try:
            return request.user.addresses.get(pk=pk)
        except UserAddress.DoesNotExist:
            return None

    def put(self, request: Request, pk: int) -> Response:
        address = self.get_object(request, pk)
        if not address:
            return self.error_response(
                message=_("Address not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        serializer = UserAddressSerializer(
            address,
            data=request.data,
            partial=True,
            context={"request": request},
        )

        if not serializer.is_valid():
            return self.error_response(
                message=_("Address update failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()

        return self.success_response(
            data=serializer.data,
            message=_("Address updated successfully."),
        )

    def delete(self, request: Request, pk: int) -> Response:
        address = self.get_object(request, pk)
        if not address:
            return self.error_response(
                message=_("Address not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        address.delete()

        return self.success_response(
            message=_("Address deleted successfully."),
        )


class AddressSetDefaultView(BaseAPIView):
    """
    PATCH /api/accounts/addresses/<id>/set-default/
    Sets the specified address as the user default.
    """

    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        try:
            address = request.user.addresses.get(pk=pk)
        except UserAddress.DoesNotExist:
            return self.error_response(
                message=_("Address not found."),
                status_code=status.HTTP_404_NOT_FOUND,
            )

        address.set_as_default()

        return self.success_response(
            data=UserAddressSerializer(address).data,
            message=_("Default address updated."),
        )


# ─── Avatar Upload ────────────────────────────────────────────────────────────
class AvatarUploadView(BaseAPIView):
    """
    POST /api/accounts/profile/avatar/

    Upload or replace the authenticated user's profile avatar.

    Flow:
        1. Validate file (size ≤ 2MB, type: JPEG/PNG/WebP).
        2. Delete old avatar from storage if present.
        3. Save new avatar to profile.
        4. Return absolute URL of new avatar.

    Why delete before save:
        Storage backends (S3, local) accumulate orphaned files if
        old avatar is not explicitly deleted before replacement.
        We delete first to keep storage clean.

    Why old avatar deletion is non-fatal:
        File may already be missing from storage (manual cleanup,
        S3 lifecycle policy, etc.). We log the failure and continue
        — a missing old file must not block the new upload.

    Permissions:
        IsAuthenticated — only the owner can upload their avatar.

    Parsers:
        MultiPartParser + FormParser — required for file upload.

    Success (200):
        Returns absolute URL of the newly uploaded avatar.

    Errors:
        400 — File missing, invalid type, exceeds size limit.
        500 — Unexpected DB or storage failure (logged, sanitized).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = AvatarUploadSerializer

    def post(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        # ── Validate uploaded file ────────────────────────────────────────────
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

        profile = request.user.profile
        new_avatar = serializer.validated_data["avatar"]

        # ── Delete old avatar from storage ────────────────────────────────────
        # Non-fatal — missing file must not block the new upload.
        if profile.avatar:
            try:
                profile.avatar.delete(save=False)
            except Exception:
                logger.warning(
                    "Failed to delete old avatar from storage — "
                    "proceeding with new upload. Manual cleanup may be needed.",
                    extra={**log_context, "old_avatar": str(profile.avatar)},
                )

        # ── Save new avatar ───────────────────────────────────────────────────
        try:
            profile.avatar = new_avatar
            profile.save(update_fields=["avatar"])
        except Exception:
            logger.exception(
                "Unexpected error saving new avatar to profile",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Avatar updated successfully",
            extra=log_context,
        )

        return self.success_response(
            data={"avatar": profile.avatar.url},
            message=_("Avatar uploaded successfully."),
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