# apps/cart/selectors/cart.py
from __future__ import annotations

"""
Cart selectors — DB queries only.

RESPONSIBILITY
──────────────
All Cart-related database queries live here and only here.
Returns model instances or QuerySets.
Zero business logic. Zero serialization. Zero HTTP concerns.
Zero DRF imports.
"""

import logging

from django.db.models import Prefetch

from apps.cart.models import Cart, CartItem

logger = logging.getLogger("apps.cart")


def get_cart_with_items(user) -> Cart:
    """
    Fetch the authenticated user's cart with full prefetch chain.

    Prefetch chain:
        items                    → all CartItems for this cart
        items__product           → Product per item (for price, name, slug)
        items__product__images   → ProductImages per product (for primary image)

    This single query pattern (1 cart + 2 prefetch queries = 3 total)
    prevents N+1 on CartSerializer and CartItemSerializer field access:
        item.product.name        → covered by items__product
        item.product.current_price → covered by items__product
        item.subtotal            → covered by items__product
        get_product_image()      → covered by items__product__images

    Why also select_related("coupon") on Cart:
        CartSerializer exposes coupon_id and coupon_code_input.
        coupon FK is nullable — select_related handles NULL gracefully.
        Without it: accessing cart.coupon fires an extra query per cart.

    Raises:
        Cart.DoesNotExist — caller (view) handles this as 500.
        Cart missing = post_save signal failure on user creation.
        This is a server-side defect, not a client error.

    Callers:
        CartDetailAPIView.get()
        CartService.add_item() — re-fetch after mutation
        CartService.update_item() — re-fetch after mutation
        CartService.clear_cart() — re-fetch after mutation
    """
    return (
        Cart.objects
        .select_related("coupon")
        .prefetch_related(
            Prefetch(
                "items",
                queryset=CartItem.objects.select_related(
                    "product"
                ).prefetch_related(
                    "product__images"
                ),
            )
        )
        .get(user=user)
    )


def get_cart_for_user(user) -> Cart:
    """
    Fetch the user's cart WITHOUT prefetch chain.

    Use for operations that do NOT need financial totals or item details:
        - Existence checks
        - Getting cart PK for FK references
        - Abandoned cart detection
        - Any write operation where re-fetch happens after the mutation

    Why separate from get_cart_with_items:
        Prefetching images for 20 cart items costs 3 queries minimum.
        For a write operation that immediately re-fetches anyway,
        this cheaper fetch avoids wasted prefetch overhead.

    Raises:
        Cart.DoesNotExist — caller handles as 500.
    """
    return Cart.objects.get(user=user)