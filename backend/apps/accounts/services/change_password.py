# apps/accounts/services/change_password.py
from __future__ import annotations

import logging

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.accounts")


def change_user_password(
    *,
    user: "User",
    new_password: str,
    verification_token: str,
) -> None:
    """
    Change password after identity proven via OTP gate.

    No current_password field — OTP verification already proved identity.

    Steps:
        1. Consume SecurityVerifiedSession (purpose=change_password)
        2. Set new password
        3. Blacklist all JWT tokens

    Args:
        user:               Authenticated user.
        new_password:       Validated new password from serializer.
        verification_token: UUID from SecurityVerifiedSession.

    Raises:
        DomainError: Session invalid or expired.
    """
    from apps.accounts.services.security_otp import consume_verified_session
    from apps.accounts.utils.token_utils import blacklist_all_user_tokens

    log_context = {"user_id": user.id}

    # Step 1: Consume verified session
    consume_verified_session(
        user    = user,
        purpose = "change_password",
        token   = verification_token,
    )

    # Step 2: Set new password
    user.set_password(new_password)
    user.save(update_fields=["password"])

    logger.info("Password changed successfully", extra=log_context)

    # Step 3: Blacklist all tokens
    try:
        blacklist_all_user_tokens(user)
        logger.info("Tokens blacklisted after password change", extra=log_context)
    except Exception:
        logger.exception(
            "Failed to blacklist tokens after password change",
            extra=log_context,
        )