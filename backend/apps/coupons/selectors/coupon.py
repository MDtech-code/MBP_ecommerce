# apps/coupons/selectors/coupon.py
from __future__ import annotations

"""
Coupon selectors — database reads for coupon retrieval.

Responsibility:
    All coupon-related database queries live here.
    Returns model instances only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Dependency direction:
    models → selectors → services → views
"""

import logging
from typing import TYPE_CHECKING

from apps.coupons.models import Coupon

if TYPE_CHECKING:
    from apps.cart.models import Cart

logger = logging.getLogger("apps.coupons")


def get_coupon_by_code(code: str) -> Coupon:
    """
    Fetch a single active coupon by its code.

    Uppercases the code before querying — codes are always
    stored uppercase via Coupon.save() strip+upper logic.

    Args:
        code: Raw coupon code string entered by user.

    Returns:
        Coupon instance matching the code and is_active=True.

    Raises:
        Coupon.DoesNotExist — caller handles as DomainError 400.

    Why is_active=True in filter:
        Inactive coupons are soft-disabled by admin.
        They should behave as non-existent to the customer.
        A separate "inactive" error message would leak internal state.
    """
    return Coupon.objects.get(
        code=code.strip().upper(),
        is_active=True,
    )


def get_coupon_for_cart(cart: "Cart") -> Coupon | None:
    """
    Return the coupon currently applied to a cart, or None.

    Uses select_related to fetch the coupon in the same query
    as the cart — avoids an extra query when coupon fields are accessed
    during financial calculations in the checkout service.

    Args:
        cart: Cart instance (already fetched by caller).

    Returns:
        Coupon instance if one is applied, None otherwise.

    Callers:
        OrderService.checkout() — reads cart coupon before atomic block.
    """
    if not cart.coupon_id:
        return None

    return (
        Coupon.objects
        .filter(pk=cart.coupon_id)
        .first()
    )