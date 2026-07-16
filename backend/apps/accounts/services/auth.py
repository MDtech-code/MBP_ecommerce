# apps/accounts/services/auth.py
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from django.conf import settings

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

from apps.accounts.utils.ip_utils import log_login_activity

logger = logging.getLogger("apps.accounts")


def login_user(
    *,
    email: str,
    password: str,
    ip_address: str | None,
    user_agent: str,
) -> dict[str, Any]:
    """
    Authenticate user and generate JWT tokens.

    Responsibility:
        - Authenticate credentials
        - Check account is active
        - Check email is verified
        - Log login activity (success and failure)
        - Generate and return access + refresh tokens

    Why ip_address and user_agent as arguments?
        Service layer has zero dependency on request object.
        View extracts these before calling service and passes
        as plain strings — keeps service transport-agnostic
        and independently testable without HTTP context.

    Flow:
        1. Authenticate credentials via Django authenticate()
        2. Check is_active
        3. Check is_verified
        4. Log activity
        5. Generate JWT tokens

    Args:
        email:      Normalized email from serializer.
        password:   Plain-text password from serializer.
        ip_address: Client IP extracted from request by view.
        user_agent: User agent string extracted from request by view.

    Returns:
        dict with keys:
            user:    Authenticated User instance.
            access:  Access token string.
            refresh: RefreshToken instance (for cookie).

    Raises:
        DomainError: Invalid credentials (400).
        DomainError: Account inactive (400).
        DomainError: Email not verified (400).
        DomainError: Token generation failed (400).
    """

    #! ── Step 1: Authenticate credentials ──────────────────────────────────────
    
    user = authenticate(username=email, password=password)

    if user is None:
        log_login_activity(
            email=email,
            was_successful=False,
            ip_address=ip_address,
            user_agent=user_agent,
            failure_reason=ErrorCode.INVALID_CREDENTIALS,
        )
        logger.warning(
            "Login failed — invalid credentials",
            extra={"email": email, "ip_address": ip_address},
        )
        raise DomainError(
            "Invalid email or password.",
            code=ErrorCode.INVALID_CREDENTIALS,
            status_code=400,
        )

    #! ── Step 2: Account active check ───────────────────────────────────────────
    if not user.is_active:
        log_login_activity(
            email=email,
            was_successful=False,
            ip_address=ip_address,
            user_agent=user_agent,
            user=user,
            failure_reason=ErrorCode.ACCOUNT_INACTIVE,
        )
        logger.warning(
            "Login failed — account inactive",
            extra={"user_id": user.id, "email": email},
        )
        raise DomainError(
            "Your account has been deactivated. Please contact support.",
            code=ErrorCode.ACCOUNT_INACTIVE,
            status_code=400,
        )

    #! ── Step 3: Email verified check ───────────────────────────────────────────
    if not user.is_verified:
        log_login_activity(
            email=email,
            was_successful=False,
            ip_address=ip_address,
            user_agent=user_agent,
            user=user,
            failure_reason=ErrorCode.EMAIL_NOT_VERIFIED,
        )
        logger.warning(
            "Login failed — email not verified",
            extra={"user_id": user.id, "email": email},
        )
        raise DomainError(
            "Please verify your email address before logging in.",
            code=ErrorCode.EMAIL_NOT_VERIFIED,
            status_code=400,
        )

    #! ── Step 4: Log successful login ───────────────────────────────────────────
    log_login_activity(
        email=email,
        was_successful=True,
        ip_address=ip_address,
        user_agent=user_agent,
        user=user,
        failure_reason="",
    )

    #! ── Step 5: Generate JWT tokens ────────────────────────────────────────────
    try:
        refresh = RefreshToken.for_user(user)
    except Exception:
        logger.exception(
            "Failed to generate JWT token during login",
            extra={"user_id": user.id},
        )
        raise DomainError(
            "An unexpected error occurred. Please try again later.",
            code=ErrorCode.SERVER_ERROR,
            status_code=400,
        )

    logger.info(
        "User logged in successfully",
        extra={"user_id": user.id, "email": email},
    )

    return {
        "user": user,
        "access": str(refresh.access_token),
        "refresh": refresh,
    }


