# apps/accounts/services/registration.py
from __future__ import annotations

import logging
from django.db import IntegrityError, transaction
from apps.accounts.models import  User
from apps.accounts.tasks import send_verification_email_task
from apps.accounts.selectors.user_selectors import email_exists,create_user_profile,create_verification_token
from apps.cart.selectors.cart import create_cart_for_user
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from apps.common.utils.email_utils import mask_email


logger = logging.getLogger(__name__)


def register_user(
    *,
    email: str,
    full_name: str,
    password: str,
) -> "User":
    """
    Registration workflow:-

    Responsibility:
        This function owns the entire registration transaction.
        It creates the User, UserProfile, Cart, and EmailVerificationToken
        in a single atomic transaction, then dispatches the verification
        email after the transaction commits.

    Phase 1 — Atomic transaction:
        1. Uniqueness check
        2. Create User
        3. Create UserProfile
        4. Create Cart
        5. Create EmailVerificationToken

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
    

    
    email = email.lower().strip()
    full_name = " ".join(full_name.strip().split())
    log_context = {"email": mask_email(email)}

    #! ── Phase 1: Atomic DB operations ─────────────────────────────────────────
    try:
        with transaction.atomic():

            #! Step 1: Create User
            try:
                if email_exists(email):
                    raise DomainError(
                    "An account with this email already exists.",
                    code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    status_code=409,
                )
                
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

            #! Step 2: Create UserProfile
            create_user_profile(user)
            logger.info(
             "UserProfile created for new user",
             extra={"user_id": user.id, "email": mask_email(user.email)},
         )

            #! Step 3: Create Cart
            create_cart_for_user(user)
            logger.info(
                "Cart created",
                extra={**log_context, "user_id": user.id},
            )

            #! Step 4: Create EmailVerificationToken
            token_obj =create_verification_token(user)
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

    # ── Phase 2: dispatch email  ────────────────────────
    print(user,type(user))
    _dispatch_verification_email(
        user=user,
        token=token_obj.token,
        log_context=log_context,
    )

    return user

def _dispatch_verification_email(
    user:User,
    token: str,
    log_context: dict,
) -> None:
   
    try:
        send_verification_email_task.delay(user.id, str(token))
        logger.info(
            "Verification email task dispatched",
            extra={**log_context, "user_id": user.id},
        )
    except Exception:
        logger.exception(
            "Failed to dispatch verification email — "
            "user created but email not sent. "
            "Recovery via resend-verification endpoint.",
            extra={**log_context, "user_id": user.id},
        )