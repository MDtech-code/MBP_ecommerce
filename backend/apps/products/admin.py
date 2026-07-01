from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from .models import Category, Brand, BikeModel, Product, ProductImage







# ─── Category admin ─────────────────────────────────────────────────────────
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
    list_filter = ["is_active", "parent"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]

    # Why: makes is_active togglable directly from the list page
    # without opening each category — saves many clicks for admins
    list_editable = ["is_active"]

    def subcategory_count(self, obj: Category) -> int:
        """Shows child count in list — helps admin spot large branches."""
        return obj.subcategories.count()

    subcategory_count.short_description = _("Children")

    # ── Form field overrides ───────────────────────────────────────────────

    def formfield_for_foreignkey(self, db_field, request: HttpRequest, **kwargs):
        """
        Why override:
            Default parent dropdown shows ALL categories.
            Admin could accidentally select:
                - The category itself as its own parent (self-loop)
                - One of its own children as parent (circular loop)
            Both corrupt the tree silently if save_model validation is bypassed.

        What we do:
            When editing an existing category (object_id in URL):
                Exclude self + all descendants from the parent dropdown.
            When creating a new category (no object_id):
                No exclusions needed — nothing exists yet.

        Why exclude descendants and not just direct children:
            Setting a grandchild as parent creates a circular loop
            even though it is not a direct child.
            Example: Engine → Pistons → Piston Rings
            If you set "Piston Rings" as parent of "Engine" → infinite loop.
        """
        if db_field.name == "parent":
            # Extract the object being edited from the URL
            object_id = request.resolver_match.kwargs.get("object_id")

            if object_id:
                try:
                    current = Category.objects.get(pk=object_id)
                    excluded_ids = self._get_descendant_ids(current)
                    excluded_ids.add(current.pk)  # exclude self

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
        Recursively collects all descendant PKs of a category.

        Why recursive and not a single query:
            Django ORM does not support recursive CTEs out of the box.
            For category trees (typically <100 nodes), Python recursion
            is fast enough and avoids adding django-mptt or django-treebeard
            as a dependency.

        Why we need ALL descendants:
            We must exclude not just direct children but grandchildren too.
            Otherwise a grandchild could be set as parent → circular loop.
        """
        ids: set[int] = set()
        children = category.subcategories.all()
        for child in children:
            ids.add(child.pk)
            ids |= self._get_descendant_ids(child)
        return ids

    # ── Validation ────────────────────────────────────────────────────────

    def save_model(
        self,
        request: HttpRequest,
        obj: Category,
        form,
        change: bool,
    ) -> None:
        """
        Why validate here AND in formfield_for_foreignkey:
            formfield_for_foreignkey restricts the dropdown UI.
            save_model is the last line of defense against:
                - Direct API/shell writes that bypass the form
                - Future code that calls .save() directly
                - Race conditions where tree changes between form load and submit

        Why NOT raise ValidationError directly:
            Raising ValidationError in save_model causes Django admin to
            show a generic 500 error page instead of a friendly message.
            Correct pattern: use self.message_user() + return early.

        Why check obj.pk != obj.parent.pk instead of obj == obj.parent:
            obj may not be saved yet (no pk) when creating.
            Comparing PKs is explicit and null-safe.
        """
        if obj.parent_id is not None:

            # ── Self-parent check ──────────────────────────────────────────
            if obj.pk and obj.pk == obj.parent_id:
                self.message_user(
                    request,
                    _("A category cannot be its own parent. Change was not saved."),
                    level="error",
                )
                return

            # ── Circular loop check ────────────────────────────────────────
            if obj.pk:
                descendant_ids = self._get_descendant_ids(obj)
                if obj.parent_id in descendant_ids:
                    self.message_user(
                        request,
                        _(
                            f'Cannot set "{obj.parent}" as parent of "{obj}" — '
                            f'this would create a circular reference. '
                            f'Change was not saved.'
                        ),
                        level="error",
                    )
                    return

        super().save_model(request, obj, form, change)

    # ── Queryset optimization ─────────────────────────────────────────────

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Why select_related("parent"):
            list_display includes "parent" field.
            Without select_related, each row triggers a separate query
            to fetch the parent object — classic N+1 in admin list view.
        """
        return (
            super().get_queryset(request)
            .select_related("parent")
        )



