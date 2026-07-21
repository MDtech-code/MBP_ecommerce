# apps/products/services/product_service.py
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from apps.products.models import Product
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
    



    @staticmethod
    def create_low_stock_alert(instance: "Product") -> None:
        """
        Create a LowStockAlert if product is low on stock and no
        unresolved alert already exists for it.

        Why check for existing unresolved alert:
            Stock can drop multiple times while already below threshold.
            10 → 4 → 3 → 2 → 1 with threshold=5 should produce ONE alert.
            Without this guard, admin inbox floods with duplicate alerts
            for the same restock action required.

        Why create here not in signal:
            Service owns business logic. Signal is just the trigger.
            This method is independently testable without firing signals.
            Future: management command or admin action can also call this.

        Why import inside method:
            LowStockAlert imports Product (FK).
            product_service.py imports Product for type hint.
            Top-level import of LowStockAlert here would not cause circular
            import but keeping model imports local to where they are used
            is cleaner — service does not need to declare all models at top.

        Args:
            instance: Product instance after save — is_low_stock already
                      computed from current stock and threshold values.
        """
        from apps.products.models import LowStockAlert

        if not instance.is_low_stock:
            return

        already_alerted = LowStockAlert.objects.filter(
            product=instance,
            is_resolved=False,
        ).exists()

        if already_alerted:
            logger.debug(
                "ProductService.create_low_stock_alert: "
                "unresolved alert already exists | product_id=%s stock=%s",
                instance.pk,
                instance.stock,
            )
            return

        LowStockAlert.objects.create(
            product=instance,
            stock_at_alert=instance.stock,
            threshold_at_alert=instance.low_stock_threshold,
        )
        logger.warning(
            "ProductService.create_low_stock_alert: "
            "alert created | product_id=%s name=%s stock=%s threshold=%s",
            instance.pk,
            instance.name,
            instance.stock,
            instance.low_stock_threshold,
        )


    