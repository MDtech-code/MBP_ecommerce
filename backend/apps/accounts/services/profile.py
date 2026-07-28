# apps/accounts/services/profile.py
from __future__ import annotations

import logging

from django.db import transaction

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from apps.accounts.validators import ensure_phone_uniqueness
logger = logging.getLogger("apps.accounts")
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from apps.accounts.models import User,UserAddress,QuerySet

# ── Profile ────────────────────────────────────────────────────────────────────

def get_user_profile(*, user_id: int) -> "User":
    """
    Fetch user with profile and addresses in a single query.

    Args:
        user_id: PK of the authenticated user.

    Returns:
        User instance with profile and addresses prefetched.

    Raises:
        Exception: Any unexpected DB error is logged and re-raised.
    """
    from apps.accounts.models import User

    return (
        User.objects
        .select_related("profile")
        .prefetch_related("addresses")
        .get(pk=user_id)
    )


def update_user_profile(*, user_id: int, data: dict) -> "User":
    """
    Partially update the authenticated user's profile.

    Phase 1 — Atomic transaction:
        1. Fetch user with profile
        2. Validate and save profile fields

    Phase 2 — After commit:
        3. Re-fetch user with fresh data for response

    Args:
        user_id: PK of the authenticated user.
        data:    Partial update dict from serializer validated_data.

    Returns:
        Updated User instance with profile and addresses prefetched.

    Raises:
        DomainError: Profile does not exist for this user (400).
        Exception:   Any unexpected error is logged and re-raised.
    """
    from apps.accounts.models import User, UserProfile
    from apps.accounts.serializers import ProfileUpdateSerializer

    log_context = {"user_id": user_id}
    

    try:
        print("try ma hu")
        # ensure_phone_uniqueness(data['phone'])
        with transaction.atomic():

            # Step 1: Fetch user with profile
            try:
                user = (
                    User.objects
                    .select_related("profile")
                    .get(pk=user_id)
                )
                profile = user.profile

            except UserProfile.DoesNotExist:
                logger.error(
                    "Profile not found for authenticated user — "
                    "may not have been created during registration.",
                    extra=log_context,
                )
                raise DomainError(
                    "Profile not found.",
                    code=ErrorCode.NOT_FOUND,
                    status_code=400,
                )
            # Step 2: Instance-aware uniqueness check — only if phone is incoming
            if "phone" in data and data["phone"]:
                ensure_phone_uniqueness(data["phone"], instance=profile)

            # Step 2: Validate and save
            serializer = ProfileUpdateSerializer(
                profile,
                data=data,
                partial=True,
            )

            if not serializer.is_valid():
                # Re-raise as DomainError so view stays clean.
                # Validation errors from service should not happen —
                # view already validated. This is a safety net.
                raise DomainError(
                    "Profile update failed.",
                    code=ErrorCode.VALIDATION_ERROR,
                    status_code=400,
                )

            serializer.save()

            logger.info(
                "Profile updated successfully",
                extra=log_context,
            )

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during profile update transaction — "
            "all changes rolled back.",
            extra=log_context,
        )
        raise

    # Re-fetch after commit — ensures response reflects saved state
    return get_user_profile(user_id=user_id)


# ── Avatar ─────────────────────────────────────────────────────────────────────

def update_user_avatar(*, user_id: int, new_avatar) -> str:
    """
    Replace the authenticated user's profile avatar.

    Old avatar deletion is non-fatal — missing file must never
    block the new upload. Log and continue.

    Phase 1:
        1. Delete old avatar from storage (non-fatal)
        2. Save new avatar to profile

    Args:
        user_id:    PK of the authenticated user.
        new_avatar: Validated image file from serializer.

    Returns:
        URL string of the newly saved avatar.

    Raises:
        Exception: Unexpected DB error on save is logged and re-raised.
    """
    from apps.accounts.models import User

    log_context = {"user_id": user_id}

    user = User.objects.select_related("profile").get(pk=user_id)
    profile = user.profile

    # Step 1: Delete old avatar — non-fatal
    if profile.avatar:
        try:
            profile.avatar.delete(save=False)
        except Exception:
            logger.warning(
                "Failed to delete old avatar from storage — "
                "proceeding with new upload. Manual cleanup may be needed.",
                extra={**log_context, "old_avatar": str(profile.avatar)},
            )

    # Step 2: Save new avatar
    try:
        profile.avatar = new_avatar
        profile.save(update_fields=["avatar"])
        logger.info(
            "Avatar updated successfully",
            extra=log_context,
        )
    except Exception:
        logger.exception(
            "Unexpected error saving new avatar to profile",
            extra=log_context,
        )
        raise

    return profile.avatar.url


