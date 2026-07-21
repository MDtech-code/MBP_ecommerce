# apps/products/selectors/brand.py
from __future__ import annotations

"""
Brand selectors — DB queries only.

RESPONSIBILITY
──────────────
All Brand-related database queries live here and only here.
Returns QuerySets or model instances.
Zero business logic. Zero serialization. Zero HTTP concerns.
Zero DRF imports.
"""

import logging

from django.db.models import QuerySet

from apps.products.models import Brand

logger = logging.getLogger("apps.products")


def list_active_brands() -> QuerySet:
    """
    Return an optimized QuerySet of all active brands.

    Why order_by("name"):
        Without explicit ordering, DB may return different row orders
        across requests depending on query planner decisions.
        Deterministic ordering = stable cache payload = no phantom
        cache misses caused by reordered identical data.

    Why no select_related or annotate:
        Brand has no FK fields needed for serialization.
        BrandSerializer only needs id, name, slug, logo, is_active —
        all native Brand fields, no joins required.

    DB cost: 1 query, no joins.

    Callers:
        BrandListAPIView.get() on cache miss.
    """
    return (
        Brand.objects
        .filter(is_active=True)
        .order_by("name")
    )


def get_brand_by_slug(slug: str) -> Brand:
    """
    Return a single active Brand instance by slug.

    Raises:
        Brand.DoesNotExist — caller decides the HTTP response shape.
        Never catch here — let it propagate.

    Callers:
        Future: BrandDetailAPIView
    """
    return Brand.objects.filter(is_active=True).get(slug=slug)