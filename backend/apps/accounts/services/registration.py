# apps/accounts/services/registration.py
from __future__ import annotations

import logging
from apps.accounts.models import EmailVerificationToken, User,UserProfile
from apps.accounts.tasks import send_verification_email_task
from apps.cart.models import Cart
from django.db import IntegrityError, transaction

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.accounts")


def register_user(
    *,
    email: str,
    full_name: str,
    password: str,
) -> "User":
    """
    Complete user registration workflow.

    Responsibility:
        This function owns the entire registration transaction.
        It creates the User, UserProfile, Cart, and EmailVerificationToken
        in a single atomic transaction, then dispatches the verification
        email after the transaction commits.

    Why profile and cart here instead of signals?
        Signals are silent, invisible, and outside the transaction boundary.
        If a signal fails, the user is created but profile/cart are missing
        and no rollback occurs. Here everything is explicit, visible,
        transactional, and independently testable.

    Why task dispatch AFTER the transaction?
        If the task fires inside the transaction and the transaction later
        rolls back, the worker picks up a user_id that no longer exists.
        Dispatching after commit guarantees the worker always finds the user.

    Phase 1 — Atomic transaction:
        1. Create User
        2. Create UserProfile
        3. Create Cart
        4. Create EmailVerificationToken

    Phase 2 — After commit:
        5. Dispatch verification email task

    Args:
        email:     Normalized, validated email from serializer.
        full_name: Validated full name from serializer.
        password:  Validated plain-text password from serializer.

    Returns:
        Newly created User instance.

    Raises:
        DomainError: If email already exists (race condition, 409).
        Exception:   Any unexpected error is logged and re-raised.
    """
    

    

    log_context = {"email": email}

    # ── Phase 1: Atomic DB operations ─────────────────────────────────────────
    try:
        with transaction.atomic():

            # Step 1: Create User
            try:
                user = User.objects.create_user(
                    email=email,
                    full_name=full_name,
                    password=password,
                )
            except IntegrityError:
                logger.warning(
                    "Duplicate email race condition during registration",
                    extra=log_context,
                )
                raise DomainError(
                    "An account with this email already exists.",
                    code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    status_code=409,
                )

            logger.info(
                "User record created",
                extra={**log_context, "user_id": user.id},
            )

            # Step 2: Create UserProfile
            UserProfile.objects.create(user=user)
            logger.info(
                "UserProfile created",
                extra={**log_context, "user_id": user.id},
            )

            # Step 3: Create Cart
            Cart.objects.create(user=user)
            logger.info(
                "Cart created",
                extra={**log_context, "user_id": user.id},
            )

            # Step 4: Create EmailVerificationToken
            token_obj = EmailVerificationToken.objects.create(user=user)
            logger.info(
                "Verification token created",
                extra={**log_context, "user_id": user.id},
            )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during registration transaction — "
            "all changes rolled back.",
            extra=log_context,
        )
        raise

    # ── Phase 2: Task dispatch (after commit) ──────────────────────────────────
    # User, UserProfile, Cart, Token are all committed at this point.
    # Worker is guaranteed to find the user.
    try:
        send_verification_email_task.delay(user.id, str(token_obj.token))
        logger.info(
            "Verification email task dispatched",
            extra={**log_context, "user_id": user.id},
        )
    except Exception:
        # Task failure does NOT undo registration.
        # User account is valid — resend endpoint handles recovery.
        logger.exception(
            "Failed to dispatch verification email — "
            "user created but email not sent. "
            "Resend endpoint available for recovery.",
            extra={**log_context, "user_id": user.id},
        )

    return user