# apps/coupons/admin.py
from __future__ import annotations

"""
Coupons app — Django admin registration.

Allows admin to create, edit, and monitor coupons and their usage records.
CouponUsage is a financial record — has_delete_permission=False enforced.
Coupon.save() calls full_clean() automatically — admin form validation
is handled by the model itself.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Coupon, CouponUsage


# ─────────────────────────────────────────────────────────────────────────────
# COUPON USAGE INLINE
# ─────────────────────────────────────────────────────────────────────────────


class CouponUsageInline(admin.TabularInline):
    """
    Displays all redemption records for a coupon inline on its admin page.

    CouponUsage is a financial record — no deletion permitted.
    All fields readonly — usage records are immutable evidence.
    """

    model = CouponUsage
    extra = 0
    can_delete = False
    readonly_fields = [
        "user",
        "order",
        "discount_applied",
        "created_at",
    ]
    fields = [
        "user",
        "order",
        "discount_applied",
        "created_at",
    ]

    def has_add_permission(self, request, obj=None) -> bool:
        """
        CouponUsage records are created only via checkout service.
        Manual creation via admin is not permitted.
        """
        return False


# ─────────────────────────────────────────────────────────────────────────────
# COUPON ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    """
    Admin interface for Coupon creation and management.

    Admins create coupons here. Coupon.save() calls full_clean()
    automatically — validation (date range, discount type constraints)
    is enforced at the model level before any DB write.

    times_used and total_used are readonly — managed exclusively
    by OrderService.checkout() and cancel_order() via F() expressions.
    """

    list_display = [
        "code",
        "discount_type",
        "discount_value",
        "min_order_amount",
        "usage_limit_total",
        "usage_limit_per_user",
        "times_used",
        "total_used_display",
        "valid_from",
        "valid_until",
        "is_active",
        "is_currently_valid",
    ]
    list_filter = [
        "discount_type",
        "is_active",
        "valid_from",
        "valid_until",
    ]
    search_fields = [
        "code",
    ]
    readonly_fields = [
        "times_used",
        "total_used_display",
        "is_currently_valid",
        "created_at",
        "updated_at",
    ]
    fieldsets = [
        (
            _("Coupon Identity"),
            {
                "fields": [
                    "code",
                    "is_active",
                ],
            },
        ),
        (
            _("Discount Configuration"),
            {
                "fields": [
                    "discount_type",
                    "discount_value",
                    "max_discount_amount",
                    "min_order_amount",
                ],
                "description": _(
                    "For PERCENTAGE: enter 0–100. "
                    "For FIXED_PKR: enter PKR amount. "
                    "For FREE_SHIPPING: discount_value must be 0."
                ),
            },
        ),
        (
            _("Usage Limits"),
            {
                "fields": [
                    "usage_limit_total",
                    "usage_limit_per_user",
                    "times_used",
                    "total_used_display",
                ],
            },
        ),
        (
            _("Validity Window"),
            {
                "fields": [
                    "valid_from",
                    "valid_until",
                    "is_currently_valid",
                ],
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ],
                "classes": ["collapse"],
            },
        ),
    ]
    inlines = [CouponUsageInline]

    def total_used_display(self, obj: Coupon) -> int:
        """
        Show authoritative usage count from CouponUsage records.

        total_used property counts CouponUsage records — always accurate.
        times_used is the fast pre-check counter — may diverge after
        cancellations. Both displayed so admin can compare them.
        """
        return obj.total_used

    total_used_display.short_description = _("Total Used (Authoritative)")

    def is_currently_valid(self, obj: Coupon) -> bool:
        """Display whether coupon is within its validity window right now."""
        return obj.is_currently_valid

    is_currently_valid.short_description = _("Currently Valid")
    is_currently_valid.boolean = True

    def save_model(self, request, obj, form, change) -> None:
        """
        Coupon.save() calls full_clean() automatically.
        Admin save flows through model validation before DB write.
        Code is stripped and uppercased in Coupon.save() — no
        manual normalization needed here.
        """
        obj.save()


# ─────────────────────────────────────────────────────────────────────────────
# COUPON USAGE ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    """
    Admin interface for CouponUsage — financial records.

    Read-only view only — CouponUsage records are created exclusively
    by OrderService.checkout() and must never be manually created
    or deleted. Deletion would allow coupon reuse after cancellation.
    """

    list_display = [
        "coupon",
        "user",
        "order",
        "discount_applied",
        "created_at",
    ]
    list_filter = [
        "coupon",
        "created_at",
    ]
    search_fields = [
        "coupon__code",
        "user__email",
        "order__order_number",
    ]
    readonly_fields = [
        "coupon",
        "user",
        "order",
        "discount_applied",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request) -> bool:
        """
        CouponUsage records are created only via checkout service.
        Manual creation not permitted.
        """
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """
        CouponUsage is a financial record — deletion not permitted.
        Deletion would allow coupon reuse after order cancellation.
        """
        return False