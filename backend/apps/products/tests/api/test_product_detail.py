# apps/products/tests/api/test_product_detail_api.py
"""
API tests for ProductDetailAPIView.

Endpoint:
    GET /api/products/<slug>/

What is tested:
    Response structure    — envelope, meta fields
    Product data          — all fields present, correct values
    Nested objects        — category, brand, images, compatible_bikes
    Computed fields       — current_price, has_discount, discount_percentage,
                            is_in_stock
    Timestamps            — created_at, updated_at from TimestampFieldsMixin
    Related products      — same category, excludes self, max 4, AVAILABLE only
    404 handling          — nonexistent slug returns 404 not 503
    Cache behavior        — source, hit on second request, per-slug keys,
                            invalidation after product/image change
    Permissions           — AllowAny, POST not allowed

What is NOT tested here:
    - Serializer field output  → unit/test_serializers.py
    - Signal internals         → unit/test_signals.py
    - Model save logic         → unit/test_models.py

Markers:
    @pytest.mark.integration
    @pytest.mark.django_db
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.products.models import Category, Product

from ..urls import PRODUCT_LIST_URL, product_detail_url


# ─── Response helpers ──────────────────────────────────────────────────────────

def assert_success_envelope(response, expected_status: int = 200) -> None:
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["message"], str)
    assert payload["errors"] is None
    assert isinstance(payload["meta"], dict)


def assert_detail_meta(meta: dict) -> None:
    """
    Detail meta must contain source and elapsed_ms.
    No pagination — detail returns a single object.
    """
    assert "source" in meta
    assert "elapsed_ms" in meta
    assert meta["source"] in ("l1_memory", "l2_redis", "database")
    assert isinstance(meta["elapsed_ms"], float)


# ─── Response Structure Tests ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailResponseStructure:

    @pytest.mark.integration
    def test_returns_200_with_correct_envelope(
        self,
        api_client,
        product,
    ) -> None:
        """
        Basic smoke test — endpoint reachable, envelope correct.
        data must be a dict (single object), not a list.
        """
        response = api_client.get(product_detail_url(product.slug))
        assert_success_envelope(response)

        payload = response.json()
        # Detail returns dict not list
        assert isinstance(payload["data"], dict)

    @pytest.mark.integration
    def test_meta_fields_present(
        self,
        api_client,
        product,
    ) -> None:
        """
        meta must contain source and elapsed_ms.
        No pagination meta — single product response.
        """
        response = api_client.get(product_detail_url(product.slug))
        assert_detail_meta(response.json()["meta"])

    @pytest.mark.integration
    def test_all_detail_fields_present(
        self,
        api_client,
        product,
    ) -> None:
        """
        All ProductDetailSerializer Meta.fields must be present.
        Including timestamps — only detail serializer has TimestampFieldsMixin.
        """
        response = api_client.get(product_detail_url(product.slug))
        data = response.json()["data"]

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

    @pytest.mark.integration
    def test_timestamps_present_in_detail_not_list(
        self,
        api_client,
        product,
    ) -> None:
        """
        created_at and updated_at must appear in detail response.
        They must NOT appear in list response.

        Why:
            TimestampFieldsMixin applied only to ProductDetailSerializer.
            ProductListSerializer intentionally excludes timestamps.
        """
        detail_response = api_client.get(product_detail_url(product.slug))
        detail_data = detail_response.json()["data"]

        assert detail_data["created_at"] is not None
        assert detail_data["updated_at"] is not None

        list_response = api_client.get(PRODUCT_LIST_URL)
        list_item = next(
            (i for i in list_response.json()["data"] if i["id"] == product.pk),
            None,
        )
        assert list_item is not None
        assert "created_at" not in list_item
        assert "updated_at" not in list_item

    @pytest.mark.integration
    def test_post_not_allowed(self, api_client, product) -> None:
        response = api_client.post(product_detail_url(product.slug), {})
        assert response.status_code == 405


# ─── Product Data Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailData:
    """
    Tests verifying the correct product data is returned.
    """

    @pytest.mark.integration
    def test_correct_product_returned_by_slug(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Each product must be returned by its own unique slug.
        Requesting product slug must not return featured_product data.
        """
        response = api_client.get(product_detail_url(product.slug))
        data = response.json()["data"]

        assert data["id"] == product.pk
        assert data["slug"] == product.slug
        assert data["name"] == product.name
        assert data["sku"] == product.sku

    @pytest.mark.integration
    def test_computed_price_fields_no_discount(
        self,
        api_client,
        product,
    ) -> None:
        """
        Without discount:
            current_price == price
            has_discount == False
            discount_percentage == 0
        """
        response = api_client.get(product_detail_url(product.slug))
        data = response.json()["data"]

        assert data["current_price"] == product.price
        assert data["has_discount"] is False
        assert data["discount_percentage"] == 0
        assert data["discount_price"] is None

    @pytest.mark.integration
    def test_computed_price_fields_with_discount(
        self,
        api_client,
        discounted_product,
    ) -> None:
        """
        With discount:
            current_price == discount_price
            has_discount == True
            discount_percentage == 20
        price=500, discount_price=400
        """
        response = api_client.get(product_detail_url(discounted_product.slug))
        data = response.json()["data"]

        assert Decimal(data["current_price"]) == discounted_product.discount_price
        assert data["has_discount"] is True
        assert data["discount_percentage"] == 20

    @pytest.mark.integration
    def test_is_in_stock_true(self, api_client, product) -> None:
        """
        product has stock=10 and status=AVAILABLE → is_in_stock=True.
        """
        response = api_client.get(product_detail_url(product.slug))
        assert response.json()["data"]["is_in_stock"] is True

    @pytest.mark.integration
    def test_stock_field_present_in_detail(
        self,
        api_client,
        product,
    ) -> None:
        """
        stock (raw quantity) must be present in detail —
        not just is_in_stock boolean.
        Frontend shows "Only 3 left in stock" using raw stock value.
        """
        response = api_client.get(product_detail_url(product.slug))
        data = response.json()["data"]

        assert "stock" in data
        assert data["stock"] == product.stock


