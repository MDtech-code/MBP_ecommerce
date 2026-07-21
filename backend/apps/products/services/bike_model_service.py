# apps/products/services/bike_model_service.py
from __future__ import annotations

"""
BikeModel service — business operations for bike models.

RESPONSIBILITY
──────────────
Business logic and side-effect orchestration for BikeModel.

Currently: cache invalidation only.

Future candidates:
    - validate_year_range: enforce year_end >= year_start at service level
    - find_compatible_products: given a bike model, return matching products
    - bulk_deactivate_by_brand: when a brand is deactivated

Zero DRF imports. Zero serializer calls.
Pure Python and Django ORM only.

WHY PREFIX DELETE FOR BIKE MODELS
───────────────────────────────────
Brand list has ONE cache key → single delete.

Bike model list has MANY cache keys — one per brand filter combination:
    products_bike_models_brand_all
    products_bike_models_brand_1
    products_bike_models_brand_2
    products_bike_models_brand_N

We cannot know at invalidation time which brand keys exist in cache.
Prefix delete clears ALL variants in one operation using SCAN.
This is safe — SCAN does not block Redis unlike KEYS *.
"""

import logging

from apps.core.cache import two_level_cache
from apps.products.constants import BIKE_MODELS_CACHE_PREFIX

logger = logging.getLogger("apps.products")


class BikeModelService:
    """
    Business operations for BikeModel.

    Why a class:
        Consistent pattern with CategoryService and BrandService.
        Future methods (find_compatible_products, etc.) belong here.
    """

    @staticmethod
    def invalidate_cache() -> None:
        """
        Invalidate ALL bike model cache keys via prefix delete.

        Why prefix delete:
            Bike model cache is keyed per brand filter combination.
            Any change to any BikeModel must bust ALL brand variants
            because we cannot know which specific keys are warm.

            Example: if BikeModel with brand_id=3 is updated,
            the "brand_all" key is stale AND the "brand_3" key is stale.
            Prefix delete clears both (and any others) in one SCAN pass.

        Called by:
            signals.py on BikeModel post_save (created or updated)
            signals.py on BikeModel post_delete
        """
        two_level_cache.delete(BIKE_MODELS_CACHE_PREFIX)
        logger.info(
            "BikeModelService.invalidate_cache: "
            "all bike model cache keys cleared | prefix=%s",
            BIKE_MODELS_CACHE_PREFIX,
        )