@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "is_active", "created_at"]
    list_filter = ["is_active"]
    list_editable = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["name"]

    def get_queryset(self, request):
        return super().get_queryset(request)


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
    list_filter = ["is_active", "brand"]
    list_editable = ["is_active"]
    search_fields = ["name", "brand__name"]
    prepopulated_fields = {"slug": ("name",)}
    ordering = ["brand__name", "name"]
    autocomplete_fields = ["brand"]

    def get_queryset(self, request):
        """
        Why select_related("brand"):
            list_display includes brand and display_name (which accesses brand.name).
            Without select_related, each row = one extra query for brand.
        """
        return (
            super().get_queryset(request)
            .select_related("brand")
        )

    def save_model(self, request, obj, form, change):
        """
        Why validate year range:
            year_end must be >= year_start if provided.
            DB has no constraint for this — admin is the validation point.
            Same message_user pattern as CategoryAdmin — no 500 errors.
        """
        if obj.year_end is not None and obj.year_end < obj.year_start:
            self.message_user(
                request,
                f"Production end year ({obj.year_end}) cannot be before "
                f"start year ({obj.year_start}). Change was not saved.",
                level="error",
            )
            return
        super().save_model(request, obj, form, change)





class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    # Why max_num=10:
    #   Prevents admin from adding unlimited images accidentally.
    #   10 is generous for any product gallery.
    max_num = 10
    fields = ["image", "image_preview", "is_primary", "order"]
    readonly_fields = ["image_preview"]

    def image_preview(self, obj: ProductImage):
        """
        Why: admin sees a thumbnail instead of a filename string.
        Makes identifying which image is primary much easier visually.
        Without this, admin sees "products/2024/01/abc.png" — not helpful.
        """
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px; border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = _("Preview")


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
    list_filter = ["status", "is_featured", "category", "brand"]
    search_fields = ["name", "sku", "description"]
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ["category", "brand", "compatible_bikes"]
    inlines = [ProductImageInline]
    ordering = ["-created_at"]

    # Why status and is_featured in list_editable:
    #   These are changed frequently by operations team.
    #   Toggling featured or changing status without opening each product
    #   saves significant time when managing large catalogs.
    list_editable = ["status", "is_featured"]

    readonly_fields = [
        "created_by",
        "current_price",
        "has_discount",
        "discount_percentage",
        "is_in_stock",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "sku", "description"),
        }),
        (_("Classification"), {
            "fields": ("category", "brand", "compatible_bikes"),
        }),
        (_("Pricing & Stock"), {
            "fields": (
                "price",
                "discount_price",
                "current_price",
                "has_discount",
                "discount_percentage",
                "stock",
                "status",
                "is_in_stock",
            ),
        }),
        (_("Visibility"), {
            "fields": ("is_featured",),
        }),
        (_("Meta"), {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # ── List display methods ───────────────────────────────────────────────

    def display_price(self, obj: Product) -> str:
        """
        Why custom method instead of direct current_price property:
            Model properties are not sortable in admin list view.
            admin_order_field tells Django which DB column to sort by
            when the column header is clicked.

        Why show both prices when discount exists:
            Admin needs to see at a glance whether a product is on sale.
            "Rs. 850 (was 1000)" is clearer than just "850".
        """
        if obj.has_discount:
            return format_html(
                'Rs. {} <span style="color:#999; text-decoration:line-through;'
                'font-size:11px;">Rs. {}</span>',
                obj.discount_price,
                obj.price,
            )
        return format_html("Rs. {}", obj.price)

    display_price.short_description = _("Price")
    display_price.admin_order_field = "price"

    def stock_status(self, obj: Product) -> str:
        """
        Why visual stock indicator:
            Operations team needs to spot low-stock products instantly.
            Color-coded badge is faster to scan than reading numbers.

        Thresholds:
            0        → red   "Out of Stock"
            1-5      → orange "Low Stock (N)"
            6+       → green  "In Stock (N)"
        """
        if obj.stock == 0:
            return format_html(
                '<span style="color:#dc2626; font-weight:bold;">✕ Out of Stock</span>'
            )
        if obj.stock <= 5:
            return format_html(
                '<span style="color:#d97706; font-weight:bold;">⚠ Low ({})</span>',
                obj.stock,
            )
        return format_html(
            '<span style="color:#16a34a;">✓ In Stock ({})</span>',
            obj.stock,
        )

    stock_status.short_description = _("Stock")
    stock_status.admin_order_field = "stock"

    # ── Queryset optimization ──────────────────────────────────────────────

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Why select_related("category", "brand"):
            list_display includes category and brand columns.
            Without this, each row fires 2 extra queries.
            100 products in list = 200 extra queries — classic N+1.
        """
        return (
            super().get_queryset(request)
            .select_related("category", "brand")
        )

    # ── Validation ────────────────────────────────────────────────────────

    def save_model(
        self,
        request: HttpRequest,
        obj: Product,
        form,
        change: bool,
    ) -> None:
        """
        Validates pricing logic before saving.

        Why validate discount_price < price:
            DB has no constraint for this.
            A discount_price >= price is logically wrong —
            it would show a "discount" that is actually more expensive.
            discount_percentage would also show 0% or negative.

        Why validate stock vs status:
            Admin may mark product "available" while stock=0.
            This creates a bad UX — customer sees "available" but
            cannot add to cart.
            Warn admin but allow save — stock may be incoming.

        Why auto-assign created_by:
            created_by is readonly in the form.
            On creation, we set it to the logged-in admin automatically.
            On update, we never overwrite it — preserves original creator.
        """
        # ── discount_price validation ──────────────────────────────────────
        if (
            obj.discount_price is not None
            and obj.price is not None
            and obj.discount_price >= obj.price
        ):
            self.message_user(
                request,
                _(
                    f'Discount price (Rs. {obj.discount_price}) must be '
                    f'less than regular price (Rs. {obj.price}). '
                    f'Change was not saved.'
                ),
                level="error",
            )
            return

        # ── Stock vs status warning (non-blocking) ─────────────────────────
        if obj.status == Product.Status.AVAILABLE and obj.stock == 0:
            self.message_user(
                request,
                _(
                    f'Warning: "{obj.name}" is marked Available but has 0 stock. '
                    f'Customers will see it as available but may not be able to order.'
                ),
                level="warning",
            )
            # Why not return here: warning only — admin may know stock is incoming

        # ── Auto-assign created_by ─────────────────────────────────────────
        if not change:
            obj.created_by = request.user

        super().save_model(request, obj, form, change)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = [
        "image_preview",
        "product",
        "is_primary",
        "order",
        "created_at",
    ]
    list_filter = ["is_primary"]
    search_fields = ["product__name"]
    autocomplete_fields = ["product"]
    readonly_fields = ["image_preview", "created_at"]

    def image_preview(self, obj: ProductImage):
        """
        Why: standalone ProductImage admin also needs preview.
        Admin managing images outside the product inline
        needs to see what the image looks like.
        """
        if obj.image:
            return format_html(
                '<img src="{}" style="height:60px; border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    image_preview.short_description = _("Preview")

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        Why select_related("product"):
            list_display includes product column.
            Each row would fire a query to fetch product without this.
        """
        return (
            super().get_queryset(request)
            .select_related("product")
        )
