from __future__ import annotations

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.api.serializers import BaseModelSerializer
from .models import Category, Brand, BikeModel, Product, ProductImage

logger = logging.getLogger("apps.products")


# ─── Category Serializers ──────────────────────────────────────────────────
class CategoryFlatSerializer(BaseModelSerializer):
    """
    Flat representation — one object per category, no nesting.

    Use cases:
        - Dropdown / select inputs  (frontend needs id + name only)
        - Search results
        - Admin panels
        - Any place where hierarchy does not matter

    Why parent_name included:
        Dropdown needs to show "Pistons (Engine)" not just "Pistons".
        Without parent_name, frontend makes extra API calls to resolve it.

    Why subcategory_count included:
        Tells frontend whether a category is expandable without extra calls.

    DB cost: ZERO extra queries when queryset uses:
        .select_related("parent")           → covers parent_name
        .annotate(subcategories_count=Count("subcategories"))  → covers count
    """

    parent_name = serializers.SerializerMethodField()
    subcategory_count = serializers.IntegerField(
        source="subcategories_count",
        read_only=True,
        default=0,
    )

    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
            "parent",
            "parent_name",
            "is_subcategory",
            "subcategory_count",
            "is_active",
        ]

    def get_parent_name(self, obj: Category) -> str | None:
        if obj.parent_id is None:
            return None
        return obj.parent.name if obj.parent else None


# class CategoryTreeSerializer(BaseModelSerializer):
#     """
#     Recursive tree representation.

#     Each root category contains its children, each child contains
#     its children, and so on — to any depth.

#     Use cases:
#         - Navigation menus
#         - Category sidebar
#         - Category selection tree (accordion UI)

#     How recursion works:
#         children field calls CategoryTreeSerializer on each child object.
#         DRF handles the recursion — no manual looping needed.

#     Why 'many=True' on children:
#         Each category can have multiple children — always a list.

#     Why read_only=True:
#         This serializer is for GET responses only.
#         Write operations use a dedicated write serializer.

#     DB cost: ZERO extra queries when queryset uses:
#         .prefetch_related("subcategories__subcategories__subcategories")
#         This covers 3 levels of depth in one prefetch.
#         Adjust depth prefix chain based on your max tree depth.

#     Important — why we do NOT call this serializer on the full queryset:
#         We only pass ROOT categories (parent=None) to this serializer.
#         The serializer then accesses .subcategories.all() on each root,
#         which is served from the prefetch cache — not hitting DB again.
#         Passing all categories would double-render subcategories.
#     """

#     children = serializers.SerializerMethodField()

#     class Meta:
#         model = Category
#         fields = [
#             "id",
#             "name",
#             "slug",
#             "is_subcategory",
#             "is_active",
#             "children",
#         ]

#     def get_children(self, obj: Category) -> list:
#         """
#         Why SerializerMethodField instead of nested serializer directly:
#             Direct nested serializer = DRF evaluates it even when empty.
#             SerializerMethodField = we control exactly what is passed in,
#             and we can filter (only active children) before serializing.

#         Why filter is_active here:
#             prefetch_related fetches ALL subcategories including inactive.
#             We must filter them out here before sending to frontend.
#             We cannot filter inside prefetch_related without a custom Prefetch object
#             (shown in the view below).
#         """
#         # subcategories is the related_name on the Category model
#         # Because we use prefetch_related, .all() hits no DB — uses prefetch cache
#         active_children = [
#             child for child in obj.subcategories.all()
#             if child.is_active
#         ]
#         # Recursive — each child is serialized the same way
#         return CategoryTreeSerializer(active_children, many=True).data

# class CategorySerializer(BaseModelSerializer):
#     """Used for category listing and dropdowns."""
#     parent_name = serializers.SerializerMethodField()
#     subcategory_count: serializers.IntegerField = serializers.IntegerField(
#         source="subcategories_count",
#         read_only=True,
#         default=0,
#     )

