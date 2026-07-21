# apps/products/selectors/bike_model.py
from __future__ import annotations

"""
BikeModel selectors — DB queries only.

RESPONSIBILITY
──────────────
All BikeModel-related database queries live here and only here.
Returns QuerySets or model instances.
Zero business logic. Zero serialization. Zero HTTP concerns.
Zero DRF imports.
"""

import logging
from typing import Optional

from django.db.models import QuerySet

from apps.products.models import BikeModel

logger = logging.getLogger("apps.products")


def list_active_bike_models(brand_id: Optional[int] = None) -> QuerySet:
    """
    Return an optimized QuerySet of active bike models.

    Args:
        brand_id: Optional brand PK to filter by.
                  None  → return all active models across all brands.
                  int   → return only models belonging to that brand.

    Why brand_id filter applied here in selector:
        The filter is a DB concern — it belongs in the query layer.
        The view passes the validated brand_id down.
        The selector applies it cleanly at the ORM level.

    Why select_related("brand"):
        BikeModelSerializer needs brand_name (source="brand.name").
        select_related resolves this in ONE query — no N+1.

    Why order_by("brand__name", "name"):
        Two-level sort: group by brand name first, then model name within.
        Deterministic ordering for stable cache payload.
        Also produces logical grouping in dropdown: all Honda models
        together, all Yamaha models together.

    DB cost: 1 query with JOIN on Brand.

    Callers:
        BikeModelListAPIView.get() on cache miss.
    """
    queryset = (
        BikeModel.objects
        .filter(is_active=True)
        .select_related("brand")
        .order_by("brand__name", "name")
    )

    if brand_id is not None:
        queryset = queryset.filter(brand_id=brand_id)

    return queryset


def get_bike_model_by_slug(slug: str) -> BikeModel:
    """
    Return a single active BikeModel instance by slug.

    Raises:
        BikeModel.DoesNotExist — caller decides the HTTP response shape.

    Callers:
        Future: BikeModelDetailAPIView
    """
    return (
        BikeModel.objects
        .filter(is_active=True)
        .select_related("brand")
        .get(slug=slug)
    )