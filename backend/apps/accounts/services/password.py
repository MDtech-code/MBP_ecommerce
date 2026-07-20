# apps/accounts/services/password.py
from __future__ import annotations

import logging

from django.contrib.auth.hashers import check_password
from django.db import transaction

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from apps.accounts.utils.token_utils import blacklist_all_user_tokens

logger = logging.getLogger("apps.accounts")


def request_password_reset(*, email: str) -> None:
    """
    Handle a password reset request.

    Security design:
        Never raises for missing or inactive accounts.
        Silent no-op in both cases — prevents email enumeration.
        Caller always returns the same success message.

    Flow:
        1. Look up active user by email — silent no-op if not found
        2. Create PasswordResetToken
        3. Dispatch reset email task

    Args:
        email: Normalized email address from serializer.
    """
    from apps.accounts.models import PasswordResetToken, User
    from apps.accounts.tasks import send_password_reset_email_task

    log_context = {}

    # ── User lookup — silent no-op if not found or inactive ───────────────────
    try:
        user = User.objects.get(email=email, is_active=True)
    except User.DoesNotExist:
        logger.debug(
            "Password reset requested for unregistered or inactive email "
            "(silent no-op)",
            extra=log_context,
        )
        return

    log_context["user_id"] = user.id

    # ── Create token + dispatch ────────────────────────────────────────────────
    try:
        token_obj = PasswordResetToken.objects.create(user=user)
        send_password_reset_email_task.delay(user.id, str(token_obj.token))
        logger.info(
            "Password reset email dispatched",
            extra=log_context,
        )
    except Exception:
        # Log but do not raise — caller returns same message regardless.
        # Prevents attacker from using error responses to enumerate emails.
        logger.exception(
            "Failed to create reset token or dispatch password reset email",
            extra=log_context,
        )


def confirm_password_reset(
    *,
    token_value: str,
    new_password: str,
) -> None:
    """
    Complete a password reset using a reset token.

    Operation order is critical for security:
        mark_used() BEFORE set_password() — if set_password fails,
        token is already consumed. User must request a new reset.
        This prevents replay attacks on a partially failed reset.

    Phase 1 — Atomic transaction:
        1. Fetch token with select_related user
        2. Validate token (exists, not expired, not used)
        3. Mark token as used FIRST
        4. Set and save new password

    Phase 2 — After commit:
        5. Blacklist all outstanding JWT tokens

    Args:
        token_value:  UUID string from reset email link.
        new_password: Validated plain-text new password from serializer.

    Raises:
        DomainError: Token not found (400), expired (400), already used (400).
        Exception:   Any unexpected error is logged and re-raised.
    """
    from apps.accounts.models import PasswordResetToken

    log_context = {"token": str(token_value)}

    # ── Phase 1: Atomic transaction ────────────────────────────────────────────
    try:
        with transaction.atomic():

            # Step 1: Fetch token
            try:
                token_obj = (
                    PasswordResetToken.objects
                    .select_related("user")
                    .get(token=token_value)
                )
            except PasswordResetToken.DoesNotExist:
                logger.warning(
                    "Password reset confirm failed — token not found",
                    extra=log_context,
                )
                raise DomainError(
                    "Invalid or expired reset token.",
                    code=ErrorCode.TOKEN_INVALID,
                    status_code=400,
                )

            user = token_obj.user
            log_context["user_id"] = user.id

            # Step 2a: Check expiry
            if token_obj.is_expired:
                logger.warning(
                    "Password reset confirm failed — token expired",
                    extra=log_context,
                )
                raise DomainError(
                    "Reset token has expired. Please request a new one.",
                    code=ErrorCode.TOKEN_EXPIRED,
                    status_code=400,
                )

            # Step 2b: Check already used
            if token_obj.is_used:
                logger.warning(
                    "Password reset confirm failed — token already used",
                    extra=log_context,
                )
                raise DomainError(
                    "Reset token has already been used. Please request a new one.",
                    code=ErrorCode.TOKEN_INVALID,
                    status_code=400,
                )

            # Step 3: Mark used FIRST — replay attack prevention
            token_obj.mark_used()

            # Step 4: Set new password
            user.set_password(new_password)
            user.save(update_fields=["password"])

            logger.info(
                "Password reset completed successfully",
                extra=log_context,
            )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during password reset transaction — "
            "all changes rolled back.",
            extra=log_context,
        )
        raise

    # ── Phase 2: Blacklist all JWT tokens (after commit) ──────────────────────
    try:
        blacklist_all_user_tokens(user)
        logger.info(
            "All JWT tokens blacklisted after password reset",
            extra=log_context,
        )
    except Exception:
        # Non-fatal — password is already changed.
        # Existing sessions may remain briefly active until expiry.
        logger.exception(
            "Failed to blacklist JWT tokens after password reset — "
            "password changed but existing sessions may remain active.",
            extra=log_context,
        )


# def change_password(
#     *,
#     user: "User",
#     current_password: str,
#     new_password: str,
# ) -> None:
#     """
#     Change password for an authenticated user.

#     Phase 1 — Atomic transaction:
#         1. Verify current password against stored hash
#         2. Set and save new password

#     Phase 2 — After commit:
#         3. Blacklist all outstanding JWT tokens

#     Args:
#         user:             Authenticated User instance from request.
#         current_password: Plain-text current password for confirmation.
#         new_password:     Validated plain-text new password from serializer.

#     Raises:
#         DomainError: Current password incorrect (400).
#         Exception:   Any unexpected error is logged and re-raised.
#     """
#     log_context = {"user_id": user.id}

#     # ── Phase 1: Atomic transaction ────────────────────────────────────────────
#     try:
#         with transaction.atomic():

#             # Step 1: Verify current password
#             if not check_password(current_password, user.password):
#                 logger.warning(
#                     "Password change failed — incorrect current password",
#                     extra=log_context,
#                 )
#                 raise DomainError(
#                     "Current password is incorrect.",
#                     code=ErrorCode.INVALID_CREDENTIALS,
#                     status_code=400,
#                 )

#             # Step 2: Set new password
#             user.set_password(new_password)
#             user.save(update_fields=["password"])

#             logger.info(
#                 "Password changed successfully",
#                 extra=log_context,
#             )

#     except DomainError:
#         raise

#     except Exception:
#         logger.exception(
#             "Unexpected error during password change transaction — "
#             "all changes rolled back.",
#             extra=log_context,
#         )
#         raise

#     # ── Phase 2: Blacklist all JWT tokens (after commit) ──────────────────────
#     try:
#         blacklist_all_user_tokens(user)
#         logger.info(
#             "All JWT tokens blacklisted after password change",
#             extra=log_context,
#         )
#     except Exception:
#         logger.exception(
#             "Failed to blacklist JWT tokens after password change — "
#             "password changed but existing sessions may remain active.",
#             extra=log_context,
#         )