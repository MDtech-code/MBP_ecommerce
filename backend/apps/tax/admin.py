# apps/tax/admin.py
from __future__ import annotations

import logging

from django.contrib import admin
from django.http import HttpRequest

from apps.tax.models import TaxRate

logger = logging.getLogger("apps.tax")


@admin.register(TaxRate)
class TaxRateAdmin(admin.ModelAdmin):
    """
    TaxRate admin — manages GST rates per product category.

    Tax rates are admin-managed only — no REST endpoints.
    Rates are snapshotted on OrderItem at checkout time via
    get_tax_rate_for_category() selector, so changing a rate
    here does not affect existing orders.

    Only one active rate per category should exist at any time.
    effective_from controls which rate applies — most recent
    active rate is selected by the selector.
    """

    list_display = [
        "id",
        "category",
        "tax_type",
        "rate_percentage",
        "is_active",
        "effective_from",
        "created_at",
    ]
    list_filter = [
        "tax_type",
        "is_active",
        "effective_from",
    ]
    search_fields = [
        "category__name",
    ]
    ordering = [
        "category__name",
        "-effective_from",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    fieldsets = [
        (
            "Tax Rate",
            {
                "fields": [
                    "category",
                    "tax_type",
                    "rate_percentage",
                    "is_active",
                    "effective_from",
                ]
            },
        ),
        (
            "Timestamps",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: TaxRate | None = None,
    ) -> bool:
        """
        Prevent deletion of tax rates — financial compliance record.

        Deactivate rates via is_active=False instead of deleting.
        FBR requires tax records to be retained for audit.
        """
        return False