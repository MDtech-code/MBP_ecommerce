# apps/cart/admin.py
from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Cart, CartItem


# ─── Inlines ──────────────────────────────────────────────────────────────────

class CartItemInline(admin.TabularInline):
    """
    Inline editor for CartItems within the Cart admin page.

    Displays all items in the cart with product, quantity,
    and computed subtotal. subtotal is read-only — it is a
    @property computed from product price and quantity.

    Adding/removing items via inline is allowed for admin
    support purposes (e.g. correcting a stuck cart).
    """

    model = CartItem
    extra = 0
    fields = [
        "product",
        "quantity",
        "display_subtotal",
    ]
    readonly_fields = ["display_subtotal"]

    @admin.display(description=_("Subtotal"))
    def display_subtotal(self, obj: CartItem) -> str:
        """
        Render subtotal @property as a formatted string column.

        @property cannot be used directly in readonly_fields —
        must be wrapped in an admin method.
        """
        return f"PKR {obj.subtotal:,.2f}"


# ─── Cart Admin ───────────────────────────────────────────────────────────────

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    """
    Admin interface for Cart.

    Displays computed properties (total_items, total_price, is_empty)
    as boolean/display columns. All properties require explicit
    admin method wrappers to render correctly in list_display.

    Why readonly user field:
        Cart ownership must not be reassigned via admin — it would
        leave the previous user with no cart (signal only fires on
        user creation, not cart reassignment).
    """

    inlines = [CartItemInline]

    # ── List view ─────────────────────────────────────────────────────────────
    list_display = [
        "user",
        "display_total_items",
        "display_total_price",
        "display_is_empty",
        "created_at",
        "updated_at",
    ]
    search_fields = ["user__email", "user__full_name"]
    list_filter = ["created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    list_per_page = 50
    show_full_result_count = False

    # ── Detail view ───────────────────────────────────────────────────────────
    readonly_fields = [
        "user",
        "display_total_items",
        "display_total_price",
        "display_is_empty",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            _("Ownership"),
            {
                "fields": ("user",),
            },
        ),
        (
            _("Summary"),
            {
                "fields": (
                    "display_total_items",
                    "display_total_price",
                    "display_is_empty",
                ),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def has_add_permission(self, request) -> bool:
        """
        Disable manual cart creation via admin.

        Carts are created automatically via post_save signal
        when a User is created. Manual creation would bypass
        this and could create orphaned or duplicate carts.
        """
        return False

    @admin.display(description=_("Total Items"))
    def display_total_items(self, obj: Cart) -> int:
        """Render total_items @property as a column."""
        return obj.total_items

    @admin.display(description=_("Total Price"))
    def display_total_price(self, obj: Cart) -> str:
        """Render total_price @property as formatted currency string."""
        return f"PKR {obj.total_price:,.2f}"

    @admin.display(boolean=True, description=_("Empty"))
    def display_is_empty(self, obj: Cart) -> bool:
        """Render is_empty @property as a boolean icon column."""
        return obj.is_empty


# ─── CartItem Admin ───────────────────────────────────────────────────────────

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    """
    Admin interface for CartItem.

    Provides direct access to individual cart items for
    support purposes (e.g. removing a stuck item that
    the user cannot remove via the frontend).

    subtotal is read-only — computed @property.
    """

    list_display = [
        "display_user",
        "product",
        "quantity",
        "display_subtotal",
        "created_at",
    ]
    search_fields = [
        "cart__user__email",
        "cart__user__full_name",
        "product__name",
    ]
    list_filter = ["created_at"]
    ordering = ["-created_at"]
    date_hierarchy = "created_at"
    list_per_page = 50
    show_full_result_count = False

    readonly_fields = [
        "display_subtotal",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            _("Cart & Product"),
            {
                "fields": ("cart", "product", "quantity"),
            },
        ),
        (
            _("Computed"),
            {
                "fields": ("display_subtotal",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("User"))
    def display_user(self, obj: CartItem) -> str:
        """Show the cart owner's email in list_display."""
        return obj.cart.user.email

    @admin.display(description=_("Subtotal"))
    def display_subtotal(self, obj: CartItem) -> str:
        """Render subtotal @property as formatted currency string."""
        return f"PKR {obj.subtotal:,.2f}"
