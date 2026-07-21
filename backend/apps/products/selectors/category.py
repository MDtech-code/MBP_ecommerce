# apps/products/selectors/category.py
from __future__ import annotations

"""
Product app — Selector layer.

RESPONSIBILITY
──────────────
All database queries for the products app live here and ONLY here.
Views and services never import from models directly to run queries.
Selectors are pure query functions — they return QuerySets or serialized
data. They contain zero business logic and zero HTTP concerns.

DEPENDENCY DIRECTION
────────────────────
    models.py
        ↑
    selectors.py   ← this file
        ↑
    services.py
        ↑
    views.py

NAMING CONVENTION
─────────────────
    get_*        → returns a single object or raises DoesNotExist
    list_*       → returns a QuerySet (lazy, not yet evaluated)
    fetch_*      → evaluates the QuerySet, returns plain Python data
                   (used when result goes straight to cache/serializer)
"""

import logging

from django.db.models import Count, QuerySet

from apps.products.models import  Category

logger = logging.getLogger("apps.products")


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY SELECTORS
# ─────────────────────────────────────────────────────────────────────────────

def list_active_categories() -> QuerySet:
    """
    Return a QuerySet of all active categories optimized for serialization.

    Annotations and select_related included here so the view/serializer
    never needs to know about query optimization details.

    Callers:
        CategoryService.get_flat_categories()
        CategoryService.get_tree_categories()

    DB cost: 1 query — select_related + annotate run in single SQL.
    """
    return (
        Category.objects
        .filter(is_active=True)
        .select_related("parent")
        .annotate(subcategories_count=Count("subcategories"))
        .order_by("name")
    )


def get_category_by_slug(slug: str) -> Category:
    """
    Return a single active category by slug.

    Raises:
        Category.DoesNotExist — caller decides HTTP response shape.

    Callers:
        Future: CategoryDetailAPIView
    """
    return (
        Category.objects
        .filter(is_active=True)
        .select_related("parent")
        .annotate(subcategories_count=Count("subcategories"))
        .get(slug=slug)
    )