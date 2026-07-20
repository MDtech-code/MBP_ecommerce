# apps/accounts/services/security_otp.py
from __future__ import annotations

import logging
import random
import string

from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import (
    SecurityVerificationOTP,
    SecurityVerifiedSession,
    SecurityPurpose,
)
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from apps.accounts.models import User
logger = logging.getLogger("apps.accounts")

RESEND_COOLDOWN_SECONDS = 60


def send_security_otp(
    *,
    user: "User",
    purpose: str,
    recipient_email: str | None = None,
) -> str:
    """
    Generate and send a 6-digit OTP.

    For most purposes: OTP sent to user's CURRENT email.
    For VERIFY_NEW_EMAIL: OTP sent to recipient_email (the new address).

    Args:
        user:            Authenticated user.
        purpose:         SecurityPurpose choice.
        recipient_email: Override email address — used for VERIFY_NEW_EMAIL only.

    Returns:
        Masked version of the email OTP was sent to.
        "jo**@gmail.com" or "ne**@newdomain.com"

    Raises:
        DomainError 400: Resend cooldown not elapsed.
    """
    from apps.accounts.tasks import send_security_otp_task

    log_context = {"user_id": user.id, "purpose": purpose}

    # Determine recipient
    send_to = recipient_email if recipient_email else user.email

    # ── Cooldown check ─────────────────────────────────────────────────────────
    cooldown_threshold = timezone.now() - timedelta(seconds=RESEND_COOLDOWN_SECONDS)
    recent = SecurityVerificationOTP.objects.filter(
        user       = user,
        purpose    = purpose,
        created_at__gte = cooldown_threshold,
    ).first()

    if recent:
        seconds_remaining = int(
            RESEND_COOLDOWN_SECONDS
            - (timezone.now() - recent.created_at).total_seconds()
        )
        raise DomainError(
            f"Please wait {seconds_remaining} seconds before requesting a new code.",
            code=ErrorCode.OTP_RESEND_COOLDOWN,
            status_code=400,
            client_extra={"seconds_remaining": seconds_remaining},
        )

    # ── Generate + store OTP ───────────────────────────────────────────────────
    plain_otp = _generate_otp()
    otp_hash  = make_password(plain_otp)

    with transaction.atomic():
        # Invalidate any previous active OTP for this user+purpose
        SecurityVerificationOTP.objects.filter(
            user    = user,
            purpose = purpose,
            is_used = False,
        ).update(is_used=True)

        SecurityVerificationOTP.objects.create(
            user     = user,
            purpose  = purpose,
            otp_hash = otp_hash,
            metadata = {"recipient_email": send_to},
        )

    logger.info("Security OTP created", extra={**log_context})

    # ── Dispatch task ──────────────────────────────────────────────────────────
    try:
        print("send to : ",send_to)
        send_security_otp_task.delay(
            user.id,
            plain_otp,
            purpose,
            send_to,         # ← explicit recipient
        )
    except Exception:
        logger.exception(
            "Failed to dispatch OTP email task",
            extra=log_context,
        )

    return _mask_email(send_to)


def verify_security_otp(
    *,
    user: "User",
    purpose: str,
    otp_code: str,
) -> str:
    """
    Verify OTP and issue SecurityVerifiedSession token.

    For VERIFY_NEW_EMAIL purpose:
        Also carries metadata from OTP into session
        so service can retrieve new_email without extra DB call.

    Returns:
        verification_token UUID string.
    """
    log_context = {"user_id": user.id, "purpose": purpose}

    with transaction.atomic():

        try:
            otp = (
                SecurityVerificationOTP.objects
                .select_for_update()
                .get(
                    user    = user,
                    purpose = purpose,
                    is_used = False,
                )
            )
        except SecurityVerificationOTP.DoesNotExist:
            raise DomainError(
                "No active verification code found. Please request a new one.",
                code=ErrorCode.OTP_NOT_FOUND,
                status_code=400,
            )

        if otp.is_expired:
            raise DomainError(
                "Your verification code has expired. Please request a new one.",
                code=ErrorCode.OTP_EXPIRED,
                status_code=400,
            )

        if otp.is_attempts_exceeded:
            raise DomainError(
                "Too many incorrect attempts. Please request a new code.",
                code=ErrorCode.OTP_ATTEMPTS_EXCEEDED,
                status_code=400,
            )

        if not check_password(otp_code, otp.otp_hash):
            otp.increment_attempts()
            attempts_left = otp.max_attempts - otp.attempts
            logger.warning(
                "OTP incorrect attempt",
                extra={**log_context, "attempts_left": attempts_left},
            )
            raise DomainError(
                f"Incorrect code. {attempts_left} attempt(s) remaining.",
                code=ErrorCode.OTP_INVALID,
                status_code=400,
                client_extra={"attempts_left": attempts_left},
            )

        # Success
        otp.mark_used()

        # Carry metadata into session
        otp_metadata = otp.metadata or {}

        # Invalidate previous sessions for same user+purpose
        SecurityVerifiedSession.objects.filter(
            user    = user,
            purpose = purpose,
            is_used = False,
        ).update(is_used=True)

        session = SecurityVerifiedSession.objects.create(
            user     = user,
            purpose  = purpose,
            metadata = otp_metadata,   # carries new_email for VERIFY_NEW_EMAIL
        )

    logger.info(
        "OTP verified — session token issued",
        extra={**log_context, "session_id": session.id},
    )

    return str(session.token)


def consume_verified_session(
    *,
    user: "User",
    purpose: str,
    token: str,
) -> dict:
    """
    Validate and consume a SecurityVerifiedSession token.

    Returns:
        session.metadata dict — caller can extract new_email etc.

    Raises:
        DomainError: Token invalid, wrong purpose, expired, already used.
    """
    log_context = {"user_id": user.id, "purpose": purpose}

    with transaction.atomic():
        try:
            session = (
                SecurityVerifiedSession.objects
                .select_for_update()
                .get(
                    token   = token,
                    user    = user,
                    purpose = purpose,
                    is_used = False,
                )
            )
        except SecurityVerifiedSession.DoesNotExist:
            logger.warning(
                "consume_verified_session — not found",
                extra=log_context,
            )
            raise DomainError(
                "Identity verification required. Please verify your identity first.",
                code=ErrorCode.VERIFICATION_SESSION_INVALID,
                status_code=400,
            )

        if session.is_expired:
            raise DomainError(
                "Your verification session has expired. Please verify again.",
                code=ErrorCode.VERIFICATION_SESSION_EXPIRED,
                status_code=400,
            )

        session.mark_used()
        metadata = session.metadata or {}

    logger.info("Verified session consumed", extra=log_context)
    return metadata


# ── Private helpers ────────────────────────────────────────────────────────────

def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=6))


def _mask_email(email: str) -> str:
    local, domain = email.split("@")
    masked_local  = local[:2] + "**" if len(local) > 2 else "**"
    return f"{masked_local}@{domain}"