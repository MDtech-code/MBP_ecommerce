# from __future__ import annotations

# from django.contrib import admin

# from .models import Cart, CartItem


# class CartItemInline(admin.TabularInline):
#     model = CartItem
#     extra = 0
#     readonly_fields = ["subtotal"]
#     fields = ["product", "quantity", "subtotal"]

#     def subtotal(self, obj: CartItem) -> str:
#         return f"Rs. {obj.subtotal:.2f}"
#     subtotal.short_description = "Subtotal"


# @admin.register(Cart)
# class CartAdmin(admin.ModelAdmin):
#     list_display = ["user", "total_items", "total_price", "updated_at"]
#     search_fields = ["user__email"]
#     inlines = [CartItemInline]
#     readonly_fields = ["total_items", "total_price"]


# @admin.register(CartItem)
# class CartItemAdmin(admin.ModelAdmin):
#     list_display = ["cart", "product", "quantity", "subtotal"]
#     search_fields = ["cart__user__email", "product__name"]
#     autocomplete_fields = ["cart", "product"]

#     def subtotal(self, obj: CartItem) -> str:
#         return f"Rs. {obj.subtotal:.2f}"
#     subtotal.short_description = "Subtotal"