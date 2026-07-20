# apps/accounts/services/email_change.py
from __future__ import annotations

import logging

from django.db import transaction

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from apps.accounts.models import User
logger = logging.getLogger("apps.accounts")


def request_email_change(
    *,
    user: "User",
    new_email: str,
    verification_token: str,
) -> str:
    """
    Phase 2 of email change — after identity already proven.

    Steps:
        1. Consume SecurityVerifiedSession (purpose=change_email)
        2. Check new email not already taken
        3. Create/update PendingEmailChange (lean state record)
        4. Create SecurityVerificationOTP (purpose=verify_new_email)
        5. Send OTP to new_email address

    Returns:
        Masked new email for frontend display.

    Raises:
        DomainError: Session invalid/expired, email taken.
    """
    from apps.accounts.models import PendingEmailChange, User
    from apps.accounts.services.security_otp import (
        consume_verified_session,
        send_security_otp,
    )

    log_context = {"user_id": user.id}

    try:
        with transaction.atomic():

            # Step 1: Consume verified session — proves phase 1 done
            consume_verified_session(
                user    = user,
                purpose = "change_email",
                token   = verification_token,
            )

            # Step 2: Check new email not taken
            if User.objects.filter(email=new_email).exclude(id=user.id).exists():
                raise DomainError(
                    "This email address is already associated with another account.",
                    code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    status_code=409,
                )

            # Step 3: Create lean PendingEmailChange state record
            PendingEmailChange.objects.update_or_create(
                user     = user,
                defaults = {"new_email": new_email, "expires_at": None},
            )

            logger.info(
                "PendingEmailChange created",
                extra={**log_context, "new_email": new_email},
            )

    except DomainError:
        raise
    except Exception:
        logger.exception(
            "Unexpected error during email change request",
            extra=log_context,
        )
        raise

    # Step 4+5: Send OTP to new email AFTER commit
    # Uses SecurityVerificationOTP — no duplicated OTP logic
    masked = send_security_otp(
        user            = user,
        purpose         = "verify_new_email",
        recipient_email = new_email,
    )

    return masked


def confirm_email_change_otp(
    *,
    user: "User",
    otp_code: str,
) -> None:
    """
    Phase 3 — User enters OTP received at new email address.

    Why user is passed here:
        Frontend still has valid JWT at this point.
        We use user to look up PendingEmailChange cleanly.
        No need to scan all pending records like before.

    Steps:
        1. Fetch PendingEmailChange for this user
        2. Check overall request not expired
        3. Verify OTP via SecurityVerificationOTP
        4. Update User.email
        5. Delete PendingEmailChange
        6. Blacklist all tokens

    Raises:
        DomainError: No pending change, request expired, OTP invalid.
    """
    from apps.accounts.models import PendingEmailChange
    from apps.accounts.services.security_otp import verify_security_otp
    from apps.accounts.utils.token_utils import blacklist_all_user_tokens

    log_context = {"user_id": user.id}

    # Step 1: Fetch pending change
    try:
        pending = PendingEmailChange.objects.get(user=user)
    except PendingEmailChange.DoesNotExist:
        raise DomainError(
            "No pending email change found. Please start the process again.",
            code=ErrorCode.TOKEN_INVALID,
            status_code=400,
        )

    # Step 2: Check overall request not expired
    if pending.is_expired:
        pending.delete()
        raise DomainError(
            "Email change request has expired. Please start again.",
            code=ErrorCode.TOKEN_EXPIRED,
            status_code=400,
        )

    new_email = pending.new_email
    log_context["new_email"] = new_email

    # Step 3: Verify OTP via SecurityVerificationOTP
    # verify_security_otp handles: not found, expired, attempts exceeded, wrong code
    # Issues a verified session token which we discard here — we only need side effect
    verify_security_otp(
        user     = user,
        purpose  = "verify_new_email",
        otp_code = otp_code,
    )

    # Step 4+5: Update email + delete pending record
    try:
        with transaction.atomic():
            user.email = new_email
            user.save(update_fields=["email"])
            pending.delete()

            logger.info(
                "Email changed successfully",
                extra={**log_context},
            )
    except Exception:
        logger.exception(
            "Unexpected error confirming email change",
            extra=log_context,
        )
        raise

    # Step 6: Blacklist tokens after commit
    try:
        blacklist_all_user_tokens(user)
        logger.info("Tokens blacklisted after email change", extra=log_context)
    except Exception:
        logger.exception(
            "Failed to blacklist tokens after email change",
            extra=log_context,
        )