# apps/products/services/brand_service.py
from __future__ import annotations

"""
Brand service — business operations for brands.

RESPONSIBILITY
──────────────
Business logic and side-effect orchestration for Brand.

Currently: cache invalidation only.

Future candidates:
    - safe_delete: check if brand has active products before deleting
    - merge_brands: reassign all products from one brand to another
    - bulk_activate / bulk_deactivate

Zero DRF imports. Zero serializer calls.
Pure Python and Django ORM only.
"""

import logging

from apps.core.cache import two_level_cache
from apps.products.constants import BRANDS_CACHE_KEY

logger = logging.getLogger("apps.products")


class BrandService:
    """
    Business operations for Brand.

    Why a class not module-level functions:
        Groups related operations under one namespace.
        Easier to mock in unit tests.
        Consistent pattern with CategoryService.
    """

    @staticmethod
    def invalidate_cache() -> None:
        """
        Invalidate the brand list cache.

        Called by:
            signals.py on Brand post_save (created or updated)
            signals.py on Brand post_delete

        Why service owns this and not signals directly:
            Cache key lives in constants.py.
            Service is the single place that knows how to invalidate
            Brand-related caches. If we add more brand cache keys in
            future (e.g. brand detail cache), we add invalidation here
            — signals stay unchanged.
        """
        two_level_cache.delete(BRANDS_CACHE_KEY)
        logger.info(
            "BrandService.invalidate_cache: brand list cache cleared"
        )