# ── Addresses ──────────────────────────────────────────────────────────────────

def get_user_addresses(*, user_id: int) -> "QuerySet":
    """
    Fetch all addresses for the authenticated user.

    Args:
        user_id: PK of the authenticated user.

    Returns:
        QuerySet of UserAddress instances ordered by default first.
    """
    from apps.accounts.models import UserAddress

    return UserAddress.objects.filter(user_id=user_id)





def get_user_address(*, user_id: int, address_id: int) -> "UserAddress":
    """
    Fetch a single address — enforce ownership.

    Args:
        user_id:    PK of the authenticated user.
        address_id: PK of the address to fetch.

    Returns:
        UserAddress instance.

    Raises:
        DomainError: Address not found or does not belong to user (400).
    """
    from apps.accounts.models import UserAddress

    try:
        return UserAddress.objects.get(pk=address_id, user_id=user_id)
    except UserAddress.DoesNotExist:
        logger.warning(
            "Address not found or ownership mismatch",
            extra={"user_id": user_id, "address_id": address_id},
        )
        raise DomainError(
            "Address not found.",
            code=ErrorCode.NOT_FOUND,
            status_code=400,
        )


def create_user_address(*, user_id: int, data: dict) -> "UserAddress":
    from apps.accounts.models import User, UserAddress

    log_context = {"user_id": user_id}

    try:
        user = User.objects.get(pk=user_id)
        address = UserAddress(user=user, **data)
        address.save()

        logger.info(
            "Address created successfully",
            extra={**log_context, "address_id": address.id},
        )
        return address

    except Exception:
        logger.exception(
            "Unexpected error during address creation",
            extra=log_context,
        )
        raise


def update_user_address(
    *,
    user_id: int,
    address_id: int,
    data: dict,
) -> "UserAddress":
    log_context = {"user_id": user_id, "address_id": address_id}

    address = get_user_address(user_id=user_id, address_id=address_id)

    try:
        with transaction.atomic():
            for field, value in data.items():
                setattr(address, field, value)
            address.save()

            logger.info(
                "Address updated successfully",
                extra=log_context,
            )
            return address

    except DomainError:
        raise

    except Exception:
        logger.exception(
            "Unexpected error during address update transaction.",
            extra=log_context,
        )
        raise


def delete_user_address(*, user_id: int, address_id: int) -> None:
    """
    Delete an address — enforce ownership.

    Args:
        user_id:    PK of the authenticated user.
        address_id: PK of the address to delete.

    Raises:
        DomainError: Address not found (400).
        Exception:   Any unexpected error is logged and re-raised.
    """
    log_context = {"user_id": user_id, "address_id": address_id}

    # Raises DomainError if not found or not owned
    address = get_user_address(user_id=user_id, address_id=address_id)

    try:
        address.delete()
        logger.info(
            "Address deleted successfully",
            extra=log_context,
        )

    except Exception:
        logger.exception(
            "Unexpected error during address deletion",
            extra=log_context,
        )
        raise


def set_default_address(*, user_id: int, address_id: int) -> "UserAddress":
    """
    Set an address as the user's default — enforce ownership.

    Delegates atomic default swap to UserAddress.set_as_default()
    which uses SELECT FOR UPDATE to prevent race conditions.

    Args:
        user_id:    PK of the authenticated user.
        address_id: PK of the address to set as default.

    Returns:
        Updated UserAddress instance.

    Raises:
        DomainError: Address not found (400).
        Exception:   Any unexpected error is logged and re-raised.
    """
    log_context = {"user_id": user_id, "address_id": address_id}

    # Raises DomainError if not found or not owned
    address = get_user_address(user_id=user_id, address_id=address_id)

    try:
        address.set_as_default()
        logger.info(
            "Default address updated successfully",
            extra=log_context,
        )
        return address

    except Exception:
        logger.exception(
            "Unexpected error setting default address",
            extra=log_context,
        )
        raise