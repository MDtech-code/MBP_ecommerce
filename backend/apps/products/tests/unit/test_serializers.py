# apps/products/tests/unit/test_serializers.py
"""
Unit tests for product app serializers.

What is tested:
    CategoryFlatSerializer  — fields, parent_name, subcategory_count
    BrandSerializer         — fields, logo URL
    BikeModelSerializer     — fields, brand_name, display_name
    ProductImageSerializer  — fields
    ProductListSerializer   — fields, primary_image, primary_bike,
                              computed price fields, universal fallback
    ProductDetailSerializer — fields, timestamps from mixin,
                              nested serializers, related_products

What is NOT tested here:
    - HTTP responses     → api/ test files
    - Cache behavior     → test_signals.py
    - Model save logic   → test_models.py

Key technique — prefetch simulation:
    Serializer methods like get_primary_image() and get_primary_bike()
    call obj.images.all() and obj.compatible_bikes.all() expecting
    prefetched data. In unit tests we call prefetch_related() manually
    on the queryset before passing to serializer to replicate
    exactly what the view does — zero N+1, correct cache usage.

Markers:
    @pytest.mark.unit
    @pytest.mark.django_db
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.db.models import Count, Prefetch
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory

from apps.products.models import BikeModel, Product,Category
from apps.products.serializers import (
    BikeModelSerializer,
    BrandSerializer,
    CategoryFlatSerializer,
    ProductDetailSerializer,
    ProductImageSerializer,
    ProductListSerializer,
)


# ─── Request factory ───────────────────────────────────────────────────────────
# Why APIRequestFactory not APIClient:
#   Serializers need a request object only to build absolute image URLs.
#   APIRequestFactory creates a lightweight request without going through
#   the full middleware stack — correct tool for serializer unit tests.

@pytest.fixture
def request_factory():
    return APIRequestFactory()


@pytest.fixture
def fake_request(request_factory):
    """
    Minimal GET request used as serializer context.

    Why needed:
        ImageField.url is a relative path (/media/products/...).
        Serializer calls request.build_absolute_uri(url) to produce
        the full URL frontend needs.
        Without request in context, serializer returns relative URL.
    """
    return request_factory.get("/")


# ─── CategoryFlatSerializer Tests ──────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryFlatSerializer:

    @pytest.mark.unit
    def test_root_category_fields(self, category) -> None:
        """
        Root category must serialize all expected fields.
        parent=None, parent_name=None, is_subcategory=False.
        """
        qs = (
            Category.objects
            .filter(pk=category.pk)
            .select_related("parent")
            .annotate(subcategories_count=Count("subcategories"))
        )
        serializer = CategoryFlatSerializer(qs.first())
        data = serializer.data

        assert data["id"] == category.pk
        assert data["name"] == "Engine Parts"
        assert data["slug"] == "engine-parts"
        assert data["parent"] is None
        assert data["parent_name"] is None
        assert data["is_subcategory"] is False
        assert data["is_active"] is True

    @pytest.mark.unit
    def test_subcategory_parent_name_populated(
        self,
        category,
        subcategory,
    ) -> None:
        """
        Subcategory must include parent_name from parent object.
        select_related("parent") makes this zero extra queries.
        """
        qs = (
            Category.objects
            .filter(pk=subcategory.pk)
            .select_related("parent")
            .annotate(subcategories_count=Count("subcategories"))
        )
        data = CategoryFlatSerializer(qs.first()).data

        assert data["parent"] == category.pk
        assert data["parent_name"] == "Engine Parts"
        assert data["is_subcategory"] is True

    @pytest.mark.unit
    def test_subcategory_count_zero_for_leaf(self, category) -> None:
        """
        Category with no children must have subcategory_count=0.
        """
        qs = (
            Category.objects
            .filter(pk=category.pk)
            .select_related("parent")
            .annotate(subcategories_count=Count("subcategories"))
        )
        data = CategoryFlatSerializer(qs.first()).data
        assert data["subcategory_count"] == 0

    @pytest.mark.unit
    def test_subcategory_count_correct_for_parent(
        self,
        category,
        subcategory,
    ) -> None:
        """
        Parent category must have subcategory_count=1 after child created.
        """
        qs = (
            Category.objects
            .filter(pk=category.pk)
            .select_related("parent")
            .annotate(subcategories_count=Count("subcategories"))
        )
        data = CategoryFlatSerializer(qs.first()).data
        assert data["subcategory_count"] == 1

    @pytest.mark.unit
    def test_no_timestamp_fields(self, category) -> None:
        """
        CategoryFlatSerializer must NOT include created_at / updated_at.

        Why:
            Dropdown consumers never need timestamps.
            TimestampFieldsMixin intentionally not applied.
        """
        qs = (
            Category.objects
            .filter(pk=category.pk)
            .select_related("parent")
            .annotate(subcategories_count=Count("subcategories"))
        )
        data = CategoryFlatSerializer(qs.first()).data
        assert "created_at" not in data
        assert "updated_at" not in data


# ─── BrandSerializer Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBrandSerializer:

    @pytest.mark.unit
    def test_brand_fields_present(self, brand) -> None:
        """
        BrandSerializer must include id, name, slug, logo, is_active.
        """
        data = BrandSerializer(brand).data

        assert data["id"] == brand.pk
        assert data["name"] == "Honda"
        assert data["slug"] == "honda"
        assert data["is_active"] is True

    @pytest.mark.unit
    def test_logo_is_none_when_not_set(self, brand) -> None:
        """
        logo must be None when no image uploaded.
        Brand fixture does not set a logo.
        """
        data = BrandSerializer(brand).data
        assert data["logo"] is None

    @pytest.mark.unit
    def test_no_timestamp_fields(self, brand) -> None:
        """
        BrandSerializer must NOT include created_at / updated_at.
        """
        data = BrandSerializer(brand).data
        assert "created_at" not in data
        assert "updated_at" not in data


# ─── BikeModelSerializer Tests ────────────────────────────────────────────────

@pytest.mark.django_db
class TestBikeModelSerializer:

    @pytest.mark.unit
    def test_bike_model_fields_present(self, bike_model) -> None:
        """
        BikeModelSerializer must include all declared fields.
        """
        qs = (
            BikeModel.objects
            .filter(pk=bike_model.pk)
            .select_related("brand")
        )
        data = BikeModelSerializer(qs.first()).data

        assert data["id"] == bike_model.pk
        assert data["brand"] == bike_model.brand.pk
        assert data["brand_name"] == "Honda"
        assert data["name"] == "CD70"
        assert data["slug"] == "honda-cd70"
        assert data["year_start"] == 2015
        assert data["year_end"] == 2023
        assert data["is_active"] is True

    @pytest.mark.unit
    def test_display_name_field(self, bike_model) -> None:
        """
        display_name must match BikeModel.display_name property.
        "Honda CD70"
        """
        qs = (
            BikeModel.objects
            .filter(pk=bike_model.pk)
            .select_related("brand")
        )
        data = BikeModelSerializer(qs.first()).data
        assert data["display_name"] == "Honda CD70"

    @pytest.mark.unit
    def test_year_end_none_when_still_in_production(
        self,
        db,
        brand,
    ) -> None:
        """
        year_end must serialize as null when bike still in production.
        """
        bm = BikeModel.objects.create(
            brand=brand,
            name="CB150F",
            year_start=2020,
            year_end=None,
        )
        qs = BikeModel.objects.filter(pk=bm.pk).select_related("brand")
        data = BikeModelSerializer(qs.first()).data
        assert data["year_end"] is None

    @pytest.mark.unit
    def test_no_timestamp_fields(self, bike_model) -> None:
        """
        BikeModelSerializer must NOT include created_at / updated_at.
        """
        qs = (
            BikeModel.objects
            .filter(pk=bike_model.pk)
            .select_related("brand")
        )
        data = BikeModelSerializer(qs.first()).data
        assert "created_at" not in data
        assert "updated_at" not in data


# ─── ProductImageSerializer Tests ─────────────────────────────────────────────

@pytest.mark.django_db
class TestProductImageSerializer:

    @pytest.mark.unit
    def test_image_fields_present(self, product_image) -> None:
        """
        ProductImageSerializer must include id, image, is_primary, order.
        """
        data = ProductImageSerializer(product_image).data

        assert data["id"] == product_image.pk
        assert data["is_primary"] is True
        assert data["order"] == 0

    @pytest.mark.unit
    def test_no_timestamp_fields(self, product_image) -> None:
        """
        ProductImageSerializer must NOT include created_at / updated_at.
        """
        data = ProductImageSerializer(product_image).data
        assert "created_at" not in data
        assert "updated_at" not in data


# ─── ProductListSerializer Tests ──────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListSerializer:
    """
    Tests for the lightweight product card serializer.

    All tests use prefetch_related() on the queryset to replicate
    exactly what ProductListAPIView does — ensures get_primary_image()
    and get_primary_bike() use prefetch cache, not new DB queries.
    """

    def _get_prefetched_product(self, product_pk: int) -> Product:
        """
        Helper — returns a single product with all prefetches applied.
        Replicates the view queryset for serializer unit tests.
        """
        return (
            Product.objects
            .filter(pk=product_pk)
            .select_related("category", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "compatible_bikes",
                    queryset=BikeModel.objects.select_related("brand"),
                ),
            )
            .first()
        )

    @pytest.mark.unit
    def test_basic_fields_present(self, product, fake_request) -> None:
        """
        All declared Meta.fields must be present in serialized output.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data

        expected_fields = [
            "id", "name", "slug", "sku",
            "category_name", "brand_name",
            "primary_image", "primary_bike",
            "price", "discount_price",
            "current_price", "has_discount",
            "discount_percentage", "is_in_stock",
            "status", "is_featured",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.unit
    def test_no_timestamp_fields(self, product, fake_request) -> None:
        """
        ProductListSerializer must NOT include created_at / updated_at.
        Card view never shows timestamps.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert "created_at" not in data
        assert "updated_at" not in data

    @pytest.mark.unit
    def test_category_name_from_related(self, product, fake_request) -> None:
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["category_name"] == "Engine Parts"

    @pytest.mark.unit
    def test_brand_name_from_related(self, product, fake_request) -> None:
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["brand_name"] == "Honda"

    @pytest.mark.unit
    def test_brand_name_none_for_universal_product(
        self,
        universal_product,
        fake_request,
    ) -> None:
        """
        Universal product has no brand — brand_name must be None.
        """
        obj = self._get_prefetched_product(universal_product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["brand_name"] is None

    @pytest.mark.unit
    def test_primary_image_returns_absolute_url(
        self,
        product,
        product_image,
        fake_request,
    ) -> None:
        """
        primary_image must return an absolute URL when request is in context.

        Why absolute:
            Frontend <img src> needs a full URL, not a relative path.
            request.build_absolute_uri() handles this.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["primary_image"] is not None
        assert data["primary_image"].startswith("http")

    @pytest.mark.unit
    def test_primary_image_none_when_no_images(
        self,
        product,
        fake_request,
    ) -> None:
        """
        primary_image must be None when product has no images.
        product fixture has no images attached.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["primary_image"] is None

    @pytest.mark.unit
    def test_primary_image_prefers_is_primary_true(
        self,
        product,
        product_image,
        secondary_image,
        fake_request,
    ) -> None:
        """
        When multiple images exist, the one with is_primary=True
        must be selected — not the first by order.

        product_image  → is_primary=True,  order=0
        secondary_image → is_primary=False, order=1
        Expected: product_image URL returned.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        # URL must contain the primary image filename
        assert data["primary_image"] is not None
        assert "test_product" in data["primary_image"]

    @pytest.mark.unit
    def test_primary_bike_universal_when_no_compatible_bikes(
        self,
        universal_product,
        fake_request,
    ) -> None:
        """
        Products with no compatible_bikes must return "Universal".

        Why:
            Universal parts fit all bikes.
            Frontend card shows "Universal" label in this case.
        """
        obj = self._get_prefetched_product(universal_product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["primary_bike"] == "Universal"

    @pytest.mark.unit
    def test_primary_bike_returns_first_compatible_bike(
        self,
        compatible_product,
        bike_model,
        fake_request,
    ) -> None:
        """
        Products with compatible_bikes must return first bike as
        "{brand.name} {name}" string.
        bike_model = Honda CD70
        """
        obj = self._get_prefetched_product(compatible_product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["primary_bike"] == "Honda CD70"

    @pytest.mark.unit
    def test_computed_price_fields_no_discount(
        self,
        product,
        fake_request,
    ) -> None:
        """
        Without discount:
            current_price == price
            has_discount == False
            discount_percentage == 0
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["current_price"] == product.price
        assert data["has_discount"] is False
        assert data["discount_percentage"] == 0

    @pytest.mark.unit
    def test_computed_price_fields_with_discount(
        self,
        discounted_product,
        fake_request,
    ) -> None:
        """
        With discount:
            current_price == discount_price (400)
            has_discount == True
            discount_percentage == 20
        price=500, discount_price=400 → 20% off
        """
        obj = self._get_prefetched_product(discounted_product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert Decimal(data["current_price"]) == discounted_product.discount_price
        assert data["has_discount"] is True
        assert data["discount_percentage"] == 20

    @pytest.mark.unit
    def test_is_in_stock_true(self, product, fake_request) -> None:
        obj = self._get_prefetched_product(product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["is_in_stock"] is True

    @pytest.mark.unit
    def test_is_in_stock_false(self, out_of_stock_product, fake_request) -> None:
        obj = self._get_prefetched_product(out_of_stock_product.pk)
        data = ProductListSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["is_in_stock"] is False


# ─── ProductDetailSerializer Tests ────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailSerializer:
    """
    Tests for the full product detail serializer.

    Replicates ProductDetailAPIView queryset exactly:
        select_related("category__parent", "brand")
        prefetch_related("images", compatible_bikes → select_related("brand"))
    """

    def _get_prefetched_product(self, product_pk: int) -> Product:
        return (
            Product.objects
            .filter(pk=product_pk)
            .select_related("category__parent", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "compatible_bikes",
                    queryset=BikeModel.objects.select_related("brand"),
                ),
            )
            .first()
        )

    @pytest.mark.unit
    def test_all_fields_present(self, product, fake_request) -> None:
        """
        All declared Meta.fields must be present in detail response.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data

        expected_fields = [
            "id", "name", "slug", "sku", "description",
            "category", "brand", "compatible_bikes", "images",
            "price", "discount_price", "current_price",
            "has_discount", "discount_percentage",
            "stock", "is_in_stock", "status", "is_featured",
            "related_products", "created_at", "updated_at",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    @pytest.mark.unit
    def test_timestamp_fields_present(self, product, fake_request) -> None:
        """
        ProductDetailSerializer uses TimestampFieldsMixin.
        created_at and updated_at must be present.

        Why only detail serializer:
            Detail page shows "Listed on 12 Jan 2025".
            No other product serializer needs timestamps.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["created_at"] is not None
        assert data["updated_at"] is not None

    @pytest.mark.unit
    def test_category_is_nested_object(self, product, fake_request) -> None:
        """
        category field must be a nested dict from CategoryFlatSerializer,
        not a raw integer FK.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert isinstance(data["category"], dict)
        assert data["category"]["name"] == "Engine Parts"
        assert data["category"]["slug"] == "engine-parts"

    @pytest.mark.unit
    def test_brand_is_nested_object(self, product, fake_request) -> None:
        """
        brand field must be a nested dict from BrandSerializer,
        not a raw integer FK.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert isinstance(data["brand"], dict)
        assert data["brand"]["name"] == "Honda"

    @pytest.mark.unit
    def test_brand_none_for_universal_product(
        self,
        universal_product,
        fake_request,
    ) -> None:
        """
        Universal product has no brand — brand field must be null.
        """
        obj = self._get_prefetched_product(universal_product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["brand"] is None

    @pytest.mark.unit
    def test_compatible_bikes_is_list(
        self,
        compatible_product,
        fake_request,
    ) -> None:
        """
        compatible_bikes must be a list of nested BikeModelSerializer dicts.
        """
        obj = self._get_prefetched_product(compatible_product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert isinstance(data["compatible_bikes"], list)
        assert len(data["compatible_bikes"]) == 1
        assert data["compatible_bikes"][0]["name"] == "CD70"
        assert data["compatible_bikes"][0]["brand_name"] == "Honda"

    @pytest.mark.unit
    def test_compatible_bikes_empty_for_universal(
        self,
        universal_product,
        fake_request,
    ) -> None:
        """
        Universal product must have empty compatible_bikes list.
        """
        obj = self._get_prefetched_product(universal_product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert data["compatible_bikes"] == []

    @pytest.mark.unit
    def test_images_is_list(
        self,
        product,
        product_image,
        fake_request,
    ) -> None:
        """
        images must be a list of nested ProductImageSerializer dicts.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert isinstance(data["images"], list)
        assert len(data["images"]) == 1
        assert data["images"][0]["is_primary"] is True

    @pytest.mark.unit
    def test_related_products_excludes_self(
        self,
        product,
        featured_product,
        fake_request,
    ) -> None:
        """
        related_products must not include the product itself.
        Both product and featured_product share the same category.
        related_products of product must contain featured_product, not self.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        related_ids = [p["id"] for p in data["related_products"]]
        assert product.pk not in related_ids

    @pytest.mark.unit
    def test_related_products_same_category_only(
        self,
        db,
        product,
        category,
        brand,
        admin_user,
        fake_request,
    ) -> None:
        """
        related_products must only include products from the same category.

        Create a product in a DIFFERENT category — must not appear
        in related_products of `product`.
        """
        other_category = Category.objects.create(
            name="Electrical Parts",
            is_active=True,
        )
        Product.objects.create(
            name="Headlight Bulb",
            category=other_category,
            brand=brand,
            sku="OTHER-CAT-SKU",
            price=Decimal("200.00"),
            stock=10,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        related_names = [p["name"] for p in data["related_products"]]
        assert "Headlight Bulb" not in related_names

    @pytest.mark.unit
    def test_related_products_excludes_unavailable(
        self,
        product,
        out_of_stock_product,
        fake_request,
    ) -> None:
        """
        related_products must only include AVAILABLE products.
        out_of_stock_product is in same category but status=OUT_OF_STOCK.
        Must not appear in related_products.
        """
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        related_names = [p["name"] for p in data["related_products"]]
        assert out_of_stock_product.name not in related_names

    @pytest.mark.unit
    def test_related_products_max_four(
        self,
        db,
        product,
        category,
        brand,
        admin_user,
        fake_request,
    ) -> None:
        """
        related_products must return at most 4 items.

        Create 6 extra products in same category.
        related_products must still return max 4.
        """
        for i in range(6):
            Product.objects.create(
                name=f"Extra Part {i}",
                category=category,
                brand=brand,
                sku=f"EXTRA-SKU-{i:03d}",
                price=Decimal("100.00"),
                stock=10,
                status=Product.Status.AVAILABLE,
                created_by=admin_user,
            )
        obj = self._get_prefetched_product(product.pk)
        data = ProductDetailSerializer(
            obj,
            context={"request": fake_request},
        ).data
        assert len(data["related_products"]) <= 4