# apps/products/services.py
from __future__ import annotations

"""
Product app — Service layer.

RESPONSIBILITY
──────────────
Business logic and orchestration only.
Services speak pure Python and Django ORM.
Services NEVER import DRF, serializers, or anything HTTP-related.

For CategoryService specifically:
    The only service responsibility here is cache invalidation.
    Data fetching (selector) and serialization (view) are NOT here.
    This is correct for a pure read endpoint with no business logic.

WHAT BELONGS IN SERVICES
────────────────────────
    - Multi-step write operations (create order + deduct stock + send email)
    - Business rule enforcement (can this user apply this coupon?)
    - Orchestration across multiple selectors
    - Cache invalidation (side effect of a write)

WHAT DOES NOT BELONG IN SERVICES
─────────────────────────────────
    - DRF serializer calls
    - request.data access
    - Response() construction
    - Cache reads for serving data (that is the view's job for reads)
"""

import logging

from apps.core.cache import two_level_cache

from apps.products.constants import (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
)

logger = logging.getLogger("apps.products")


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class CategoryService:
    """
    Business operations for categories.

    Currently: cache invalidation only.
    Future: safe_delete (checks for products before deleting),
            bulk_activate, merge categories, etc.

    Why a class:
        Groups related operations under one domain namespace.
        Makes it clear these methods share a business context.
        Easier to mock in unit tests than scattered module functions.
    """

    @staticmethod
    def invalidate_cache() -> None:
        """
        Invalidate both flat and tree category caches.

        Called by:
            - signals.py on post_save (category created or updated)
            - signals.py on post_delete (category deleted)

        Why both flat AND tree:
            Any change to any category affects both cached views.
            Flat has raw serialized data.
            Tree has the built hierarchy.
            Both must be cleared or stale data serves from cache.

        Why service owns this and not signals directly:
            If cache keys change, they change in ONE place.
            Signals stay thin and do not need to know key names.
            Service is testable in isolation without triggering signals.
        """
        two_level_cache.delete(CATEGORIES_FLAT_CACHE_KEY)
        two_level_cache.delete(CATEGORIES_TREE_CACHE_KEY)
        logger.info(
            "CategoryService.invalidate_cache: "
            "flat and tree caches cleared"
        )