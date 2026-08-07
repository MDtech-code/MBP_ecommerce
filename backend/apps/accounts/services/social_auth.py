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
from apps.accounts.services.avatar_sync import sync_provider_avatar

logger = logging.getLogger("apps.accounts")


def login_or_register_social_user(social_data: SocialUserData) -> User:
    print(social_data)
    """
    Core business logic for all social authentication flows.

    Decision tree:
    ─────────────────────────────────────────────────────────
    Case 1 — Returning social user:
        SocialAccount(provider, provider_id) exists
        → return linked User immediately
        (fastest path — no transaction needed)

    Case 2 — Existing email user links social:
        provider+provider_id not found
        BUT User.email matches social_data.email
        → create SocialAccount linked to existing User
        → user keeps their password login too
        (account merging)
        → avatar is NOT synced here — only on true new-account creation
          (Case 3), so a user who already has a profile (with or without
          their own uploaded avatar) is never touched.

    Case 3 — Brand new user:
        Neither SocialAccount nor email match found
        → create User + UserProfile + Cart + SocialAccount
        → atomically — all or nothing
        → AFTER the transaction commits, attempt to download and save
          the provider's avatar into UserProfile.avatar. This happens
          outside the atomic block deliberately: it's a network call
          (slow, can fail) and its failure must never roll back account
          creation — same reasoning as _dispatch_verification_email in
          the manual registration flow. A user ending up with no avatar
          is a fully valid, unremarkable state (same as manual signup);
          a failed HTTP request should never be why account creation
          fails.
    ─────────────────────────────────────────────────────────

    Social users:
        - password=None  (unusable password set by Django)
        - is_verified=True  (provider verified email)
        - No EmailVerificationToken created
        - No verification email sent

    On SocialAccount fields:
        access_token / refresh_token are now genuinely populated from
        social_data (previously both strategies hardcoded these to "",
        making the fields structurally present but functionally dead —
        see auth_strategies/google.py and facebook.py, now updated to
        capture the real provider token). These represent the OAuth
        PROVIDER's tokens (for potential future calls to Google/Facebook
        APIs on the user's behalf), not this app's own JWT access/refresh
        tokens — those are issued separately by SocialAuthView via
        RefreshToken.for_user() and have nothing to do with this model.

        last_login_at has been REMOVED from SocialAccount — it was
        redundant with User.last_login, which Django already updates
        automatically via the user_logged_in signal (already dispatched
        in LoginView, and now also in SocialAuthView — see that file).
        Nothing in the codebase read SocialAccount.last_login_at for any
        actual purpose; per-provider "last used" tracking is a real
        feature but wasn't being used anywhere, so it was removed rather
        than kept as unused scaffolding. Re-add it explicitly, with a
        real consumer, if that feature is ever actually built.

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

        logger.info(
            "Social login — returning user",
            extra={**log_context, "user_id": user.id},
        )
        return user

    # ── Cases 2 & 3: Atomic find-or-create ───────────────────────────────────
    is_new_user = False

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
                )
                is_new_user = True
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

    # ── Post-commit: avatar sync, new users only ────────────────────────────────
    # Deliberately outside the atomic block — a slow or failed network
    # call must never roll back a successfully created account. Only
    # runs for Case 3; Case 2 (linking to an existing account) never
    # touches an existing user's UserProfile.avatar.
    if is_new_user and social_data.avatar_url:
        sync_provider_avatar(
            user_profile=user.profile,
            avatar_url=social_data.avatar_url,
        )

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
# # apps/accounts/services/social_auth.py
# from __future__ import annotations

# import logging

# from django.db import transaction
# from django.utils import timezone

# from apps.accounts.models import (
#     SocialAccount,
#     User,
# )

# from apps.core.exceptions import DomainError
# from apps.core.error_codes import ErrorCode
# from apps.accounts.auth_strategies.base import SocialUserData
# from apps.accounts.selectors.user_selectors import create_user_profile
# from apps.cart.selectors.cart import create_cart_for_user
# from apps.common.utils.email_utils import mask_email


# logger = logging.getLogger("apps.accounts")


# def login_or_register_social_user(social_data: SocialUserData) -> User:
#     """
#     Core business logic for all social authentication flows.

#     Decision tree:
#     ─────────────────────────────────────────────────────────
#     Case 1 — Returning social user:
#         SocialAccount(provider, provider_id) exists
#         → update last_login_at
#         → return linked User immediately
#         (fastest path — no transaction needed)

