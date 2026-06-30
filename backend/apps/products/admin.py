from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Category, Brand, BikeModel, Product, ProductImage


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent", "is_subcategory", "is_active", "created_at"]
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "logo_preview", "is_active", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]

    def logo_preview(self, obj: Brand) -> str:
        if obj.logo:
            return format_html(
                '<img src="{}" style="height: 30px;" />', obj.logo.url
            )
        return "—"
    logo_preview.short_description = _("Logo")


@admin.register(BikeModel)
class BikeModelAdmin(admin.ModelAdmin):
    list_display = ["display_name", "brand", "year_start", "year_end", "is_active"]
    list_filter = ["brand", "is_active"]
    search_fields = ["name", "brand__name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["brand__name", "name"]
    autocomplete_fields = ["brand"]


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    fields = ["image", "is_primary", "order"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name", "sku", "category", "brand",
        "current_price", "stock", "status", "is_featured",
    ]
    list_filter = ["status", "category", "brand", "is_featured"]
    search_fields = ["name", "sku", "description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["category", "brand", "compatible_bikes"]
    inlines = [ProductImageInline]
    readonly_fields = ["created_by"]
    ordering = ["-created_at"]

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "sku", "description")
        }),
        (_("Classification"), {
            "fields": ("category", "brand", "compatible_bikes")
        }),
        (_("Pricing & Stock"), {
            "fields": ("price", "discount_price", "stock", "status")
        }),
        (_("Visibility"), {
            "fields": ("is_featured",)
        }),
        (_("Meta"), {
            "fields": ("created_by",),
            "classes": ("collapse",),
        }),
    )

    def save_model(self, request, obj: Product, form, change: bool) -> None:
        """Auto-assign created_by to the logged in admin on creation."""
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ["product", "is_primary", "order", "created_at"]
    list_filter = ["is_primary"]
    search_fields = ["product__name"]
    autocomplete_fields = ["product"]