# apps/products/admin.py
from __future__ import annotations

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    BikeModel,
    Brand,
    Category,
    LowStockAlert,
    Product,
    ProductImage,
    ProductSpecification,
    StockReservation,
)


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "parent",
        "is_subcategory",
        "subcategory_count",
        "is_active",
        "created_at",
    ]
    list_filter    = ["is_active", "parent"]
    list_editable  = ["is_active"]
    search_fields  = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering       = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "slug", "parent", "is_active"),
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

    @admin.display(description=_("Children"))
    def subcategory_count(self, obj: Category) -> int:
        """Shows child count in list — helps admin spot large branches."""
        return obj.subcategories.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("parent"): list_display has "parent" column.
        Without this — N+1, one query per row to fetch parent name.
        """
        return super().get_queryset(request).select_related("parent")

    def formfield_for_foreignkey(self, db_field, request: HttpRequest, **kwargs):
        """
        Restricts parent dropdown to exclude self and all descendants.
        Prevents circular references directly in the UI.
        save_model() is the second line of defense for API/shell writes.
        """
        if db_field.name == "parent":
            object_id = request.resolver_match.kwargs.get("object_id")
            if object_id:
                try:
                    current      = Category.objects.get(pk=object_id)
                    excluded_ids = self._get_descendant_ids(current)
                    excluded_ids.add(current.pk)
                    kwargs["queryset"] = (
                        Category.objects
                        .exclude(pk__in=excluded_ids)
                        .order_by("name")
                    )
                except Category.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _get_descendant_ids(self, category: Category) -> set[int]:
        """
        Recursively collects all descendant PKs to block circular parenting.
        Category trees are small (<100 nodes) — recursion cost is negligible.
        """
        ids: set[int] = set()
        for child in category.subcategories.all():
            ids.add(child.pk)
            ids |= self._get_descendant_ids(child)
        return ids

    def save_model(
        self,
        request: HttpRequest,
        obj: Category,
        form,
        change: bool,
    ) -> None:
        """
        Guards against self-parenting and circular references.
        Uses message_user not ValidationError — ValidationError in
        save_model renders a 500 page; message_user stays in admin.
        """
        if obj.parent_id is not None:
            if obj.pk and obj.pk == obj.parent_id:
                self.message_user(
                    request,
                    _("A category cannot be its own parent. Change was not saved."),
                    level="error",
                )
                return

            if obj.pk and obj.parent_id in self._get_descendant_ids(obj):
                self.message_user(
                    request,
                    _(
                        f'Cannot set "{obj.parent}" as parent of "{obj}" — '
                        f"circular reference detected. Change was not saved."
                    ),
                    level="error",
                )
                return

        super().save_model(request, obj, form, change)


# ─────────────────────────────────────────────────────────────────────────────
# BRAND
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display   = ["name", "slug", "is_active", "created_at"]
    list_filter    = ["is_active"]
    list_editable  = ["is_active"]
    search_fields  = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering       = ["name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "slug", "logo", "is_active"),
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


# ─────────────────────────────────────────────────────────────────────────────
# BIKE MODEL
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(BikeModel)
class BikeModelAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "brand",
        "year_start",
        "year_end",
        "is_active",
        "created_at",
    ]
    list_filter    = ["is_active", "brand"]
    list_editable  = ["is_active"]
    search_fields  = ["name", "brand__name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering       = ["brand__name", "name"]
    autocomplete_fields = ["brand"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("brand", "name", "slug", "is_active"),
            },
        ),
        (
            _("Production Years"),
            {
                "fields": ("year_start", "year_end"),
                "description": _(
                    "Leave 'Production end year' blank if model is still in production."
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

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("brand"): list_display has brand and display_name
        which both access brand.name. Without this — N+1 per row.
        """
        return super().get_queryset(request).select_related("brand")

    def save_model(
        self,
        request: HttpRequest,
        obj: BikeModel,
        form,
        change: bool,
    ) -> None:
        """
        Delegates year range validation to model's clean() method via
        full_clean(). Single source of truth — no duplicated logic.
        """
        from django.core.exceptions import ValidationError
        try:
            obj.full_clean()
        except ValidationError as e:
            for field, errors in e.message_dict.items():
                for error in errors:
                    self.message_user(request, f"{field}: {error}", level="error")
            return
        super().save_model(request, obj, form, change)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SPECIFICATION INLINE
# ─────────────────────────────────────────────────────────────────────────────

class ProductSpecificationInline(admin.TabularInline):
    """
    Inline specification editor shown within the Product admin page.
    Admin adds part-specific key-value specs here (thread size, material, etc.)
    """

    model   = ProductSpecification
    extra   = 3
    max_num = 30
    fields  = ["name", "value", "unit", "display_order"]
    ordering = ["display_order", "name"]


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT IMAGE INLINE
# ─────────────────────────────────────────────────────────────────────────────

