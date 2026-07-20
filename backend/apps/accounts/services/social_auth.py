# apps/accounts/services/social_auth.py
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import (
    SocialAccount,
    User,
    UserProfile,
)
from apps.cart.models import Cart
from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.accounts.auth_strategies.base import SocialUserData


logger = logging.getLogger("apps.accounts")


def login_or_register_social_user(social_data: SocialUserData) -> User:
    """
    Core business logic for all social authentication flows.

    Decision tree:
    ─────────────────────────────────────────────────────────
    Case 1 — Returning social user:
        SocialAccount(provider, provider_id) exists
        → update last_login_at
        → return linked User immediately
        (fastest path — no transaction needed)

    Case 2 — Existing email user links social:
        provider+provider_id not found
        BUT User.email matches social_data.email
        → create SocialAccount linked to existing User
        → user keeps their password login too
        (account merging)

    Case 3 — Brand new user:
        Neither SocialAccount nor email match found
        → create User + UserProfile + Cart + SocialAccount
        → atomically — all or nothing
    ─────────────────────────────────────────────────────────

    Social users:
        - password=None  (unusable password set by Django)
        - is_verified=True  (provider verified email)
        - No EmailVerificationToken created
        - No verification email sent

    Args:
        social_data: Normalized data from strategy layer.

    Returns:
        User instance — existing or newly created.

    Raises:
        DomainError: Account exists but blocked/inactive.
        Exception:   Unexpected DB error — logged and re-raised.
    """
    log_context = {
        "provider":    social_data.provider,
        "provider_id": social_data.provider_id,
        "email":       social_data.email,
    }

    # ── Case 1: Returning social user ─────────────────────────────────────────
    social_account = (
        SocialAccount.objects
        .filter(
            provider=social_data.provider,
            provider_id=social_data.provider_id,
        )
        .select_related("user")
        .first()
    )

    if social_account:
        user = social_account.user

        _assert_user_active(user)

        # Stamp last login — targeted update, no full save
        social_account.last_login_at = timezone.now()
        social_account.save(update_fields=["last_login_at"])

        logger.info(
            "Social login — returning user",
            extra={**log_context, "user_id": user.id},
        )
        return user

    # ── Cases 2 & 3: Atomic find-or-create ───────────────────────────────────
    try:
        with transaction.atomic():

            # Case 2: Email already in system (registered via email/password)
            user = User.objects.filter(email=social_data.email).first()

            if user:
                _assert_user_active(user)

                SocialAccount.objects.create(
                    user         = user,
                    provider     = social_data.provider,
                    provider_id  = social_data.provider_id,
                    provider_email = social_data.email,
                    is_provider_email_verified = social_data.is_provider_email_verified,
                    avatar_url   = social_data.avatar_url,
                    access_token = social_data.access_token,
                    refresh_token = social_data.refresh_token,
                    token_expires_at = social_data.token_expires_at,
                    extra_data                = social_data.extra_data, 
                    last_login_at = timezone.now(),
                )
                logger.info(
                    "Social login — linked to existing email account",
                    extra={**log_context, "user_id": user.id},
                )

            else:
                # Case 3: Net new user
                user = User.objects.create_user(
                    email      = social_data.email,
                    full_name  = social_data.full_name,
                    password   = None,
                    is_verified = social_data.is_verified,
                )
                UserProfile.objects.create(user=user)
                Cart.objects.create(user=user)
                SocialAccount.objects.create(
                    user           = user,
                    provider       = social_data.provider,
                    provider_id    = social_data.provider_id,
                    provider_email = social_data.email,
                    is_provider_email_verified = social_data.is_provider_email_verified,
                    avatar_url     = social_data.avatar_url,
                    access_token   = social_data.access_token,
                    refresh_token  = social_data.refresh_token,
                    token_expires_at = social_data.token_expires_at,
                    extra_data       = social_data.extra_data,
                    last_login_at  = timezone.now(),
                )
                logger.info(
                    "Social login — new user created",
                    extra={**log_context, "user_id": user.id},
                )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during social auth transaction",
            extra=log_context,
        )
        raise

    return user


def _assert_user_active(user: User) -> None:
    """
    Reject login for deactivated accounts.

    Raises:
        DomainError 400: Account is inactive.
    """
    if not user.is_active:
        raise DomainError(
            "This account has been deactivated. "
            "Please contact support.",
            code=ErrorCode.ACCOUNT_INACTIVE,
            status_code=400,
        )