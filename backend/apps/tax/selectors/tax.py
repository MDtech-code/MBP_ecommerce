# apps/tax/selectors/tax.py
from __future__ import annotations

"""
Tax selectors — database reads for tax rate retrieval.

Responsibility:
    All TaxRate-related database queries live here.
    Returns Decimal values only — no model instances exposed to callers.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Dependency direction:
    models → selectors → services → views
"""

import logging
from datetime import date
from decimal import Decimal

from apps.tax.models import TaxRate

logger = logging.getLogger("apps.tax")


def get_tax_rate_for_category(category_id: int) -> Decimal:
    """
    Return the most recent active GST rate for a product category.

    Queries TaxRate records filtered by category, active status,
    and effective_from on or before today. Orders by most recent
    effective_from descending so .first() returns the current rate.

    Returns Decimal("0.00") when no rate is configured — treats
    unconfigured categories as GST exempt. Admin is responsible
    for configuring explicit rates per FBR category assignment.

    Why effective_from__lte=date.today():
        FBR GST rates change over time. A rate entered today for
        next month must not apply until that date. This filter
        ensures only rates already in effect are returned.

    Why no parent category fallback:
        FBR requires explicit rate assignment per category.
        Implicit inheritance could silently apply the wrong tax
        when new subcategories are added without a rate configured.

    Args:
        category_id: Primary key of the product's Category.

    Returns:
        Decimal rate percentage e.g. Decimal("17.00"), or
        Decimal("0.00") if no active rate exists for this category.
    """
    rate = (
        TaxRate.objects
        .filter(
            category_id=category_id,
            is_active=True,
            effective_from__lte=date.today(),
        )
        .order_by("-effective_from")
        .first()
    )

    if rate is None:
        logger.debug(
            "get_tax_rate_for_category: no active rate found | "
            "category_id=%s — returning 0.00 (GST exempt treatment)",
            category_id,
        )
        return Decimal("0.00")

    logger.debug(
        "get_tax_rate_for_category: rate found | "
        "category_id=%s rate=%s%% effective_from=%s",
        category_id,
        rate.rate_percentage,
        rate.effective_from,
    )

    return rate.rate_percentage