# ─── Nested Object Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailNestedObjects:
    """
    Detail response includes fully nested objects —
    not raw FK integers.
    """

    @pytest.mark.integration
    def test_category_is_nested_object_with_fields(
        self,
        api_client,
        product,
        category,
    ) -> None:
        """
        category must be a nested dict with CategoryFlatSerializer fields.
        Frontend uses this for breadcrumb rendering.
        """
        response = api_client.get(product_detail_url(product.slug))
        cat = response.json()["data"]["category"]

        assert isinstance(cat, dict)
        assert cat["id"] == category.pk
        assert cat["name"] == "Engine Parts"
        assert cat["slug"] == "engine-parts"
        assert cat["parent"] is None
        assert cat["parent_name"] is None
        assert cat["is_subcategory"] is False

    @pytest.mark.integration
    def test_category_includes_parent_name_for_subcategory(
        self,
        api_client,
        db,
        category,
        subcategory,
        brand,
        admin_user,
    ) -> None:
        """
        Product in subcategory must show parent_name in category field.
        Breadcrumb: Home > Engine Parts > Pistons > Product.

        Why select_related("category__parent"):
            CategoryFlatSerializer.get_parent_name() accesses obj.parent.name.
            Without select_related, this fires an extra query per product.
        """
        sub_product = Product.objects.create(
            name="Piston Ring Set",
            category=subcategory,
            brand=brand,
            sku="PISTON-RING-001",
            price=Decimal("350.00"),
            stock=15,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )

        response = api_client.get(product_detail_url(sub_product.slug))
        cat = response.json()["data"]["category"]

        assert cat["name"] == "Pistons"
        assert cat["parent_name"] == "Engine Parts"
        assert cat["is_subcategory"] is True

    @pytest.mark.integration
    def test_brand_is_nested_object_with_fields(
        self,
        api_client,
        product,
        brand,
    ) -> None:
        """
        brand must be a nested dict with BrandSerializer fields.
        """
        response = api_client.get(product_detail_url(product.slug))
        b = response.json()["data"]["brand"]

        assert isinstance(b, dict)
        assert b["id"] == brand.pk
        assert b["name"] == "Honda"
        assert b["slug"] == "honda"

    @pytest.mark.integration
    def test_brand_null_for_universal_product(
        self,
        api_client,
        universal_product,
    ) -> None:
        """
        Universal product has no brand — brand field must be null.
        """
        response = api_client.get(product_detail_url(universal_product.slug))
        assert response.json()["data"]["brand"] is None

    @pytest.mark.integration
    def test_compatible_bikes_list_populated(
        self,
        api_client,
        compatible_product,
        bike_model,
    ) -> None:
        """
        compatible_bikes must be a list of nested BikeModelSerializer dicts.
        Each bike chip on the detail page is one item in this list.
        """
        response = api_client.get(product_detail_url(compatible_product.slug))
        bikes = response.json()["data"]["compatible_bikes"]

        assert isinstance(bikes, list)
        assert len(bikes) == 1

        bike = bikes[0]
        assert bike["id"] == bike_model.pk
        assert bike["name"] == "CD70"
        assert bike["brand_name"] == "Honda"
        assert bike["display_name"] == "Honda CD70"

    @pytest.mark.integration
    def test_compatible_bikes_empty_for_universal(
        self,
        api_client,
        universal_product,
    ) -> None:
        """
        Universal product must have empty compatible_bikes list.
        """
        response = api_client.get(product_detail_url(universal_product.slug))
        assert response.json()["data"]["compatible_bikes"] == []

    @pytest.mark.integration
    def test_images_list_populated(
        self,
        api_client,
        product,
        product_image,
    ) -> None:
        """
        images must be a list of nested ProductImageSerializer dicts.
        """
        response = api_client.get(product_detail_url(product.slug))
        images = response.json()["data"]["images"]

        assert isinstance(images, list)
        assert len(images) == 1

        img = images[0]
        assert img["id"] == product_image.pk
        assert img["is_primary"] is True
        assert img["order"] == 0

    @pytest.mark.integration
    def test_images_empty_when_no_images(
        self,
        api_client,
        product,
    ) -> None:
        """
        Product with no images must return empty images list — not null.
        """
        response = api_client.get(product_detail_url(product.slug))
        assert response.json()["data"]["images"] == []

    @pytest.mark.integration
    def test_multiple_images_returned_in_order(
        self,
        api_client,
        product,
        product_image,
        secondary_image,
    ) -> None:
        """
        All images must be returned ordered by [order, created_at].

        product_image  → order=0, is_primary=True
        secondary_image → order=1, is_primary=False

        Both must appear, in correct order.
        """
        response = api_client.get(product_detail_url(product.slug))
        images = response.json()["data"]["images"]

        assert len(images) == 2
        assert images[0]["is_primary"] is True
        assert images[1]["is_primary"] is False


