from __future__ import annotations

import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

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
            token_obj = EmailVerificationToken.create_for_user(user)
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

# class RegisterView(BaseAPIView):
#     """
#     POST /api/accounts/register/
#     Create new user account and send verification email.
#     """
#     permission_classes = [IsNotAuthenticated]
#     serializer_class = RegisterSerializer

#     def post(self, request):
#         serializer= self.serializer_class(data=request.data)
        
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Registration failed."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         user = serializer.save()

#         # create verification token and send email async
#         token_obj = EmailVerificationToken.create_for_user(user)
#         send_verification_email_task.delay(user.id, str(token_obj.token))

#         return self.created_response(
#             data={"email": user.email},
#             message=_(
#                 "Account created successfully. "
#                 "Please check your email to verify your account."
#             ),
#         )


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
            user.is_verified = True
            user.save(update_fields=["is_verified"])
            token_obj.delete()
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

# class VerifyEmailView(BaseAPIView):
#     """
#     POST /api/accounts/verify-email/
#     Verify email address using token from email link.
#     """
#     permission_classes = [AllowAny]
#     serializer_class=EmailVerificationSerializer

#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
          
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Invalid token."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         token_value = serializer.validated_data["token"]

#         try:
#             token_obj = EmailVerificationToken.objects.select_related("user").get(
#                 token=token_value
#             )
#         except EmailVerificationToken.DoesNotExist:
#             return self.error_response(
#                 message=_("Invalid or expired verification token."),
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         if token_obj.is_expired:
#             return self.error_response(
#                 message=_("Verification token has expired. Request a new one."),
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         user = token_obj.user
#         if user.is_verified:
#             return self.success_response(
#                 message=_("Email already verified. You can log in."),
#             )

#         user.is_verified = True
#         user.save(update_fields=["is_verified"])
#         token_obj.delete()

#         # send welcome email async
#         send_welcome_email_task.delay(user.id)

#         logger.info("Email verified for user: %s", user.email)

#         return self.success_response(
#             message=_("Email verified successfully. You can now log in."),
#         )


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
            token_obj = EmailVerificationToken.create_for_user(user)
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

# class ResendVerificationView(BaseAPIView):
#     """
#     POST /api/accounts/resend-verification/
#     Resend verification email if previous token expired.
#     """
#     permission_classes = [AllowAny]
#     serializer_class=ResendVerificationSerializer
#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
          
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Invalid request."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         email = serializer.validated_data["email"]

#         # Always return success to prevent email enumeration
#         try:
#             user = User.objects.get(email=email)
#             if not user.is_verified:
#                 token_obj = EmailVerificationToken.create_for_user(user)
#                 send_verification_email_task.delay(user.id, str(token_obj.token))
#                 logger.info("Verification email resent to: %s", email)
#         except User.DoesNotExist:
#             pass  # don't reveal if email exists

