# apps/wishlist/services/wishlist_service.py
from __future__ import annotations

"""
Wishlist service — business logic for wishlist operations.

Responsibility:
    WishlistService.add_item()    — adds a product to user's wishlist.
    WishlistService.remove_item() — removes a product from user's wishlist.

    All business rule validation lives here, not in serializers or views.
    Zero DRF imports. Zero HTTP concerns.

Uniqueness enforcement:
    add_item() checks for an existing WishlistItem before creating.
    DomainError 409 raised if item already in wishlist.
    This is checked at service layer — unique_together on the model
    is the database-level guard. Service check gives a clean error
    message before hitting the DB constraint.

Dependency direction:
    models → selectors → services → views
"""

import logging

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.wishlist.models import WishlistItem
from apps.wishlist.selectors.wishlist_selectors import get_wishlist_item

logger = logging.getLogger("apps.wishlist")


class WishlistService:
    """
    Business operations for wishlist management.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    """

    @staticmethod
    def add_item(
        *,
        user,
        product_id: int,
    ) -> WishlistItem:
        """
        Add a product to the user's wishlist.

        Validates that the product is not already in the wishlist
        before creating the WishlistItem. Raises DomainError 409
        if the item already exists.

        Product existence is not validated here — the ForeignKey
        constraint on WishlistItem will raise IntegrityError if
        the product does not exist, which surfaces as a 500.
        The view validates product existence via the serializer
        PrimaryKeyRelatedField before reaching this method.

        Args:
            user:       Authenticated user adding the item.
            product_id: Primary key of the product to add.

        Returns:
            Created WishlistItem instance.

        Raises:
            DomainError 409 — product already in user's wishlist.
        """
        existing = get_wishlist_item(user, product_id)
        if existing is not None:
            raise DomainError(
                "This product is already in your wishlist.",
                code=ErrorCode.WISHLIST_ITEM_ALREADY_EXISTS,
                status_code=409,
            )

        wishlist_item = WishlistItem.objects.create(
            user=user,
            product_id=product_id,
        )

        logger.info(
            "WishlistService.add_item: added | "
            "user=%s product_id=%s wishlist_item_id=%s",
            user.pk,
            product_id,
            wishlist_item.pk,
        )

        return wishlist_item

    @staticmethod
    def remove_item(
        *,
        user,
        product_id: int,
    ) -> None:
        """
        Remove a product from the user's wishlist.

        Raises DomainError 404 if the item does not exist in
        the user's wishlist — either the product was never added
        or belongs to another user. Both cases return 404 to
        prevent wishlist item enumeration.

        Args:
            user:       Authenticated user removing the item.
            product_id: Primary key of the product to remove.

        Returns:
            None.

        Raises:
            DomainError 400 — item not found in user's wishlist.
        """
        existing = get_wishlist_item(user, product_id)
        if existing is None:
            raise DomainError(
                "This product is not in your wishlist.",
                code=ErrorCode.WISHLIST_ITEM_NOT_FOUND,
                status_code=400,
            )

        existing.delete()

        logger.info(
            "WishlistService.remove_item: removed | "
            "user=%s product_id=%s",
            user.pk,
            product_id,
        )