#     class Meta:
#         model = Category
#         fields = [
#             "id",
#             "name",
#             "slug",
#             "parent",
#             "parent_name",
#             "is_subcategory",
#             "subcategory_count",
#             "is_active",
#         ]
#     def get_parent_name(self, obj: Category) -> str | None:
#         """
#         Why check obj.parent_id first:
#             Avoids attribute access on None.
#             parent_id is a DB column — always available without extra query.
#             obj.parent is the related object — available free via select_related.
#         """
#         if obj.parent_id is None:
#             return None
#         return obj.parent.name if obj.parent else None





# ─── Brand Serializers ─────────────────────────────────────────────────────

class BrandSerializer(BaseModelSerializer):
    """
    Flat serializer for brand listing and filter dropdowns.

    Why logo field kept:
        Frontend brand filter shows logo next to brand name.
        ImageField serializes to full URL via request context.

    Why no extra fields needed:
        Brands are simple — name, slug, logo, is_active.
        No self-referencing FK, no annotations needed.
    """

    class Meta:
        model = Brand
        fields = [
            "id",
            "name",
            "slug",
            "logo",
            "is_active",
        ]


# ─── Bike Model Serializers ────────────────────────────────────────────────

class BikeModelSerializer(BaseModelSerializer):
    """
    Serializer for bike compatibility filter dropdown.

    Why brand_name:
        Frontend dropdown shows "Honda CB150F" not just "CB150F".
        Without brand_name, frontend needs extra call to resolve brand.
        Free via select_related("brand") on the queryset.

    Why display_name:
        Model property combining brand + name + year range.
        Pre-built string for frontend label — no string formatting needed.

    Why year_start and year_end both included:
        Frontend compatibility filter may show year range.
        "Honda CB150F (2018 - 2023)" needs both values.

    Why covers_year not included:
        It is a method, not a field.
        Frontend sends year filter as query param — backend filters queryset.
        No need to expose the method in the API response.
    """

    brand_name: serializers.CharField = serializers.CharField(
        source="brand.name",
        read_only=True,
    )
    display_name: serializers.CharField = serializers.CharField(
        read_only=True,
    )

    class Meta:
        model = BikeModel
        fields = [
            "id",
            "brand",
            "brand_name",
            "name",
            "display_name",
            "slug",
            "year_start",
            "year_end",
            "is_active",
        ]
#! old brand and bike model 
# # ─── Brand Serializers ─────────────────────────────────────────────────────

# class BrandSerializer(BaseModelSerializer):
#     """Used for brand listing and filters."""

#     class Meta:
#         model = Brand
#         fields = [
#             "id",
#             "name",
#             "slug",
#             "logo",
#             "is_active",
#         ]


# # ─── Bike Model Serializers ────────────────────────────────────────────────

# class BikeModelSerializer(BaseModelSerializer):
#     """Used for bike compatibility filter dropdown."""

#     brand_name: serializers.CharField = serializers.CharField(
#         source="brand.name",
#         read_only=True,
#     )
#     display_name: serializers.CharField = serializers.CharField(
#         read_only=True,
#     )

#     class Meta:
#         model = BikeModel
#         fields = [
#             "id",
#             "brand",
#             "brand_name",
#             "name",
#             "display_name",
#             "slug",
#             "year_start",
#             "year_end",
#             "is_active",
#         ]


# ─── Product Image Serializers ─────────────────────────────────────────────

class ProductImageSerializer(BaseModelSerializer):
    """Nested inside product detail/list responses."""

    class Meta:
        model = ProductImage
        fields = [
            "id",
            "image",
            "is_primary",
            "order",
        ]


# ─── Product List Serializer (lightweight) ─────────────────────────────────

