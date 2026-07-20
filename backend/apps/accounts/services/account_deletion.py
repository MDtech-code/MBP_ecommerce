# apps/accounts/services/account_deletion.py
from __future__ import annotations

import logging

from apps.core.exceptions import DomainError
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from apps.accounts.models import User
logger = logging.getLogger("apps.accounts")


def delete_user_account(
    *,
    user: "User",
    verification_token: str,
) -> None:
    """
    Hard delete user account after identity proven via OTP gate.

    No password field — OTP verification already proved identity.

    Steps:
        1. Consume SecurityVerifiedSession (purpose=delete_account)
        2. Collect email + name before deletion
        3. Hard delete user (CASCADE handles related records)
        4. Dispatch goodbye email

    Args:
        user:               Authenticated user.
        verification_token: UUID from SecurityVerifiedSession.

    Raises:
        DomainError: Session invalid or expired.
    """
    from apps.accounts.services.security_otp import consume_verified_session
    from apps.accounts.tasks import send_goodbye_email_task

    log_context = {"user_id": user.id, "email": user.email}

    # Step 1: Consume verified session
    consume_verified_session(
        user    = user,
        purpose = "delete_account",
        token   = verification_token,
    )

    # Step 2: Collect before deletion
    user_email = user.email
    user_name  = user.short_name

    # Step 3: Hard delete
    try:
        user.delete()
        logger.info("User account deleted", extra=log_context)
    except Exception:
        logger.exception("Unexpected error during account deletion", extra=log_context)
        raise

    # Step 4: Goodbye email — after deletion
    try:
        send_goodbye_email_task.delay(user_email, user_name)
        logger.info("Goodbye email dispatched", extra=log_context)
    except Exception:
        logger.exception(
            "Failed to dispatch goodbye email — account already deleted",
            extra=log_context,
        )