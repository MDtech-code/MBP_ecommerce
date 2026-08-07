# apps/accounts/services/email_verification.py
from __future__ import annotations

import logging

from django.db import transaction
from apps.accounts.models import EmailVerificationToken
from apps.accounts.tasks import send_welcome_email_task
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.accounts")


def verify_email(*, token_value: str) -> bool:
    """
    Verify a user's email address using a verification token.

    Responsibility:
        Owns the complete email verification transaction.
        Marks the token as used and the user as verified atomically.
        Dispatches welcome email after commit.

    Returns:
        True  — user was just verified now (first time)
        False — user was already verified before this call (idempotent)

    This return value lets the view send the correct message:
        True  → "Email verified successfully. You can now log in."
        False → "Email already verified. You can log in."

    Phase 1 — Atomic transaction:
        1. Fetch token with select_related user
        2. Validate token (exists, not expired, not used)
        3. Check already verified — return False immediately (no DB writes)
        4. Mark token as used
        5. Mark user as verified

    Phase 2 — After commit (only when True):
        6. Dispatch welcome email task

    Args:
        token_value: UUID string submitted by the user.

    Raises:
        DomainError: Token not found (400), expired (400), already used (400).
        Exception:   Any unexpected error is logged and re-raised.
    """


    log_context = {"token": str(token_value)}

    # ── Phase 1: Atomic transaction ────────────────────────────────────────────
    try:
        with transaction.atomic():

            #! Step 1: Fetch token
            try:
                token_obj = (
                    EmailVerificationToken.objects
                    .select_related("user")
                    .get(token=token_value)
                )
            except EmailVerificationToken.DoesNotExist:
                logger.warning(
                    "Email verification failed — token not found",
                    extra=log_context,
                )
                raise DomainError(
                    "Invalid or expired verification token.",
                    code=ErrorCode.TOKEN_INVALID,
                    status_code=400,
                )

            user = token_obj.user
            log_context["user_id"] = user.id

            #! Step 2a: Check expiry
            if token_obj.is_expired:
                logger.warning(
                    "Email verification failed — token expired",
                    extra=log_context,
                )
                raise DomainError(
                    "Verification token has expired. Please request a new one.",
                    code=ErrorCode.TOKEN_EXPIRED,
                    status_code=400,
                )

            #! Step 2b: Check already used
            if token_obj.is_used:
                logger.warning(
                    "Email verification failed — token already used",
                    extra=log_context,
                )
                raise DomainError(
                    "This verification token has already been used.",
                    code=ErrorCode.TOKEN_INVALID,
                    status_code=400,
                )

            #! Step 2c: Already verified 
            if user.is_verified:
                logger.warning(
                    "Verification called for already-verified user",
                    extra=log_context,
                )
                return False

            #! Step 3: Mark token as used
            token_obj.mark_used()

            #! Step 4: Mark user as verified
            user.is_verified = True
            user.save(update_fields=["is_verified"])

            logger.info(
                "User email verified successfully",
                extra=log_context,
            )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during email verification transaction — "
            "all changes rolled back.",
            extra=log_context,
        )
        raise

    # ── Phase 2: Task dispatch (after commit, only on first verification) ──────
    try:
        send_welcome_email_task.delay(user.id)
        logger.info(
            "Welcome email task dispatched",
            extra=log_context,
        )
    except Exception:
        logger.exception(
            "Failed to dispatch welcome email — "
            "user is verified but welcome email not sent.",
            extra=log_context,
        )

    return True


def resend_verification(*, email: str) -> None:
    """
    Resend a verification email for an unverified user.

    Security design:
        This function never raises for missing or already-verified emails.
        Silent no-op in both cases. View always returns the same success
        message — prevents email enumeration attacks.

    Flow:
        1. Look up user by email — silent no-op if not found
        2. Silent no-op if already verified
        3. Create new EmailVerificationToken
        4. Dispatch verification email task

    Args:
        email: Normalized email address from serializer.
    """
    from apps.accounts.models import EmailVerificationToken, User
    from apps.accounts.tasks import send_verification_email_task

    log_context = {}

    # ── User lookup ────────────────────────────────────────────────────────────
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        logger.debug(
            "Resend verification — email not registered (silent no-op)",
            extra=log_context,
        )
        return

    log_context["user_id"] = user.id

    # ── Already verified — silent no-op ───────────────────────────────────────
    if user.is_verified:
        logger.info(
            "Resend verification — user already verified (silent no-op)",
            extra=log_context,
        )
        

    # ── Create token + dispatch ────────────────────────────────────────────────
    try:
        token_obj = EmailVerificationToken.objects.create(user=user)
        send_verification_email_task.delay(user.id, str(token_obj.token))
        logger.info(
            "Verification email resent successfully",
            extra=log_context,
        )
    except Exception:
        logger.exception(
            "Failed to create token or dispatch resend verification email",
            extra=log_context,
        )