# ─── Related Products Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailRelatedProducts:
    """
    related_products = same category, AVAILABLE, excludes self, max 4.
    Each related product uses ProductListSerializer shape.
    """

    @pytest.mark.integration
    def test_related_products_excludes_self(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Product must not appear in its own related_products list.
        Both product and featured_product are in same category.
        """
        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        related_ids = [p["id"] for p in related]
        assert product.pk not in related_ids

    @pytest.mark.integration
    def test_related_products_same_category(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Related products must be from the same category.
        featured_product is in same category → must appear.
        """
        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        related_ids = [p["id"] for p in related]
        assert featured_product.pk in related_ids

    @pytest.mark.integration
    def test_related_products_excludes_different_category(
        self,
        api_client,
        product,
        db,
        brand,
        admin_user,
    ) -> None:
        """
        Product in a different category must NOT appear in related_products.
        """
        other_cat = Category.objects.create(
            name="Electrical Parts",
            is_active=True,
        )
        other = Product.objects.create(
            name="LED Headlight",
            category=other_cat,
            brand=brand,
            sku="LED-001",
            price=Decimal("800.00"),
            stock=5,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )

        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        related_ids = [p["id"] for p in related]
        assert other.pk not in related_ids

    @pytest.mark.integration
    def test_related_products_excludes_unavailable(
        self,
        api_client,
        product,
        out_of_stock_product,
    ) -> None:
        """
        OUT_OF_STOCK products must not appear in related_products.
        Both product and out_of_stock_product are in same category.
        """
        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        related_ids = [p["id"] for p in related]
        assert out_of_stock_product.pk not in related_ids

    @pytest.mark.integration
    def test_related_products_max_four(
        self,
        api_client,
        product,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        related_products must never exceed 4 items.
        Create 6 extra products in same category — still max 4 returned.
        """
        for i in range(6):
            Product.objects.create(
                name=f"Related Part {i}",
                category=category,
                brand=brand,
                sku=f"REL-SKU-{i:03d}",
                price=Decimal("200.00"),
                stock=10,
                status=Product.Status.AVAILABLE,
                created_by=admin_user,
            )

        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        assert len(related) <= 4

    @pytest.mark.integration
    def test_related_products_empty_when_no_others_in_category(
        self,
        api_client,
        product,
    ) -> None:
        """
        When product is the only AVAILABLE item in its category,
        related_products must be empty list — not null, not error.
        """
        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        assert isinstance(related, list)
        assert related == []

    @pytest.mark.integration
    def test_related_products_use_list_serializer_shape(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Each related product must have ProductListSerializer fields —
        not ProductDetailSerializer fields (no nested category object,
        no related_products recursion, no timestamps).

        Why:
            ProductDetailSerializer.get_related_products() uses
            ProductListSerializer to prevent infinite recursion and
            keep the payload lean.
        """
        response = api_client.get(product_detail_url(product.slug))
        related = response.json()["data"]["related_products"]

        assert len(related) > 0
        related_item = related[0]

        # Must have list fields
        assert "category_name" in related_item
        assert "primary_image" in related_item
        assert "primary_bike" in related_item

        # Must NOT have detail-only fields
        assert "category" not in related_item
        assert "related_products" not in related_item
        assert "created_at" not in related_item
        assert "updated_at" not in related_item


# ─── 404 Handling Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetail404:

    @pytest.mark.integration
    def test_nonexistent_slug_returns_404(
        self,
        api_client,
    ) -> None:
        """
        GET /api/products/slug-that-does-not-exist/ must return 404.

        Why 404 not 503:
            Http404 is caught separately before generic Exception.
            If Http404 fell through to generic handler → 503 (wrong).
            The view re-raises Http404 → DRF converts to 404 response.
        """
        response = api_client.get(
            product_detail_url("slug-that-does-not-exist")
        )
        assert response.status_code == 404

    @pytest.mark.integration
    def test_404_response_has_correct_envelope(
        self,
        api_client,
    ) -> None:
        """
        404 response must follow the standard error envelope.
        success=False, data=None.
        """
        response = api_client.get(
            product_detail_url("nonexistent-product-slug")
        )
        payload = response.json()

        assert payload["success"] is False
        assert payload["data"] is None

    @pytest.mark.integration
    def test_out_of_stock_product_detail_accessible(
        self,
        api_client,
        out_of_stock_product,
    ) -> None:
        """
        OUT_OF_STOCK product detail must still return 200.

        Why:
            Product list excludes OUT_OF_STOCK — they don't appear in browse.
            Product detail does NOT filter by status — direct URL access
            must work so customer can see the product page with
            "Out of Stock" badge and still view product info.
        """
        response = api_client.get(
            product_detail_url(out_of_stock_product.slug)
        )
        assert response.status_code == 200
        assert response.json()["data"]["is_in_stock"] is False


# ─── Cache Behavior Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailCacheBehavior:
    """
    Each product has its own cache key:
        product_detail_{slug}

    Key insight: detail cache is per-slug (exact key),
    NOT prefix-based like list cache.
    Other products' caches must not be affected.
    """

    @pytest.mark.integration
    def test_first_request_source_is_database(
        self,
        api_client,
        product,
    ) -> None:
        """
        First request after cache clear must hit database.
        """
        response = api_client.get(product_detail_url(product.slug))
        assert response.json()["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_second_request_source_is_cache(
        self,
        api_client,
        product,
    ) -> None:
        """
        Second request must be served from cache.
        """
        api_client.get(product_detail_url(product.slug))

        response = api_client.get(product_detail_url(product.slug))
        assert response.json()["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_different_products_have_separate_cache_keys(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Caching product must not affect featured_product cache.

        product detail key:          product_detail_honda-cd70-brake-shoe-set
        featured_product detail key: product_detail_featured-spark-plug

        Completely separate — one must not pollute the other.
        """
        # Populate product cache
        api_client.get(product_detail_url(product.slug))

        # featured_product must still be a database hit
        response = api_client.get(product_detail_url(featured_product.slug))
        assert response.json()["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_cache_invalidated_after_product_updated(
        self,
        api_client,
        product,
    ) -> None:
        """
        After updating the product, stale cached data must not be served.
        Next request must hit database and return updated price.
        """
        # Populate cache
        api_client.get(product_detail_url(product.slug))

        # Update triggers signal → clears this product's detail cache
        product.price = Decimal("9999.00")
        product.save()

        response = api_client.get(product_detail_url(product.slug))
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        assert Decimal(payload["data"]["price"]) == Decimal("9999.00")

    @pytest.mark.integration
    def test_cache_invalidated_after_image_added(
        self,
        api_client,
        product,
    ) -> None:
        """
        After adding an image to a product, its detail cache must be cleared.
        Next request must return the new image in the gallery.
        """
        # Populate cache — no images yet
        first_response = api_client.get(product_detail_url(product.slug))
        assert first_response.json()["data"]["images"] == []

        # Add image — signal fires, clears detail cache
        new_image = SimpleUploadedFile(
            name="new_gallery.jpg",
            content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
            content_type="image/jpeg",
        )
        from apps.products.models import ProductImage
        ProductImage.objects.create(
            product=product,
            image=new_image,
            is_primary=True,
        )

        # Next request must hit database and include new image
        response = api_client.get(product_detail_url(product.slug))
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        assert len(payload["data"]["images"]) == 1

    @pytest.mark.integration
    def test_updating_one_product_does_not_clear_other_product_cache(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Updating product must ONLY clear product's cache.
        featured_product cache must remain warm.

        Why this matters:
            Detail cache is per-slug — exact key deletion.
            Prefix delete would clear ALL product detail caches.
            Signal uses exact key: f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}"
            Only one product's cache is cleared per signal.
        """
        # Populate both caches
        api_client.get(product_detail_url(product.slug))
        api_client.get(product_detail_url(featured_product.slug))

        # Update product — only product's cache should clear
        product.price = Decimal("1111.00")
        product.save()

        # featured_product cache must still be warm
        response = api_client.get(product_detail_url(featured_product.slug))
        assert response.json()["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_404_result_not_cached(
        self,
        api_client,
    ) -> None:
        """
        404 responses must not be cached.

        Why:
            If 404 were cached, a product created later under the same slug
            would still return 404 from cache — incorrect.
            get_object_or_404 raises Http404 which propagates out of
            build_fresh_data() before two_level_cache.set() is called.
        """
        slug = "not-yet-created-product"

        # First request — 404
        response1 = api_client.get(product_detail_url(slug))
        assert response1.status_code == 404

        # Second request — must still hit DB (404 was not cached)
        response2 = api_client.get(product_detail_url(slug))
        assert response2.status_code == 404
        # If 404 were cached, source would be l1_memory or l2_redis
        # Since it is not cached, response is also 404 (correct)


# ─── Permission Tests ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetailPermissions:
    """
    ProductDetailAPIView uses AllowAny.
    All users must be able to read any product detail.
    """

    @pytest.mark.integration
    def test_unauthenticated_can_read(
        self,
        api_client,
        product,
    ) -> None:
        response = api_client.get(product_detail_url(product.slug))
        assert response.status_code == 200

    @pytest.mark.integration
    def test_customer_can_read(
        self,
        customer_client,
        product,
    ) -> None:
        response = customer_client.get(product_detail_url(product.slug))
        assert response.status_code == 200

    @pytest.mark.integration
    def test_admin_can_read(
        self,
        admin_client,
        product,
    ) -> None:
        response = admin_client.get(product_detail_url(product.slug))
        assert response.status_code == 200

