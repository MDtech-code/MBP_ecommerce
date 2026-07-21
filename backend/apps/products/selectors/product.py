# apps/products/selectors/product.py
from __future__ import annotations

"""
Product selectors — DB queries only.

RESPONSIBILITY
──────────────
All Product-related database queries live here and only here.
Returns QuerySets or model instances.
Zero business logic. Zero serialization. Zero HTTP concerns.
Zero DRF imports.

QUERY DESIGN NOTES
──────────────────
Product list queries use .distinct() because compatible_bikes is M2M.
A product fitting 3 bike models appears 3 times in the JOIN result.
.distinct() collapses duplicates — critical for correct pagination counts.

All prefetch_related calls include select_related on nested querysets
to prevent N+1 on serializer field access (brand.name inside BikeModel, etc.)
"""

import logging
from typing import Optional

from django.db.models import Q, QuerySet
from django.db.models import Prefetch

from apps.products.models import BikeModel, Product

logger = logging.getLogger("apps.products")


def get_product_list_queryset(
    *,
    category_slug: Optional[str] = None,
    brand_slug: Optional[str] = None,
    bike_model_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search_query: Optional[str] = None,
    featured_only: bool = False,
    order_by: str = "-created_at",
) -> QuerySet:
    """
    Build and return a filtered, sorted Product QuerySet for list endpoints.

    All params are keyword-only — prevents positional argument confusion
    when caller passes 6+ filter values.

    Args:
        category_slug : filter by category.slug
        brand_slug    : filter by brand.slug
        bike_model_id : filter by compatible_bikes FK — triggers .distinct()
        min_price     : price__gte filter (already validated by caller)
        max_price     : price__lte filter (already validated by caller)
        search_query  : icontains search across name, description, sku
        featured_only : filter is_featured=True
        order_by      : ORM order_by string from SORT_OPTIONS

    Returns:
        Lazy QuerySet — not evaluated until caller slices for pagination.

    Why only AVAILABLE status:
        List endpoint never shows out_of_stock or discontinued products.
        Admin views use unfiltered querysets directly.

    Why select_related("category", "brand"):
        ProductListSerializer accesses category.name and brand.name.
        Without this — N+1, one query per product row.

    Why prefetch_related("images") and compatible_bikes with select_related:
        ProductListSerializer.get_primary_image() and get_primary_bike()
        both call .all() on prefetched relations.
        Without prefetch — one query per product for images + one for bikes.

    Why .distinct():
        compatible_bikes is M2M. Filtering by bike_model_id causes a JOIN.
        A product compatible with 3 bikes appears 3 times in JOIN result.
        .distinct() collapses duplicates — mandatory for correct count + pagination.
        Applied always (not just when bike_model_id set) — defensive, no cost.
    """
    queryset = (
        Product.objects
        .filter(status=Product.Status.AVAILABLE)
        .select_related("category", "brand")
        .prefetch_related(
            "images",
            Prefetch(
                "compatible_bikes",
                queryset=BikeModel.objects.select_related("brand"),
            ),
        )
        .order_by(order_by)
        .distinct()
    )

    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)

    if brand_slug:
        queryset = queryset.filter(brand__slug=brand_slug)

    if bike_model_id is not None:
        queryset = queryset.filter(compatible_bikes__id=bike_model_id)

    if min_price is not None:
        queryset = queryset.filter(price__gte=min_price)

    if max_price is not None:
        queryset = queryset.filter(price__lte=max_price)

    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(sku__icontains=search_query)
        )

    if featured_only:
        queryset = queryset.filter(is_featured=True)

    return queryset


def get_product_detail_queryset() -> QuerySet:
    """
    Return base QuerySet for single product detail retrieval.

    Why select_related("category__parent"):
        CategoryFlatSerializer includes parent_name for breadcrumb.
        category__parent fetches both category and its parent in ONE JOIN.
        Without __parent — separate query when serializer accesses obj.parent.

    Why select_related("brand"):
        ProductDetailSerializer nests full BrandSerializer.
        brand fields accessed — must be joined.

    Why Prefetch compatible_bikes with select_related("brand"):
        BikeModelSerializer accesses brand.name per compatible bike.
        Without select_related inside prefetch — N+1 per bike.

    Why prefetch "images":
        ProductImageSerializer renders full gallery.
        Multiple images per product — prefetch prevents N+1.

    Callers:
        ProductDetailAPIView.get() — passes .get(slug=slug) after this.
    """
    return (
        Product.objects
        .select_related("category__parent", "brand")
        .prefetch_related(
            "images",
            Prefetch(
                "compatible_bikes",
                queryset=BikeModel.objects.select_related("brand"),
            ),
            "specifications",
        )
    )