# apps/accounts/services/account_deletion.py
from __future__ import annotations

import logging

from django.contrib.auth.hashers import check_password
from apps.accounts.tasks import send_goodbye_email_task
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.accounts")


def delete_user_account(
    *,
    user: "User",
    password: str,
) -> None:
    """
    Complete user account deletion workflow.

    Responsibility:
        Validates password confirmation, collects user data
        needed for goodbye email, hard deletes the user,
        then dispatches goodbye email task after deletion.

    Why collect email and name BEFORE delete?
        After hard delete the user object is gone from DB.
        Task needs email and name to send goodbye email.
        We collect them before deletion and pass directly to task.

    Why task dispatch AFTER delete?
        Deletion is the critical operation.
        Email is non-critical — failure must never block or
        roll back a confirmed account deletion.

    Phase 1 — Validate password:
        1. Check submitted password against stored hash

    Phase 2 — Collect data + hard delete:
        2. Collect email and name before delete
        3. Hard delete user (CASCADE handles all related data)

    Phase 3 — After delete:
        4. Dispatch goodbye email task

    Args:
        user:     The authenticated User instance requesting deletion.
        password: Plain-text password submitted for confirmation.

    Raises:
        DomainError: If password confirmation fails (400).
        Exception:   Any unexpected error is logged and re-raised.
    """
    

    log_context = {"user_id": user.id, "email": user.email}

    # ── Phase 1: Password confirmation ─────────────────────────────────────────
    if not check_password(password, user.password):
        logger.warning(
            "Account deletion failed — incorrect password confirmation",
            extra=log_context,
        )
        raise DomainError(
            "Incorrect password. Please try again.",
            code=ErrorCode.INVALID_CREDENTIALS,
            status_code=400,
        )

    # ── Phase 2: Collect data + hard delete ────────────────────────────────────
    # Collect before delete — user object will be gone after deletion.
    # Task needs these to send goodbye email.
    user_email = user.email
    user_name = user.short_name

    try:
        user.delete()
        logger.info(
            "User account hard deleted successfully",
            extra=log_context,
        )
    except Exception:
        logger.exception(
            "Unexpected error during user account deletion",
            extra=log_context,
        )
        raise

    # ── Phase 3: Goodbye email dispatch (after delete) ─────────────────────────
    # User is gone from DB at this point.
    # We pass email and name directly — no DB lookup needed in task.
    try:
        send_goodbye_email_task.delay(user_email, user_name)
        logger.info(
            "Goodbye email task dispatched",
            extra=log_context,
        )
    except Exception:
        # Email failure must NOT affect deletion confirmation.
        # Account is already deleted — this is non-critical.
        logger.exception(
            "Failed to dispatch goodbye email after account deletion — "
            "account is deleted but goodbye email not sent.",
            extra=log_context,
        )