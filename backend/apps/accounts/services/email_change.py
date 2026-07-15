# apps/accounts/services/email_change.py
from __future__ import annotations

import logging

from django.contrib.auth.hashers import check_password
from django.db import transaction

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from apps.accounts.utils.token_utils import blacklist_all_user_tokens

logger = logging.getLogger("apps.accounts")


def request_email_change(
    *,
    user: "User",
    new_email: str,
    password: str,
) -> None:
    """
    Handle an authenticated user's request to change their email.

    Why password confirmation?
        Email is a login credential. Requiring password confirmation
        prevents account takeover if an attacker has a valid session
        but not the password (e.g. stolen JWT token).

    Why not change email immediately?
        New email must be verified first. If we changed it immediately
        and the user mistyped, they would lose access to their account.
        PendingEmailChange holds the new email until verified.

    Why notify old email?
        Security notification — if this was not the user,
        they can contact support immediately.

    Phase 1 — Atomic transaction:
        1. Verify password confirmation
        2. Check new email is not already taken
        3. Create or update PendingEmailChange record
           (OneToOne — only one pending change per user at a time)

    Phase 2 — After commit:
        4. Send verification email to NEW address
        5. Send security notification to OLD address

    Args:
        user:      Authenticated User instance from request.
        new_email: Normalized, validated new email from serializer.
        password:  Plain-text password for confirmation.

    Raises:
        DomainError: Wrong password (400), new email taken (409).
        Exception:   Any unexpected error is logged and re-raised.
    """
    from apps.accounts.models import PendingEmailChange, User
    from apps.accounts.tasks import (
        send_email_change_verification_task,
        send_email_change_notification_task,
    )

    log_context = {"user_id": user.id}

    # ── Phase 1: Atomic transaction ────────────────────────────────────────────
    try:
        with transaction.atomic():

            # Step 1: Verify password
            if not check_password(password, user.password):
                logger.warning(
                    "Email change request failed — incorrect password",
                    extra=log_context,
                )
                raise DomainError(
                    "Incorrect password. Please try again.",
                    code=ErrorCode.INVALID_CREDENTIALS,
                    status_code=400,
                )

            # Step 2: Check new email not already taken
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                logger.warning(
                    "Email change request failed — new email already taken",
                    extra=log_context,
                )
                raise DomainError(
                    "This email address is already associated with another account.",
                    code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    status_code=409,
                )

            # Step 3: Create or update PendingEmailChange
            # OneToOne — update_or_create replaces any existing pending request.
            # This means requesting a new email change cancels the previous one.
            old_email = user.email
            pending, _ = PendingEmailChange.objects.update_or_create(
                user=user,
                defaults={
                    "new_email": new_email,
                    "is_used": False,
                    "expires_at": None,  # save() will auto-set from expiry_hours
                },
            )

            logger.info(
                "PendingEmailChange created",
                extra={**log_context, "new_email": new_email},
            )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during email change request transaction — "
            "all changes rolled back.",
            extra=log_context,
        )
        raise

    # ── Phase 2: Task dispatch (after commit) ──────────────────────────────────

    # Task 1: Verification email to NEW address
    try:
        print('mia try ma hu')
        send_email_change_verification_task.delay(
            user.id,
            new_email,
            str(pending.token),
        )
        logger.info(
            "Email change verification task dispatched",
            extra={**log_context, "new_email": new_email},
        )
    except Exception:
        logger.exception(
            "Failed to dispatch email change verification task",
            extra={**log_context, "new_email": new_email},
        )

    # Task 2: Security notification to OLD address
    try:
        send_email_change_notification_task.delay(
            user.id,
            old_email,
            user.short_name,
        )
        logger.info(
            "Email change security notification dispatched to old email",
            extra={**log_context, "old_email": old_email},
        )
    except Exception:
        logger.exception(
            "Failed to dispatch email change security notification to old email",
            extra=log_context,
        )


def confirm_email_change(*, token_value: str) -> None:
    """
    Confirm an email change using the token sent to the new address.

    Phase 1 — Atomic transaction:
        1. Fetch PendingEmailChange by token
        2. Validate (exists, not expired, not used)
        3. Mark token as used FIRST (replay attack prevention)
        4. Update user.email to new_email

    Phase 2 — After commit:
        5. Blacklist all JWT tokens (email is login credential)

    Args:
        token_value: UUID string from verification email link.

    Raises:
        DomainError: Token not found (400), expired (400), already used (400).
        Exception:   Any unexpected error is logged and re-raised.
    """
    from apps.accounts.models import PendingEmailChange

    log_context = {"token": str(token_value)}

    # ── Phase 1: Atomic transaction ────────────────────────────────────────────
    try:
        with transaction.atomic():

            # Step 1: Fetch token
            try:
                pending = (
                    PendingEmailChange.objects
                    .select_related("user")
                    .get(token=token_value)
                )
            except PendingEmailChange.DoesNotExist:
                logger.warning(
                    "Email change confirm failed — token not found",
                    extra=log_context,
                )
                raise DomainError(
                    "Invalid or expired email change token.",
                    code=ErrorCode.TOKEN_INVALID,
                    status_code=400,
                )

            user = pending.user
            log_context["user_id"] = user.id

            # Step 2a: Check expiry
            if pending.is_expired:
                logger.warning(
                    "Email change confirm failed — token expired",
                    extra=log_context,
                )
                raise DomainError(
                    "Email change token has expired. Please request a new one.",
                    code=ErrorCode.TOKEN_EXPIRED,
                    status_code=400,
                )

            # Step 2b: Check already used
            if pending.is_used:
                logger.warning(
                    "Email change confirm failed — token already used",
                    extra=log_context,
                )
                raise DomainError(
                    "This email change token has already been used.",
                    code=ErrorCode.TOKEN_INVALID,
                    status_code=400,
                )

            # Step 3: Mark used FIRST — replay attack prevention
            pending.mark_used()

            # Step 4: Update email
            new_email = pending.new_email
            user.email = new_email
            user.save(update_fields=["email"])

            logger.info(
                "Email changed successfully",
                extra={**log_context, "new_email": new_email},
            )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during email change confirm transaction — "
            "all changes rolled back.",
            extra=log_context,
        )
        raise

    # ── Phase 2: Blacklist all JWT tokens (after commit) ──────────────────────
    # Email is a login credential — blacklist mandatory.
    # Existing sessions must be invalidated immediately.
    try:
        blacklist_all_user_tokens(user)
        logger.info(
            "All JWT tokens blacklisted after email change",
            extra=log_context,
        )
    except Exception:
        logger.exception(
            "Failed to blacklist JWT tokens after email change — "
            "email changed but existing sessions may remain active.",
            extra=log_context,
        )