#     Case 2 — Existing email user links social:
#         provider+provider_id not found
#         BUT User.email matches social_data.email
#         → create SocialAccount linked to existing User
#         → user keeps their password login too
#         (account merging)

#     Case 3 — Brand new user:
#         Neither SocialAccount nor email match found
#         → create User + UserProfile + Cart + SocialAccount
#         → atomically — all or nothing
#     ─────────────────────────────────────────────────────────

#     Social users:
#         - password=None  (unusable password set by Django)
#         - is_verified=True  (provider verified email)
#         - No EmailVerificationToken created
#         - No verification email sent

#     Args:
#         social_data: Normalized data from strategy layer.

#     Returns:
#         User instance — existing or newly created.

#     Raises:
#         DomainError: Account exists but blocked/inactive.
#         Exception:   Unexpected DB error — logged and re-raised.
#     """
#     log_context = {
#         "provider":    social_data.provider,
#         "provider_id": social_data.provider_id,
#         "email":       social_data.email,
#     }

#     # ── Case 1: Returning social user ─────────────────────────────────────────
#     social_account = (
#         SocialAccount.objects
#         .filter(
#             provider=social_data.provider,
#             provider_id=social_data.provider_id,
#         )
#         .select_related("user")
#         .first()
#     )

#     if social_account:
#         user = social_account.user

#         _assert_user_active(user)

#         # Stamp last login — targeted update, no full save
#         social_account.last_login_at = timezone.now()
#         social_account.save(update_fields=["last_login_at"])

#         logger.info(
#             "Social login — returning user",
#             extra={**log_context, "user_id": user.id},
#         )
#         return user

#     # ── Cases 2 & 3: Atomic find-or-create ───────────────────────────────────
#     try:
#         with transaction.atomic():

#             # Case 2: Email already in system (registered via email/password)
#             user = User.objects.filter(email=social_data.email).first()

#             if user:
#                 _assert_user_active(user)

#                 SocialAccount.objects.create(
#                     user         = user,
#                     provider     = social_data.provider,
#                     provider_id  = social_data.provider_id,
#                     provider_email = social_data.email,
#                     is_provider_email_verified = social_data.is_provider_email_verified,
#                     avatar_url   = social_data.avatar_url,
#                     access_token = social_data.access_token,
#                     refresh_token = social_data.refresh_token,
#                     token_expires_at = social_data.token_expires_at,
#                     extra_data                = social_data.extra_data, 
#                     last_login_at = timezone.now(),
#                 )
#                 logger.info(
#                     "Social login — linked to existing email account",
#                     extra={**log_context, "user_id": user.id},
#                 )

#             else:
#                 # Case 3: Net new user
#                 user = User.objects.create_user(
#                     email      = social_data.email,
#                     full_name  = social_data.full_name,
#                     password   = None,
#                     is_verified = social_data.is_verified,
#                 )

                
#                 create_user_profile(user)
#                 logger.info(
#                  "UserProfile created for new user",
#                  extra={"user_id": user.id, "email": mask_email(user.email)},
#                 )
            
#                 create_cart_for_user(user)
#                 logger.info(
#                     "Cart created",
#                     extra={**log_context, "user_id": user.id},
#                 )
#                 SocialAccount.objects.create(
#                     user           = user,
#                     provider       = social_data.provider,
#                     provider_id    = social_data.provider_id,
#                     provider_email = social_data.email,
#                     is_provider_email_verified = social_data.is_provider_email_verified,
#                     avatar_url     = social_data.avatar_url,
#                     access_token   = social_data.access_token,
#                     refresh_token  = social_data.refresh_token,
#                     token_expires_at = social_data.token_expires_at,
#                     extra_data       = social_data.extra_data,
#                     last_login_at  = timezone.now(),
#                 )
#                 logger.info(
#                     "Social login — new user created",
#                     extra={**log_context, "user_id": user.id},
#                 )

#     except DomainError:
#         raise

#     except Exception:
#         logger.exception(
#             "Unexpected error during social auth transaction",
#             extra=log_context,
#         )
#         raise

#     return user


# def _assert_user_active(user: User) -> None:
#     """
#     Reject login for deactivated accounts.

#     Raises:
#         DomainError 400: Account is inactive.
#     """
#     if not user.is_active:
#         raise DomainError(
#             "This account has been deactivated. "
#             "Please contact support.",
#             code=ErrorCode.ACCOUNT_INACTIVE,
#             status_code=400,
#         )