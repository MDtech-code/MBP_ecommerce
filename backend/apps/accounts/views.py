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
'''
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

def set_csrf_cookie(request, response) -> None:
    """
    Ensure csrftoken cookie is set and readable by JS.
    """
    csrf_token = get_token(request)
    response.set_cookie(
        "csrftoken",
        csrf_token,
        httponly=False,   # must be accessible to JS
        secure=True,      # True in production
        samesite="Lax",   # or "None" if cross-site frontend/backend
    )


def clear_refresh_cookie(response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=COOKIE_SETTINGS["path"],
    )

def clear_csrf_cookie(response) -> None:
    response.delete_cookie(
        "csrftoken",   # the name you used when setting it
        path="/",      # CSRF cookie is usually scoped to root
    )

'''

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

        # Django auth signal — HTTP context signal, belongs in view.
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
'''
# ─── Register ─────────────────────────────────────────────────────────────────
class RegisterView(BaseAPIView):
    """
    POST /api/accounts/register/

    Create a new user account and dispatch a verification email asynchronously.

    Permissions:
        IsNotAuthenticated — authenticated users are redirected away.

    Throttling:
        AnonRateThrottle — guards against registration spam/abuse.

    Success (201):
        Returns the registered email address.
        Verification email is dispatched via Celery.

    Errors:
        400 — Validation failure (invalid fields, duplicate email, etc.).
        403 — Already authenticated.
        500 — Unexpected server error (logged, sanitized response returned).

    Notes:
        - If token creation or task dispatch fails after the user is saved,
          the user account is NOT rolled back. The verification email can be
          resent separately. This is logged at ERROR level for investigation.
    """

    permission_classes = [IsNotAuthenticated]
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

        # ── Phase 1: Persist the user ─────────────────────────────────────
        try:
            user = serializer.save()
        except Exception:
            logger.exception(
                "Unexpected error during user creation",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "New user registered successfully",
            extra={
                **log_context,
                "user_id": user.id,
                "email": user.email,
            },
        )

        # ── Phase 2: Token creation + async email dispatch ────────────────
        # Isolated from Phase 1 — user already exists at this point.
        # Failure here does NOT roll back the account.
        # The user can request a new verification email via a separate endpoint.
        try:
            token_obj = EmailVerificationToken.objects.create(user=user)
            send_verification_email_task.delay(user.id, str(token_obj.token))
            logger.info(
                "Verification email task dispatched",
                extra={**log_context, "user_id": user.id},
            )
        except Exception:
            logger.exception(
                "Failed to dispatch verification email after registration — "
                "user account created but email not sent. Manual follow-up required.",
                extra={**log_context, "user_id": user.id, "email": user.email},
            )
            # Still return success — user was created.
            # Front-end can surface a "resend verification" option.

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

    Verify a user's email address using the token from their verification email.

    Flow:
        1. Validate token UUID format.
        2. Look up token in DB — 400 if not found.
        3. Check expiry — 400 if expired.
        4. Check if already verified — 200 early return (idempotent).
        5. Mark user as verified, delete token, dispatch welcome email.

    Permissions:
        AllowAny — token itself is the authentication mechanism.

    Success (200):
        Email marked as verified. Welcome email dispatched async.

    Errors:
        400 — Invalid format, token not found, token expired.
        500 — Unexpected DB or task failure (logged, sanitized).

    Security note:
        Token is deleted immediately on successful verification —
        one-time use enforced at the application layer.
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

        # ── Token lookup ──────────────────────────────────────────────────────
        try:
            token_obj = EmailVerificationToken.objects.select_related("user").get(
                token=token_value
            )
        except EmailVerificationToken.DoesNotExist:
            logger.warning(
                "Email verification failed — token not found",
                extra={**log_context, "token": str(token_value)},
            )
            return self.error_response(
                message=_("Invalid or expired verification token."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── Expiry check ──────────────────────────────────────────────────────
        if token_obj.is_expired:
            logger.warning(
                "Email verification failed — token expired",
                extra={**log_context, "user_id": token_obj.user.id},
            )
            return self.error_response(
                message=_("Verification token has expired. Please request a new one."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user

        # ── Already verified — idempotent success ─────────────────────────────
        # Log as warning — repeated calls may indicate a confused client
        # or a replay attempt. Not an error, but worth tracking.
        if user.is_verified:
            logger.warning(
                "Email verification called for already-verified user",
                extra={**log_context, "user_id": user.id, "email": user.email},
            )
            return self.success_response(
                message=_("Email already verified. You can log in."),
            )

        # ── Mark verified + cleanup ───────────────────────────────────────────
        # Both operations in one try block — they are one atomic unit.
        # If save() fails, token is NOT deleted (consistent state preserved).
        try:
            with transaction.atomic(): 
             token_obj.mark_used()
             user.is_verified = True
             user.save(update_fields=["is_verified"])
            #  token_obj.delete()
        except Exception:
            logger.exception(
                "Unexpected error while marking user as verified",
                extra={**log_context, "user_id": user.id, "email": user.email},
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Email verified successfully",
            extra={**log_context, "user_id": user.id, "email": user.email},
        )

        # ── Welcome email dispatch ────────────────────────────────────────────
        # Isolated from verification logic — failure here must NOT
        # roll back the verified state or return an error to the user.
        try:
            send_welcome_email_task.delay(user.id)
        except Exception:
            logger.exception(
                "Failed to dispatch welcome email after verification — "
                "user is verified but welcome email was not sent.",
                extra={**log_context, "user_id": user.id, "email": user.email},
            )

        return self.success_response(
            message=_("Email verified successfully. You can now log in."),
        )


# ─── Resend Verification ──────────────────────────────────────────────────────
class ResendVerificationView(BaseAPIView):
    """
    POST /api/accounts/resend-verification/

    Resend a verification email if the previous token expired or was lost.

    Security design:
        Always returns the same 200 response regardless of whether the email
        exists or is already verified. This prevents email enumeration attacks —
        an attacker cannot determine which emails are registered by probing
        this endpoint.

    Flow:
        1. Validate email format.
        2. Look up user — silently no-op if not found.
        3. If found and unverified → create new token, dispatch email async.
        4. If found and already verified → silently no-op.
        5. Always return the same success message.

    Permissions:
        AllowAny — unauthenticated users need this to recover from
        lost/expired verification emails.

    Success (200):
        Always returned — see security note above.
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

        email = serializer.validated_data["email"]

        # ── User lookup ───────────────────────────────────────────────────────
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Do not reveal that this email is not registered.
            # Log at DEBUG only — this is expected and frequent.
            logger.debug(
                "Resend verification requested for unregistered email",
                extra={**log_context},
                # Intentionally not logging the email itself in production
                # to avoid PII in logs. Log user_id where possible instead.
            )
            return self.success_response(
                message=_(
                    "If this email is registered and unverified, "
                    "a new verification link has been sent."
                ),
            )

        # ── Already verified — silent no-op ───────────────────────────────────
        if user.is_verified:
            logger.info(
                "Resend verification requested for already-verified user",
                extra={**log_context, "user_id": user.id},
            )
            return self.success_response(
                message=_(
                    "If this email is registered and unverified, "
                    "a new verification link has been sent."
                ),
            )

        # ── Create token + dispatch email ─────────────────────────────────────
        try:
            token_obj = EmailVerificationToken.objects.create(user=user)
            send_verification_email_task.delay(user.id, str(token_obj.token))
            logger.info(
                "Verification email resent",
                extra={**log_context, "user_id": user.id},
            )
        except Exception:
            # Log but still return success — do not reveal failure to client.
            # This prevents an attacker from using error responses to
            # determine whether an email is registered.
            logger.exception(
                "Failed to create token or dispatch verification email on resend",
                extra={**log_context, "user_id": user.id},
            )

        return self.success_response(
            message=_(
                "If this email is registered and unverified, "
                "a new verification link has been sent."
            ),
        )
'''
'''
# ─── Login ────────────────────────────────────────────────────────────────────

class LoginView(BaseAPIView):
    """
    POST /api/accounts/login/

    Authenticate user and issue JWT tokens.

    Token delivery:
        - Access token:  returned in response body (short-lived).
        - Refresh token: set in HttpOnly, Secure, SameSite=Lax cookie
          scoped to ``/api/accounts/token/`` (never accessible to JS).

    Permissions:
        IsNotAuthenticated — already-authenticated users are blocked.

    Success (200):
        Returns access token + serialized user data.

    Errors:
        400 — Invalid credentials, inactive account, unverified email.
        403 — Already authenticated.
        500 — Unexpected token generation failure (logged, sanitized).
    """

    permission_classes = [IsNotAuthenticated]
    serializer_class = LoginSerializer

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        serializer = self.serializer_class(
            data=request.data,
            context={"request": request},
        )

        if not serializer.is_valid():
            logger.warning(
                "Login validation failed",
                extra={
                    **log_context,
                    "errors": serializer.errors,
                },
            )
            # ── Log failed attempt — validation error ─────────────────────
            # Extract email best-effort — may be missing or malformed
            email_attempted = request.data.get("email", "")
            if email_attempted:
                log_login_activity(
                    request=request,
                    email=email_attempted,
                    was_successful=False,
                    failure_reason="invalid_credentials",
                )
            return self.error_response(
                message=_("Invalid email or password."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )
           

        user = serializer.validated_data["user"]
        failure_reason = serializer.validated_data.get("failure_reason", "")
        # ── Log the outcome ───────────────────────────────────────────────
        log_login_activity(
            request=request,
            email=user.email,
            was_successful=True,
            user=user,
            failure_reason="",
        )

        user_logged_in.send(
            sender=user.__class__,
            request=request,
            user=user,
        )

        # ── Token generation ──────────────────────────────────────────────────
        # Isolated in try/except — DB or JWT config failures must not
        # surface raw exceptions to the client.
        try:
            refresh = RefreshToken.for_user(user)
        except Exception:
            logger.exception(
                "Failed to generate JWT token during login",
                extra={**log_context, "user_id": user.id},
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "User logged in successfully",
            extra={
                **log_context,
                "user_id": user.id,
                "email": user.email,
            },
        )

        response = self.success_response(
            data={
                "access": str(refresh.access_token),
                "user": UserSerializer(user).data,
            },
            message=_("Login successful."),
        )

        set_refresh_cookie(response, refresh)
        set_csrf_cookie(request, response)
        return response


# ─── Logout ───────────────────────────────────────────────────────────────────

class LogoutView(BaseAPIView):
    """
    POST /api/accounts/logout/

    Blacklist the refresh token and clear the HttpOnly cookie.

    Behaviour:
        - Valid refresh token cookie present → blacklisted + cookie cleared.
        - Token already invalid/expired     → cookie still cleared.
        - No cookie present                 → cookie clear attempted, 200 returned.
        - Either way → 200 response (idempotent from client perspective).

    Permissions:
        IsAuthenticated — must be logged in to log out.

    Success (200):
        Cookie cleared, token blacklisted if present and valid.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if not refresh_token:
            # No cookie present — still return success.
            # Client may have already cleared it locally or
            # this is a retry after a previous successful logout.
            logger.warning(
                "Logout called with no refresh token cookie present",
                extra=log_context,
            )
        else:
            try:
                token = RefreshToken(refresh_token)
                token.blacklist()
                user_logged_out.send(
                    sender=request.user.__class__,
                    request=request,
                    user=request.user,
                )
                logger.info(
                    "User logged out — refresh token blacklisted",
                    extra=log_context,
                )
            except TokenError:
                # Token already expired or invalid — not an error condition.
                # Still clear the cookie so client state is clean.
                logger.warning(
                    "Logout called with already-invalid refresh token — "
                    "cookie will still be cleared",
                    extra=log_context,
                )
            except Exception:
                # Unexpected failure (e.g. DB unreachable for blacklist write).
                # Log it but still clear the cookie — partial logout is
                # better than leaving the client in a broken auth state.
                logger.exception(
                    "Unexpected error during token blacklist on logout",
                    extra=log_context,
                )

        response = self.success_response(
            message=_("Logged out successfully."),
        )
        clear_refresh_cookie(response)
        clear_csrf_cookie(response)
        return response


# ─── Token Refresh ────────────────────────────────────────────────────────────
class TokenRefreshView(BaseAPIView):
    """
    POST /api/accounts/token/refresh/

    Issue a new access token using the refresh token from the HttpOnly cookie.

    Rotation behaviour (controlled by ``SIMPLE_JWT.ROTATE_REFRESH_TOKENS``):
        - If enabled:  old refresh token blacklisted, new one set in cookie.
        - If disabled: same refresh token remains valid until natural expiry.

    Why no CSRF decorator:
        CSRF protection for HttpOnly cookie-based JWT is provided by the
        cookie's ``SameSite=Lax`` attribute — not Django's CSRF middleware.
        Adding ``ensure_csrf_cookie`` to a stateless JWT API is incorrect
        and introduces unnecessary coupling to session-based auth patterns.

    Permissions:
        AllowAny — authentication state is determined by the cookie itself,
        not by the DRF auth classes.

    Success (200):
        Returns new access token in response body.

    Errors:
        401 — No cookie present, token invalid, token expired, user deleted.
        500 — Unexpected server error during rotation (logged, sanitized).
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        log_context = {"request_id": request.id}

        refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

        if not refresh_token:
            logger.warning(
                "Token refresh attempted with no refresh cookie",
                extra=log_context,
            )
            return self.error_response(
                message=_("Refresh token not found."),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Validate incoming refresh token ───────────────────────────────────
        try:
            token = RefreshToken(refresh_token)
            new_access = str(token.access_token)

        except TokenError as exc:
            logger.warning(
                "Token refresh failed — invalid or expired token",
                extra={**log_context, "reason": str(exc)},
            )
            return self.error_response(
                message=_("Session expired. Please log in again."),
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        except Exception:
            logger.exception(
                "Unexpected error during token validation on refresh",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── Build response with new access token ──────────────────────────────
        response = self.success_response(
            data={"access": new_access},
            message=_("Token refreshed successfully."),
        )

        # ── Refresh token rotation (optional) ─────────────────────────────────
        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
            try:
                user_id = token["user_id"]
                UserModel = get_user_model()
                user = UserModel.objects.get(id=user_id)

                token.blacklist()
                new_refresh = RefreshToken.for_user(user)
                set_refresh_cookie(response, new_refresh)

                logger.info(
                    "Refresh token rotated successfully",
                    extra={**log_context, "user_id": user_id},
                )

            except UserModel.DoesNotExist:
                # Token references a deleted user — treat as invalid session.
                # Clear cookie and force re-login.
                logger.error(
                    "Token rotation failed — user not found for token claim",
                    extra={
                        **log_context,
                        "user_id": token.get("user_id"),
                    },
                )
                clear_refresh_cookie(response)
                clear_csrf_cookie(response)
                return self.error_response(
                    message=_("Session is no longer valid. Please log in again."),
                    status_code=status.HTTP_401_UNAUTHORIZED,
                )

            except Exception:
                # Rotation failed but new access token was already generated.
                # Client can continue until next refresh cycle.
                # Log for investigation but do not fail the request.
                logger.exception(
                    "Unexpected error during refresh token rotation",
                    extra={
                        **log_context,
                        "user_id": token.get("user_id"),
                    },
                )

        return response
    

'''

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
'''

# ─── Password Reset Request ───────────────────────────────────────────────────
# ─── Internal Helpers ─────────────────────────────────────────────────────────

def _blacklist_all_tokens_for_user(user: User) -> None:
    """
    Blacklist all outstanding JWT refresh tokens for a given user.

    Called after password reset and password change to invalidate
    any existing sessions across all devices.

    Args:
        user: The ``User`` whose tokens should be blacklisted.

    Note:
        Requires ``rest_framework_simplejwt.token_blacklist`` in
        ``INSTALLED_APPS``. This is already present in your project
        (confirmed by token_blacklist migrations in test output).
    """
    outstanding_tokens = OutstandingToken.objects.filter(user=user)
    for token in outstanding_tokens:
        try:
            refresh = RefreshToken(token.token)
            refresh.blacklist()
        except Exception:
            # Individual token blacklist failure — log and continue.
            # We want to blacklist as many as possible, not stop on first failure.
            logger.warning(
                "Failed to blacklist individual token during bulk invalidation",
                extra={"user_id": user.id, "token_id": token.id},
            )
# ─── Password Reset Request ───────────────────────────────────────────────────

class PasswordResetRequestView(BaseAPIView):
    """
    POST /api/accounts/password-reset/

    Send a password reset email to the given address.

    Security design:
        Always returns the same 200 response regardless of whether
        the email is registered or the account is active.
        This prevents email enumeration attacks.

    Flow:
        1. Validate email format.
        2. Look up active user — silently no-op if not found.
        3. Create reset token (invalidates previous tokens).
        4. Dispatch reset email async via Celery.
        5. Always return success message.

    Permissions:
        AllowAny — unauthenticated users need this to recover access.

    Success (200):
        Always returned — see security note above.
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

        email = serializer.validated_data["email"]

        # ── User lookup ───────────────────────────────────────────────────────
        try:
            user = User.objects.get(email=email, is_active=True)
        except User.DoesNotExist:
            # Do not reveal that this email is not registered.
            logger.debug(
                "Password reset requested for unregistered or inactive email",
                extra={**log_context},
            )
            return self.success_response(
                message=_(
                    "If this email is registered, "
                    "a password reset link has been sent."
                ),
            )

        # ── Token creation + email dispatch ──────────────────────────────────
        try:
            token_obj = PasswordResetToken.objects.create(user=user)
            send_password_reset_email_task.delay(user.id, str(token_obj.token))
            logger.info(
                "Password reset email dispatched",
                extra={**log_context, "user_id": user.id},
            )
        except Exception:
            # Log but still return success — do not reveal failure to client.
            logger.exception(
                "Failed to create reset token or dispatch email",
                extra={**log_context, "user_id": user.id},
            )

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

    Complete a password reset using the token from the reset email.

    Operation order (critical for security):
        1. Validate token format and fields.
        2. Look up token — 400 if not found.
        3. Check is_valid (not expired, not used) — 400 if invalid.
        4. Mark token as used FIRST — prevents replay attacks even if
           the subsequent password save fails.
        5. Set and save new password.
        6. Blacklist all outstanding JWT tokens — forces re-login
           on all devices with stolen sessions.

    Why mark_used before set_password:
        If set_password fails after mark_used, the token is consumed
        and the user must request a new reset — safe behaviour.
        If mark_used ran after set_password and failed, the token
        would remain valid for replay — dangerous behaviour.

    Permissions:
        AllowAny — token itself is the authentication mechanism.

    Success (200):
        Password updated. All existing sessions invalidated.

    Errors:
        400 — Invalid format, token not found, token expired or used.
        500 — Unexpected DB failure (logged, sanitized).
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

        token_value = serializer.validated_data["token"]
        new_password = serializer.validated_data["password"]

        # ── Token lookup ──────────────────────────────────────────────────────
        try:
            token_obj = PasswordResetToken.objects.select_related("user").get(
                token=token_value
            )
        except PasswordResetToken.DoesNotExist:
            logger.warning(
                "Password reset confirm failed — token not found",
                extra={**log_context, "token": str(token_value)},
            )
            return self.error_response(
                message=_("Invalid or expired reset token."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── Validity check (expiry + used) ────────────────────────────────────
        if not token_obj.is_valid:
            logger.warning(
                "Password reset confirm failed — token expired or already used",
                extra={**log_context, "user_id": token_obj.user.id},
            )
            return self.error_response(
                message=_("Reset token has expired or has already been used."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = token_obj.user

        # ── Mark used FIRST, then change password ─────────────────────────────
        # Order is critical — see class docstring for explanation.
        try:
            token_obj.mark_used()
            user.set_password(new_password)
            user.save(update_fields=["password"])
        except Exception:
            logger.exception(
                "Unexpected error during password reset save",
                extra={**log_context, "user_id": user.id},
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Password reset completed successfully",
            extra={**log_context, "user_id": user.id},
        )

        # ── Blacklist all outstanding JWT tokens ──────────────────────────────
        # Forces re-login on all devices — invalidates any stolen sessions.
        # Non-fatal — password is already changed if this fails.
        try:
            _blacklist_all_tokens_for_user(user)
            logger.info(
                "All JWT tokens blacklisted after password reset",
                extra={**log_context, "user_id": user.id},
            )
        except Exception:
            logger.exception(
                "Failed to blacklist JWT tokens after password reset — "
                "password was changed but existing sessions may remain active.",
                extra={**log_context, "user_id": user.id},
            )

        return self.success_response(
            message=_("Password reset successfully. You can now log in."),
        )


# ─── Change Password ──────────────────────────────────────────────────────────

class ChangePasswordView(BaseAPIView):
    """
    POST /api/accounts/change-password/

    Allow an authenticated user to change their own password.

    Flow:
        1. Validate new password fields.
        2. Verify current password against stored hash.
        3. Set and save new password.
        4. Blacklist all outstanding JWT tokens — forces re-login
           on all other devices with potentially stolen sessions.

    Why blacklist tokens after change:
        If an attacker had a valid refresh token (e.g. from a stolen
        session), changing the password should invalidate it.
        Without this, the attacker retains access until token expiry.

    Permissions:
        IsAuthenticated — must be logged in to change password.

    Success (200):
        Password updated. All existing sessions invalidated.

    Errors:
        400 — Validation failure, incorrect current password.
        500 — Unexpected DB failure (logged, sanitized).
    """

    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer

    def post(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

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

        user = request.user
        current_password = serializer.validated_data["current_password"]
        new_password = serializer.validated_data["new_password"]

        # ── Verify current password ───────────────────────────────────────────
        if not user.check_password(current_password):
            logger.warning(
                "Password change failed — incorrect current password",
                extra=log_context,
            )
            return self.error_response(
                message=_("Current password is incorrect."),
                errors={
            "current_password": ErrorDetail(
                _("Incorrect password."),
                code=ErrorCode.INVALID_CREDENTIALS,
            )
        },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── Save new password ─────────────────────────────────────────────────
        try:
            user.set_password(new_password)
            user.save(update_fields=["password"])
        except Exception:
            logger.exception(
                "Unexpected error during password change save",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Password changed successfully",
            extra=log_context,
        )

        # ── Blacklist all outstanding JWT tokens ──────────────────────────────
        # Forces re-login on all devices — invalidates stolen sessions.
        # Non-fatal — password is already changed if this fails.
        try:
            _blacklist_all_tokens_for_user(user)
            logger.info(
                "All JWT tokens blacklisted after password change",
                extra=log_context,
            )
        except Exception:
            logger.exception(
                "Failed to blacklist JWT tokens after password change — "
                "password was changed but existing sessions may remain active.",
                extra=log_context,
            )

        return self.success_response(
            message=_("Password changed successfully. Please log in again."),
        )
'''



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