class ProductListSerializer(BaseModelSerializer):
    """
    Lightweight serializer for product listing pages.
    Excludes heavy fields like full description and compatible_bikes
    to keep list responses fast.
    """

    category_name: serializers.CharField = serializers.CharField(
        source="category.name",
        read_only=True,
    )
    brand_name: serializers.CharField = serializers.CharField(
        source="brand.name",
        read_only=True,
        default=None,
    )
    primary_image: serializers.SerializerMethodField = serializers.SerializerMethodField()
    current_price: serializers.DecimalField = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    has_discount: serializers.BooleanField = serializers.BooleanField(
        read_only=True,
    )
    discount_percentage: serializers.IntegerField = serializers.IntegerField(
        read_only=True,
    )
    is_in_stock: serializers.BooleanField = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "category_name",
            "brand_name",
            "primary_image",
            "price",
            "discount_price",
            "current_price",
            "has_discount",
            "discount_percentage",
            "is_in_stock",
            "status",
            "is_featured",
        ]

    def get_primary_image(self, obj: Product) -> str | None:
        """Return URL of primary image, or first image as fallback."""
        primary = obj.images.filter(is_primary=True).first()
        image = primary or obj.images.first()
        if image and image.image:
            request = self.context.get("request")
            url = image.image.url
            return request.build_absolute_uri(url) if request else url
        return None


# ─── Product Detail Serializer (full) ──────────────────────────────────────

class ProductDetailSerializer(BaseModelSerializer):
    """
    Full serializer for single product detail page.
    Includes all images, compatible bikes, and full description.
    """

    category: CategoryFlatSerializer = CategoryFlatSerializer(read_only=True)
    brand: BrandSerializer = BrandSerializer(read_only=True)
    compatible_bikes: BikeModelSerializer = BikeModelSerializer(
        many=True, read_only=True,
    )
    images: ProductImageSerializer = ProductImageSerializer(
        many=True, read_only=True,
    )
    current_price: serializers.DecimalField = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    has_discount: serializers.BooleanField = serializers.BooleanField(
        read_only=True,
    )
    discount_percentage: serializers.IntegerField = serializers.IntegerField(
        read_only=True,
    )
    is_in_stock: serializers.BooleanField = serializers.BooleanField(
        read_only=True,
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "sku",
            "description",
            "category",
            "brand",
            "compatible_bikes",
            "images",
            "price",
            "discount_price",
            "current_price",
            "has_discount",
            "discount_percentage",
            "stock",
            "is_in_stock",
            "status",
            "is_featured",
            "created_at",
            "updated_at",
        ]


# ─── Product Create/Update Serializer ──────────────────────────────────────

class ProductWriteSerializer(BaseModelSerializer):
    """
    Used for admin create/update operations.
    Accepts writable fields including FK ids and M2M list.
    """

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "brand",
            "compatible_bikes",
            "description",
            "sku",
            "price",
            "discount_price",
            "stock",
            "status",
            "is_featured",
        ]

    def validate_sku(self, value: str) -> str:
        """SKU uniqueness check, excluding self on update."""
        value = value.strip().upper()
        qs = Product.objects.filter(sku=value)
        if self.instance:
            qs = qs.exclude(id=self.instance.id)
        if qs.exists():
            raise serializers.ValidationError(
                _("A product with this SKU already exists.")
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """Discount price must be less than regular price."""
        price = attrs.get("price", getattr(self.instance, "price", None))
        discount_price = attrs.get("discount_price")

        if discount_price is not None and price is not None:
            if discount_price >= price:
                raise serializers.ValidationError({
                    "discount_price": _(
                        "Discount price must be less than regular price."
                    )
                })
        return attrs

    def create(self, validated_data: dict) -> Product:
        request = self.context.get("request")
        validated_data["created_by"] = request.user if request else None
        product = super().create(validated_data)
        logger.info("Product created via API: %s (sku=%s)", product.name, product.sku)
        return product


# ─── Product Image Upload Serializer ───────────────────────────────────────

class ProductImageUploadSerializer(serializers.Serializer):
    """Used when admin uploads a new product image."""

    image: serializers.ImageField = serializers.ImageField(
        error_messages={
            "invalid_image": _("Upload a valid image file."),
            "blank": _("No image was submitted."),
        }
    )
    is_primary: serializers.BooleanField = serializers.BooleanField(
        default=False,
    )

    def validate_image(self, value):
        max_size = 3 * 1024 * 1024  # 3MB
        allowed_types = ["image/jpeg", "image/png", "image/webp"]

        if value.size > max_size:
            raise serializers.ValidationError(
                _("Image size must not exceed 3MB.")
            )
        if value.content_type not in allowed_types:
            raise serializers.ValidationError(
                _("Only JPEG, PNG and WebP images are allowed.")
            )
        return value