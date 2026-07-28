from __future__ import annotations

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from django.db.models import Prefetch

from .models import Category, Brand, BikeModel, Product, ProductImage,ProductSpecification
from apps.core.mixins import TimestampFieldsMixin
logger = logging.getLogger("apps.products")


# ─── Category Serializers ──────────────────────────────────────────────────
class CategoryFlatSerializer(serializers.ModelSerializer):
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



# ─── Brand Serializers ─────────────────────────────────────────────────────

class BrandSerializer(serializers.ModelSerializer):
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

class BikeModelSerializer(serializers.ModelSerializer):
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



# ─── Product Image Serializers ─────────────────────────────────────────────

class ProductImageSerializer(serializers.ModelSerializer):
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
class ProductListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for product grid/list pages.

    What frontend card needs (from design):
        - Discount badge      → discount_percentage
        - Product image       → primary_image (URL)
        - Product name        → name
        - Compatible bike     → primary_bike (first compatible bike name)
        - Current price       → current_price
        - Original price      → price (shown crossed out)
        - Has discount flag   → has_discount (controls badge visibility)
        - In stock flag       → is_in_stock (controls Add to Cart button)
        - Status              → status

    What is intentionally excluded:
        - description         → heavy text, not needed for card
        - compatible_bikes    → full M2M list, use primary_bike for card
        - created_by          → internal field, never expose to frontend

    Why ratings omitted:
        Rating system is a separate reviews app — not built yet.
        Frontend will show placeholder stars until reviews app ships.

    Query requirements for zero N+1:
        .select_related("category", "brand")   → category_name, brand_name
        .prefetch_related("images")            → primary_image
        .prefetch_related("compatible_bikes")  → primary_bike
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
    primary_image = serializers.SerializerMethodField()
    primary_bike = serializers.SerializerMethodField()
    current_price: serializers.DecimalField = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
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
            "primary_bike",
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
        """
        Why iterate prefetched cache instead of .filter():
            obj.images.filter(is_primary=True) fires a NEW query per product
            even when prefetch_related("images") was used.

            .filter() on a prefetched M2M/FK bypasses the prefetch cache
            and goes back to DB — this is the N+1 we must avoid.

            Solution: use Python to search the already-fetched list.
            obj.images.all() on a prefetched relation = zero DB queries.

        Why check image.image (the field) not just image (the object):
            An image object can exist with an empty/null image field.
            Accessing .url on an empty ImageField raises ValueError.
        """
        images = obj.images.all()

        # Find primary first, fall back to first image
        primary = next((img for img in images if img.is_primary), None)
        chosen = primary or (images[0] if images else None)

        if not chosen or not chosen.image:
            return None

        request = self.context.get("request")
        url = chosen.image.url
        return request.build_absolute_uri(url) if request else url

    def get_primary_bike(self, obj: Product) -> str | None:
        """
        Why only first compatible bike for list view:
            Product card shows one bike label e.g. "Honda CD70".
            Full compatible_bikes list belongs in the detail serializer.
            Showing all bikes would overflow the card UI.

        Why "Universal" when no compatible bikes:
            Products with no compatible_bikes fit all bikes.
            Frontend shows "Universal" label in this case.
            Matches the design — "Delkor Bike Battery → Universal".

        Why access .all() not .filter():
            Same reason as get_primary_image — uses prefetch cache.
            .filter() on prefetched M2M = new DB query per product.
        """
        bikes = obj.compatible_bikes.all()
        if not bikes:
            return "Universal"
        first = bikes[0]
        return f"{first.brand.name} {first.name}"



# ─── Product Detail Serializer (full) ──────────────────────────────────────

class ProductSpecificationSerializer(serializers.ModelSerializer):
    """
    Serializer for key-value product specifications.

    Nested inside ProductDetailSerializer.specifications field.
    Frontend renders these as a specification table on the detail page.

    Why no TimestampFieldsMixin:
        Specification rows are detail data, not auditable resources.
        Frontend spec table needs name, value, unit, order — not timestamps.

    Why display_order included:
        Frontend must render specs in the correct admin-defined order.
        display_order field drives the ordering — must be in response.
    """

    class Meta:
        model = ProductSpecification
        fields = [
            "id",
            "name",
            "value",
            "unit",
            "display_order",
        ]
class ProductDetailSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Full serializer for single product detail page.

    What frontend detail page needs (from design):
        images[]          → gallery with primary + thumbnails
        brand             → name shown in red under product title
        category          → breadcrumb (name + parent_name)
        compatible_bikes  → chip tags "Honda CD70", "Honda Dream"
        current_price     → displayed prominently
        price             → shown crossed out when discounted
        discount_pct      → badge "-15%"
        is_in_stock       → "In Stock" / "Out of Stock" badge
        description       → description tab content
        related_products  → 4 cards in "Related Products" section

    Why related_products as SerializerMethodField:
        Related products = same category, excluding self, limit 4.
        This is computed at serialization time from the queryset.
        Using a nested serializer (ProductListSerializer) keeps
        the response shape consistent with the list endpoint.

    DB query requirements for zero N+1:
        select_related("category__parent", "brand")
        prefetch_related(
            "images",
            Prefetch("compatible_bikes",
                     queryset=BikeModel.objects.select_related("brand")),
        )
        Related products fetched separately in get_related_products().
    """

    category = CategoryFlatSerializer(read_only=True)
    brand = BrandSerializer(read_only=True)
    compatible_bikes = BikeModelSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    current_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True,
    )
    has_discount = serializers.BooleanField(read_only=True)
    discount_percentage = serializers.IntegerField(read_only=True)
    is_in_stock = serializers.BooleanField(read_only=True)
    related_products = serializers.SerializerMethodField()
    specifications = ProductSpecificationSerializer(many=True, read_only=True)

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
            "weight_grams",
            "status",
            "is_featured",
            "related_products",
            "specifications",
            "created_at",
            "updated_at",
        ]

    def get_related_products(self, obj: Product) -> list:
        """
        Returns up to 4 products from the same category excluding self.

        Why same category:
            Frontend "Related Products" section shows same-category items.
            Most relevant context for a customer viewing a brake part
            is other brake parts.

        Why limit 4:
            Frontend shows exactly 4 cards in a row.
            Fetching more wastes DB and serialization time.

        Why only AVAILABLE status:
            Out of stock / discontinued items must not appear
            as recommendations — bad UX.

        Why ProductListSerializer not ProductDetailSerializer:
            Prevents infinite recursion
            (detail → related → each related has related → infinite).
            List serializer has all fields the card needs.

        Why no caching here:
            The parent product detail is already cached.
            Related products are cached as part of that cached payload.
            No separate cache needed.

        Why select_related + prefetch_related on related queryset:
            ProductListSerializer accesses category_name, brand_name,
            primary_image, primary_bike — all need prefetch to avoid N+1.
        """
        related = (
            Product.objects
            .filter(
                category=obj.category,
                status=Product.Status.AVAILABLE,
            )
            .exclude(pk=obj.pk)
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "compatible_bikes",
                    queryset=BikeModel.objects.select_related("brand"),
                ),
            )
            .order_by("-is_featured", "-created_at")[:4]
        )
        return ProductListSerializer(
            related,
            many=True,
            context=self.context,
        ).data


