# apps/wishlist/selectors/wishlist_selectors.py
from __future__ import annotations

"""
Wishlist selectors — all database reads for the wishlist app.

Responsibility:
    Every query that touches WishlistItem lives here.
    Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Ownership enforcement:
    All selectors scope by user — customers only see and act
    on their own wishlist items. A valid item belonging to
    another user raises WishlistItem.DoesNotExist, not 403.
    This prevents wishlist item ID enumeration attacks.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db.models import QuerySet

from apps.wishlist.models import WishlistItem

logger = logging.getLogger("apps.wishlist")


def get_wishlist_items(user) -> QuerySet:
    """
    Return all WishlistItems for the requesting user.

    Selects related product to avoid N+1 on serialization.
    Ordered by most recently added first (model Meta default).

    Args:
        user: Authenticated user whose wishlist to retrieve.

    Returns:
        QuerySet of WishlistItem instances with product loaded.
    """
    return (
        WishlistItem.objects
        .select_related("product", "product__category")
        .filter(user=user)
        .order_by("-created_at")
    )


def get_wishlist_item(
    user,
    product_id: int,
) -> WishlistItem | None:
    """
    Return a single WishlistItem for the user and product, or None.

    Used by WishlistService to check existence before add/remove.
    Ownership enforced by user filter — returns None for items
    belonging to other users rather than raising PermissionDenied.

    Args:
        user:       Authenticated user.
        product_id: Product primary key.

    Returns:
        WishlistItem instance if found, else None.
    """
    return (
        WishlistItem.objects
        .filter(user=user, product_id=product_id)
        .first()
    )