class ProductImageInline(admin.TabularInline):
    """
    Inline image gallery editor shown within the Product admin page.
    image_preview renders a thumbnail for visual confirmation.
    """

    model    = ProductImage
    extra    = 1
    max_num  = 10
    fields   = ["image", "image_preview", "is_primary", "order"]
    readonly_fields = ["image_preview"]

    def image_preview(self, obj: ProductImage) -> str:
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px; border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = _("Preview")


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "sku",
        "category",
        "brand",
        "display_price",
        "stock_status",
        "status",
        "is_featured",
        "created_at",
    ]
    list_filter   = ["status", "is_featured", "category", "brand"]
    list_editable = ["status", "is_featured"]
    search_fields = ["name", "sku", "description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["category", "brand", "compatible_bikes"]
    inlines  = [ProductSpecificationInline, ProductImageInline]
    ordering = ["-created_at"]
    readonly_fields = [
        "created_by",
        "current_price",
        "has_discount",
        "discount_percentage",
        "is_in_stock",
        "is_low_stock",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "slug", "sku", "description"),
            },
        ),
        (
            _("Classification"),
            {
                "fields": ("category", "brand", "compatible_bikes"),
            },
        ),
        (
            _("Pricing"),
            {
                "fields": (
                    "price",
                    "discount_price",
                    "current_price",
                    "has_discount",
                    "discount_percentage",
                ),
            },
        ),
        (
            _("Stock & Status"),
            {
                "fields": (
                    "stock",
                    "low_stock_threshold",
                    "weight_grams",
                    "status",
                    "is_in_stock",
                    "is_low_stock",
                ),
                "description": _(
                    "Set 'Low stock threshold' to 0 to disable low stock alerts "
                    "for this product. Weight is used for shipping cost calculation."
                ),
            },
        ),
        (
            _("Visibility"),
            {
                "fields": ("is_featured",),
            },
        ),
        (
            _("Meta"),
            {
                "fields": ("created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    # ── List display helpers ───────────────────────────────────────────────────

    @admin.display(description=_("Price"), ordering="price")
    def display_price(self, obj: Product) -> str:
        """
        Renders discounted price with strikethrough original.
        admin_order_field maps column sort to the real DB price field.
        """
        if obj.has_discount:
            return format_html(
                "Rs. {} "
                '<span style="color:#999;text-decoration:line-through;'
                'font-size:11px;">Rs. {}</span>',
                obj.discount_price,
                obj.price,
            )
        return format_html("Rs. {}", obj.price)

    @admin.display(description=_("Stock"), ordering="stock")
    def stock_status(self, obj: Product) -> str:
        """
        Color-coded stock badge using the product's own low_stock_threshold.

        Thresholds (using product-level setting, not hardcoded magic number):
            stock == 0                      → red    ✕ Out of Stock
            0 < stock <= low_stock_threshold → orange ⚠ Low (N)
            stock > low_stock_threshold      → green  ✓ In Stock (N)
        """
        if obj.stock == 0:
            return format_html(
                '<span style="color:#dc2626;font-weight:bold;">✕ Out of Stock</span>'
            )
        if obj.low_stock_threshold > 0 and obj.stock <= obj.low_stock_threshold:
            return format_html(
                '<span style="color:#d97706;font-weight:bold;">⚠ Low ({})</span>',
                obj.stock,
            )
        return format_html(
            '<span style="color:#16a34a;">✓ In Stock ({})</span>',
            obj.stock,
        )

    # ── Queryset ───────────────────────────────────────────────────────────────

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("category", "brand"):
            list_display has category and brand columns.
            100 products = 200 extra queries without this.
        """
        return (
            super().get_queryset(request)
            .select_related("category", "brand")
        )

    # ── Validation ─────────────────────────────────────────────────────────────

    def save_model(
        self,
        request: HttpRequest,
        obj: Product,
        form,
        change: bool,
    ) -> None:
        """
        Validation order:
            1. Discount < regular price — hard block, do not save.
            2. Available + zero stock — soft warning, allow save.
            3. Auto-assign created_by on creation only.
        """
        if (
            obj.discount_price is not None
            and obj.price is not None
            and obj.discount_price >= obj.price
        ):
            self.message_user(
                request,
                _(
                    f"Discount price (Rs. {obj.discount_price}) must be less than "
                    f"regular price (Rs. {obj.price}). Change was not saved."
                ),
                level="error",
            )
            return

        if obj.status == Product.Status.AVAILABLE and obj.stock == 0:
            self.message_user(
                request,
                _(
                    f'Warning: "{obj.name}" is marked Available but has 0 stock. '
                    f"Customers will see it as available but cannot order."
                ),
                level="warning",
            )

        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT IMAGE (STANDALONE)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = [
        "image_preview",
        "product",
        "is_primary",
        "order",
        "created_at",
    ]
    list_filter   = ["is_primary"]
    search_fields = ["product__name"]
    autocomplete_fields = ["product"]
    readonly_fields = ["image_preview", "created_at", "updated_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """select_related("product"): list_display has product column."""
        return super().get_queryset(request).select_related("product")

    @admin.display(description=_("Preview"))
    def image_preview(self, obj: ProductImage) -> str:
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px; border-radius:4px;" />',
                obj.image.url,
            )
        return "—"


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SPECIFICATION (STANDALONE)
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ProductSpecification)
class ProductSpecificationAdmin(admin.ModelAdmin):
    """
    Standalone admin for ProductSpecification.
    Primarily managed via ProductSpecificationInline on the Product page.
    Standalone view useful for bulk spec auditing across products.
    """

    list_display  = ["product", "name", "value", "unit", "display_order"]
    search_fields = ["product__name", "name", "value"]
    list_filter   = ["name"]
    ordering      = ["product__name", "display_order", "name"]
    autocomplete_fields = ["product"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """select_related("product"): list_display has product column."""
        return super().get_queryset(request).select_related("product")


# ─────────────────────────────────────────────────────────────────────────────
# STOCK RESERVATION
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    """
    Read-only admin for StockReservation.
    Reservations are created/deleted by checkout flow and Celery tasks.
    Delete is permitted — support staff may need to manually release
    a stuck reservation so a product becomes available again.
    Add and change are blocked.
    """

    list_display = [
        "product",
        "user",
        "quantity",
        "expires_at",
        "display_is_expired",
        "created_at",
    ]
    search_fields = [
        "product__name",
        "product__sku",
        "user__email",
    ]
    list_filter   = ["product"]
    list_per_page = 50
    ordering      = ["expires_at"]
    readonly_fields = [
        "product",
        "user",
        "session_key",
        "quantity",
        "expires_at",
        "created_at",
        "updated_at",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("product", "user"):
            list_display accesses both product.name and user.email.
        """
        return (
            super().get_queryset(request)
            .select_related("product", "user")
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    @admin.display(boolean=True, description=_("Expired"))
    def display_is_expired(self, obj: StockReservation) -> bool:
        return obj.is_expired


# ─────────────────────────────────────────────────────────────────────────────
# LOW STOCK ALERT
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(LowStockAlert)
class LowStockAlertAdmin(admin.ModelAdmin):
    """
    Admin interface for LowStockAlert.

    Immutable core fields (product, stock_at_alert, threshold_at_alert)
    are read-only. Resolution fields (is_resolved, resolved_at) are editable
    so operations team can mark alerts resolved after restocking.
    """

    list_display = [
        "product",
        "stock_at_alert",
        "threshold_at_alert",
        "is_resolved",
        "resolved_at",
        "created_at",
    ]
    search_fields = [
        "product__name",
        "product__sku",
    ]
    list_filter   = ["is_resolved"]
    list_editable = ["is_resolved"]
    list_per_page = 50
    ordering      = ["-created_at"]
    date_hierarchy = "created_at"

    # Immutable fields — snapshotted at alert creation time
    readonly_fields = [
        "product",
        "stock_at_alert",
        "threshold_at_alert",
        "resolved_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Alert"),
            {
                "fields": (
                    "product",
                    "stock_at_alert",
                    "threshold_at_alert",
                    "created_at",
                ),
                "description": _(
                    "These fields are snapshotted at alert creation "
                    "and cannot be modified."
                ),
            },
        ),
        (
            _("Resolution"),
            {
                "fields": (
                    "is_resolved",
                    "resolved_at",
                ),
                "description": _(
                    "Mark 'Resolved' after restocking the product. "
                    "'Resolved at' is set automatically."
                ),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("updated_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """select_related("product"): list_display accesses product.name."""
        return super().get_queryset(request).select_related("product")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """
        Alerts are created by post_save signal on Product — not manually.
        """
        return False

    def save_model(
        self,
        request: HttpRequest,
        obj: LowStockAlert,
        form,
        change: bool,
    ) -> None:
        """
        Only resolution fields are editable. Pass update_fields
        explicitly so LowStockAlert.save() immutability guard
        does not raise on the editable fields.
        """
        obj.save(update_fields=["is_resolved", "resolved_at", "updated_at"])