#         return self.success_response(
#             message=_(
#                 "If this email is registered and unverified, "
#                 "a new verification link has been sent."
#             ),
#         )


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
            return self.error_response(
                message=_("Login failed."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        user = serializer.validated_data["user"]

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
        return response
# class LoginView(BaseAPIView):
#     """
#     POST /api/accounts/login/
#     Authenticate user and return JWT tokens.
#     Access token in response body.
#     Refresh token in HttpOnly cookie.
#     """
#     permission_classes = [IsNotAuthenticated]
#     serializer_class=LoginSerializer
#     def post(self, request):
      
#         serializer = self.serializer_class(data=request.data,context={"request":request})
          
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Login failed."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         user = serializer.validated_data["user"]
#         refresh = RefreshToken.for_user(user)

#         response = self.success_response(
#             data={
#                 "access": str(refresh.access_token),
#                 "user": UserSerializer(user).data,
#             },
#             message=_("Login successful."),
#         )

#         set_refresh_cookie(response, refresh)
#         logger.info("User logged in: %s", user.email)
#         return response


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
        return response
# class LogoutView(BaseAPIView):
#     """
#     POST /api/accounts/logout/
#     Blacklist refresh token and clear cookie.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

#         if refresh_token:
#             try:
#                 token = RefreshToken(refresh_token)
#                 token.blacklist()
#                 logger.info("User logged out: %s", request.user.email)
#             except TokenError:
#                 pass  # token already invalid — still clear cookie

#         response = self.success_response(
#             message=_("Logged out successfully."),
#         )
#         clear_refresh_cookie(response)
#         return response


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
# from django.views.decorators.csrf import ensure_csrf_cookie
# from django.utils.decorators import method_decorator
# from rest_framework import serializers

# class EmptySerializer(serializers.Serializer):
#     pass
# @method_decorator(ensure_csrf_cookie, name="dispatch")  
# class TokenRefreshView(BaseAPIView):
#     """
#     POST /api/accounts/token/refresh/
#     Issue new access token using refresh token from cookie.
#     """
#     permission_classes = [AllowAny]
#     serializer_class=EmptySerializer

#     def post(self, request):
#         refresh_token = request.COOKIES.get(REFRESH_COOKIE_NAME)

#         if not refresh_token:
#             return self.error_response(
#                 message=_("Refresh token not found."),
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#             )

#         try:
#             token = RefreshToken(refresh_token)
#             new_access = str(token.access_token)

#             response = self.success_response(
#                 data={"access": new_access},
#                 message=_("Token refreshed successfully."),
#             )

#             # rotate refresh token
#             if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS"):
#                 token.blacklist()
#                 from django.contrib.auth import get_user_model
#                 User = get_user_model()

#                 user_id = token["user_id"]
#                 user = User.objects.get(id=user_id)
#                 new_refresh = RefreshToken.for_user(user)
#                 set_refresh_cookie(response, new_refresh)

#             return response

#         except TokenError as e:
#             return self.error_response(
#                 message=_("Invalid or expired refresh token."),
#                 errors=str(e),
#                 status_code=status.HTTP_401_UNAUTHORIZED,
#             )


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
            token_obj = PasswordResetToken.create_for_user(user)
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
                errors={"current_password": _("Incorrect password.")},
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



# class PasswordResetRequestView(BaseAPIView):
#     """
#     POST /api/accounts/password-reset/
#     Send password reset email.
#     """
#     permission_classes = [AllowAny]
#     serializer_class=PasswordResetRequestSerializer
#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
          
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Invalid request."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         email = serializer.validated_data["email"]

#         # Always return success — prevent email enumeration
#         try:
#             user = User.objects.get(email=email, is_active=True)
#             token_obj = PasswordResetToken.create_for_user(user)
#             send_password_reset_email_task.delay(user.id, str(token_obj.token))
#             logger.info("Password reset requested for: %s", email)
#         except User.DoesNotExist:
#             pass

#         return self.success_response(
#             message=_(
#                 "If this email is registered, "
#                 "a password reset link has been sent."
#             ),
#         )


# # ─── Password Reset Confirm ───────────────────────────────────────────────────

# class PasswordResetConfirmView(BaseAPIView):
#     """
#     POST /api/accounts/password-reset/confirm/
#     Reset password using token from email.
#     """
#     permission_classes = [AllowAny]
#     serializer_class=PasswordResetConfirmSerializer
#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
          
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Password reset failed."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         token_value = serializer.validated_data["token"]
#         new_password = serializer.validated_data["password"]

#         try:
#             token_obj = PasswordResetToken.objects.select_related("user").get(
#                 token=token_value
#             )
#         except PasswordResetToken.DoesNotExist:
#             return self.error_response(
#                 message=_("Invalid or expired reset token."),
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         if not token_obj.is_valid:
#             return self.error_response(
#                 message=_("Reset token has expired or already been used."),
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         user = token_obj.user
#         user.set_password(new_password)
#         user.save(update_fields=["password"])
#         token_obj.mark_used()

#         logger.info("Password reset completed for: %s", user.email)

#         return self.success_response(
#             message=_("Password reset successfully. You can now log in."),
#         )

# # ─── Change Password ──────────────────────────────────────────────────────────

# class ChangePasswordView(BaseAPIView):
#     """
#     POST /api/accounts/change-password/
#     Change password for authenticated user.
#     """
#     permission_classes = [IsAuthenticated]
#     serializer_class=ChangePasswordSerializer
#     def post(self, request):
#         serializer = self.serializer_class(data=request.data)
              
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Password change failed."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         user = request.user
#         current_password = serializer.validated_data["current_password"]
#         new_password = serializer.validated_data["new_password"]

#         if not user.check_password(current_password):
#             return self.error_response(
#                 message=_("Current password is incorrect."),
#                 errors={"current_password": _("Incorrect password.")},
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         user.set_password(new_password)
#         user.save(update_fields=["password"])

#         logger.info("Password changed for user: %s", user.email)

#         return self.success_response(
#             message=_("Password changed successfully. Please log in again."),
#         )

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