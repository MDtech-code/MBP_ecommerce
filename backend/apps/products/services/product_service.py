# apps/products/services/product_service.py
from __future__ import annotations

"""
Product service — business operations for products.

RESPONSIBILITY
──────────────
Business logic and side-effect orchestration for Product and ProductImage.

Currently: cache invalidation only.

Future candidates:
    - deduct_stock(product, quantity): atomic stock deduction at checkout
    - restore_stock(product, quantity): atomic restore on order cancel/RTO
    - create_low_stock_alert(product): triggered by post_save signal
    - check_reservation_conflict(product, quantity, user): before checkout

Zero DRF imports. Zero serializer calls.
Pure Python and Django ORM only.

WHY TWO INVALIDATION METHODS
──────────────────────────────
List cache  → prefix delete (hundreds of filter+sort+page combinations)
Detail cache → exact key delete (one key per product slug)

Both are needed because a product change affects both:
    - The listing where it appeared
    - Its own detail page
"""

import logging

from apps.core.cache import two_level_cache
from apps.products.constants import (
    PRODUCT_DETAIL_CACHE_PREFIX,
    PRODUCTS_LIST_CACHE_PREFIX,
)

logger = logging.getLogger("apps.products")


class ProductService:
    """
    Business operations for Product and ProductImage.

    Why ProductImage invalidation lives here and not in ImageService:
        ProductImage changes affect Product caches (list + detail).
        The affected resource IS the product — not the image.
        Grouping both under ProductService keeps invalidation logic
        in one place. No ImageService is needed.
    """

    @staticmethod
    def invalidate_list_cache() -> None:
        """
        Invalidate ALL product list cache keys via prefix delete.

        Why prefix delete:
            List cache key encodes every filter+sort+page combination.
            Any product change makes ALL list variants potentially stale
            (the product could appear on any page, any filter combo).
            Prefix delete clears all variants in one SCAN pass.

        Called by:
            signals.py on Product post_save / post_delete
            signals.py on ProductImage post_save / post_delete
        """
        two_level_cache.delete(PRODUCTS_LIST_CACHE_PREFIX)
        logger.info(
            "ProductService.invalidate_list_cache: "
            "all product list cache keys cleared | prefix=%s",
            PRODUCTS_LIST_CACHE_PREFIX,
        )

    @staticmethod
    def invalidate_detail_cache(slug: str) -> None:
        """
        Invalidate the detail cache for a specific product slug.

        Why exact key not prefix:
            Each product has its own detail key.
            Only THIS product's cache needs clearing.
            Other product detail caches stay warm.

        Args:
            slug: Product.slug — used to build the exact cache key.

        Called by:
            signals.py on Product post_save / post_delete (instance.slug)
            signals.py on ProductImage post_save / post_delete (instance.product.slug)
        """
        cache_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}"
        two_level_cache.delete(cache_key)
        logger.info(
            "ProductService.invalidate_detail_cache: "
            "product detail cache cleared | slug=%s key=%s",
            slug,
            cache_key,
        )