def logout_user(*, refresh_token: str | None, user) -> None:
    """
    Blacklist refresh token on logout.

    Non-fatal by design:
        Missing, expired, or already-invalid tokens are not errors.
        Cookie is always cleared by the view regardless of outcome here.

    Args:
        refresh_token: Raw token string from cookie. None if cookie missing.
        user:          Authenticated User instance from request.
    """
    log_context = {"user_id": user.id}

    if not refresh_token:
        logger.warning(
            "Logout called with no refresh token cookie",
            extra=log_context,
        )
        return

    try:
        token = RefreshToken(refresh_token)
        token.blacklist()
        logger.info(
            "Refresh token blacklisted on logout",
            extra=log_context,
        )
    except TokenError:
        # Already expired or invalid — not an error condition.
        # Cookie will still be cleared by view.
        logger.warning(
            "Logout called with already-invalid refresh token — "
            "cookie will still be cleared",
            extra=log_context,
        )
    except Exception:
        # Unexpected failure — log but do not raise.
        # Partial logout is better than broken auth state.
        logger.exception(
            "Unexpected error during token blacklist on logout",
            extra=log_context,
        )


def refresh_access_token(
    *,
    refresh_token: str | None,
) -> dict[str, Any]:
    """
    Validate refresh token and issue new access token.

    Handles optional token rotation if ROTATE_REFRESH_TOKENS is enabled.

    Args:
        refresh_token: Raw token string from cookie.

    Returns:
        dict with keys:
            access:           New access token string.
            new_refresh:      New RefreshToken instance if rotated, else None.
            rotation_enabled: bool — True if rotation happened.

    Raises:
        DomainError: No token provided (401).
        DomainError: Token invalid or expired (401).
        DomainError: User not found for token claim (401).
    """
    log_context = {}

    # ── No cookie present ──────────────────────────────────────────────────────
    if not refresh_token:
        logger.warning("Token refresh attempted with no refresh cookie")
        raise DomainError(
            "Refresh token not found.",
            code=ErrorCode.TOKEN_INVALID,
            status_code=400,
        )

    # ── Validate token ─────────────────────────────────────────────────────────
    try:
        token = RefreshToken(refresh_token)
        new_access = str(token.access_token)
    except TokenError as exc:
        logger.warning(
            "Token refresh failed — invalid or expired token",
            extra={"reason": str(exc)},
        )
        raise DomainError(
            "Session expired. Please log in again.",
            code=ErrorCode.TOKEN_EXPIRED,
            status_code=400,
        )
    except Exception:
        logger.exception("Unexpected error during token validation on refresh")
        raise DomainError(
            "An unexpected error occurred. Please try again later.",
            code=ErrorCode.SERVER_ERROR,
            status_code=400,
        )

    # ── Token rotation (optional) ──────────────────────────────────────────────
    rotation_enabled = settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS", False)
    new_refresh = None

    if rotation_enabled:
        try:
            user_id = token["user_id"]
            log_context["user_id"] = user_id

            UserModel = get_user_model()
            user = UserModel.objects.get(id=user_id)

            token.blacklist()
            new_refresh = RefreshToken.for_user(user)

            logger.info(
                "Refresh token rotated successfully",
                extra=log_context,
            )

        except UserModel.DoesNotExist:
            logger.error(
                "Token rotation failed — user not found for token claim",
                extra={"user_id": token.get("user_id")},
            )
            raise DomainError(
                "Session is no longer valid. Please log in again.",
                code=ErrorCode.TOKEN_INVALID,
                status_code=400,
            )

        except Exception:
            # Rotation failed but new access token was already generated.
            # Client can continue until next refresh cycle.
            # Log for investigation — do not fail the request.
            logger.exception(
                "Unexpected error during refresh token rotation",
                extra=log_context,
            )

    return {
        "access": new_access,
        "new_refresh": new_refresh,
        "rotation_enabled": rotation_enabled,
    }