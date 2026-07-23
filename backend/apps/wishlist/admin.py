# apps/wishlist/admin.py
from __future__ import annotations

import logging

from django.contrib import admin
from django.http import HttpRequest

from apps.wishlist.models import WishlistItem

logger = logging.getLogger("apps.wishlist")


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    """
    WishlistItem admin — read-only view of customer wishlists.

    Used for analytics and customer support — staff can see what
    products customers have saved. No mutations from admin.

    Filtering by product allows identifying most-wishlisted items
    which is a demand signal for inventory planning.
    """

    list_display = [
        "id",
        "user_email",
        "product_name",
        "product_in_stock",
        "created_at",
    ]
    list_filter  = [
        "created_at",
        "product__category",
    ]
    search_fields = [
        "user__email",
        "product__name",
    ]
    ordering      = ["-created_at"]
    readonly_fields = [
        "user",
        "product",
        "created_at",
        "updated_at",
    ]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self,
        request: HttpRequest,
        obj: WishlistItem | None = None,
    ) -> bool:
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: WishlistItem | None = None,
    ) -> bool:
        return False

    def user_email(self, obj: WishlistItem) -> str:
        """Return user email for list display."""
        return getattr(obj.user, "email", "—")

    user_email.short_description = "Customer"  # type: ignore[attr-defined]

    def product_name(self, obj: WishlistItem) -> str:
        """Return product name for list display."""
        return getattr(obj.product, "name", "—")

    product_name.short_description = "Product"  # type: ignore[attr-defined]

    def product_in_stock(self, obj: WishlistItem) -> bool:
        """Return product stock status for quick demand signal view."""
        return getattr(obj.product, "is_in_stock", False)

    product_in_stock.short_description = "In Stock"  # type: ignore[attr-defined]
    product_in_stock.boolean           = True         # type: ignore[attr-defined]