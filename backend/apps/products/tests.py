from __future__ import annotations

import pytest
from django.core.cache import caches
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.choices.role import Role
from .models import Category, Brand, BikeModel, Product, ProductImage


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    caches['default'].clear()
    caches['local'].clear()
    yield
    caches['default'].clear()
    caches['local'].clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db) -> User:
    return User.objects.create_user(
        email="customer@test.com",
        full_name="Test Customer",
        password="StrongPass123",
        is_verified=True,
    )


@pytest.fixture
def admin(db) -> User:
    return User.objects.create_superuser(
        email="admin@test.com",
        full_name="Admin User",
        password="AdminPass123",
    )


@pytest.fixture
def admin_client(api_client, admin) -> APIClient:
    response = api_client.post("/api/accounts/login/", {
        "email": admin.email,
        "password": "AdminPass123",
    }, format='json')
    token = response.data["data"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def customer_client(api_client, customer) -> APIClient:
    response = api_client.post("/api/accounts/login/", {
        "email": customer.email,
        "password": "StrongPass123",
    }, format='json')
    token = response.data["data"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def category(db) -> Category:
    return Category.objects.create(name="Engine Parts")


@pytest.fixture
def brand(db) -> Brand:
    return Brand.objects.create(name="Honda")


@pytest.fixture
def bike_model(db, brand) -> BikeModel:
    return BikeModel.objects.create(
        brand=brand,
        name="CB150F",
        year_start=2018,
        year_end=2023,
    )


@pytest.fixture
def product(db, category, brand, bike_model) -> Product:
    product = Product.objects.create(
        name="Piston Ring Set",
        category=category,
        brand=brand,
        sku="ENG-PIS-001",
        price=1500,
        stock=10,
    )
    product.compatible_bikes.add(bike_model)
    return product


# ─── Category Tests ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryList:

    def test_list_categories_success(self, api_client, category):
        response = api_client.get("/api/products/categories/")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert len(response.data["data"]) == 1

    def test_categories_cached_on_second_request(self, api_client, category):
        api_client.get("/api/products/categories/")
        response = api_client.get("/api/products/categories/")
        assert response.data["meta"]["source"] == "l1_memory"

    def test_inactive_category_excluded(self, api_client, category):
        category.is_active = False
        category.save()
        response = api_client.get("/api/products/categories/")
        assert len(response.data["data"]) == 0


# ─── Brand Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBrandList:

    def test_list_brands_success(self, api_client, brand):
        response = api_client.get("/api/products/brands/")
        assert response.status_code == 200
        assert len(response.data["data"]) == 1

    def test_brands_cached_on_second_request(self, api_client, brand):
        api_client.get("/api/products/brands/")
        response = api_client.get("/api/products/brands/")
        assert response.data["meta"]["source"] == "l1_memory"


# ─── Bike Model Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBikeModelList:

    def test_list_bike_models_success(self, api_client, bike_model):
        response = api_client.get("/api/products/bike-models/")
        assert response.status_code == 200
        assert len(response.data["data"]) == 1

    def test_filter_bike_models_by_brand(self, api_client, bike_model, brand):
        response = api_client.get(f"/api/products/bike-models/?brand={brand.id}")
        assert response.status_code == 200
        assert response.data["data"][0]["brand"] == brand.id

    def test_filter_bike_models_by_nonexistent_brand(self, api_client, bike_model):
        response = api_client.get("/api/products/bike-models/?brand=9999")
        assert len(response.data["data"]) == 0

    def test_display_name_format(self, api_client, bike_model):
        response = api_client.get("/api/products/bike-models/")
        assert "Honda" in response.data["data"][0]["display_name"]


# ─── Product List Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductList:

    def test_list_products_success(self, api_client, product):
        response = api_client.get("/api/products/")
        assert response.status_code == 200
        assert response.data["success"] is True
        assert len(response.data["data"]) == 1

    def test_product_list_has_pagination_meta(self, api_client, product):
        response = api_client.get("/api/products/")
        meta = response.data["meta"]
        assert "page" in meta
        assert "page_size" in meta
        assert "total_items" in meta
        assert "total_pages" in meta
        assert "source" in meta

    def test_products_cached_on_second_request(self, api_client, product):
        api_client.get("/api/products/")
        response = api_client.get("/api/products/")
        assert response.data["meta"]["source"] == "l1_memory"

    def test_out_of_stock_products_excluded_by_default(self, api_client, product):
        product.status = Product.Status.OUT_OF_STOCK
        product.save()
        response = api_client.get("/api/products/")
        assert len(response.data["data"]) == 0

    def test_filter_by_category(self, api_client, product, category):
        response = api_client.get(f"/api/products/?category={category.slug}")
        assert len(response.data["data"]) == 1

    def test_filter_by_wrong_category_returns_empty(self, api_client, product):
        other_category = Category.objects.create(name="Brakes")
        response = api_client.get(f"/api/products/?category={other_category.slug}")
        assert len(response.data["data"]) == 0

    def test_filter_by_brand(self, api_client, product, brand):
        response = api_client.get(f"/api/products/?brand={brand.slug}")
        assert len(response.data["data"]) == 1

    def test_filter_by_bike_model_compatibility(self, api_client, product, bike_model):
        """The killer feature — filter parts that fit a specific bike."""
        response = api_client.get(f"/api/products/?bike_model={bike_model.id}")
        assert len(response.data["data"]) == 1

    def test_filter_by_incompatible_bike_returns_empty(self, api_client, product, brand):
        other_bike = BikeModel.objects.create(
            brand=brand, name="CG125", year_start=2015,
        )
        response = api_client.get(f"/api/products/?bike_model={other_bike.id}")
        assert len(response.data["data"]) == 0

    def test_filter_by_price_range(self, api_client, product):
        response = api_client.get("/api/products/?min_price=1000&max_price=2000")
        assert len(response.data["data"]) == 1

    def test_filter_by_price_range_excludes_outside(self, api_client, product):
        response = api_client.get("/api/products/?min_price=5000")
        assert len(response.data["data"]) == 0

    def test_search_by_name(self, api_client, product):
        response = api_client.get("/api/products/?q=Piston")
        assert len(response.data["data"]) == 1

    def test_search_by_sku(self, api_client, product):
        response = api_client.get("/api/products/?q=ENG-PIS-001")
        assert len(response.data["data"]) == 1

    def test_search_no_match_returns_empty(self, api_client, product):
        response = api_client.get("/api/products/?q=NonexistentPart")
        assert len(response.data["data"]) == 0

    def test_filter_featured_products(self, api_client, product):
        product.is_featured = True
        product.save()
        response = api_client.get("/api/products/?featured=true")
        assert len(response.data["data"]) == 1

    def test_pagination_page_size(self, api_client, category, brand):
        for i in range(15):
            Product.objects.create(
                name=f"Part {i}", category=category, brand=brand,
                sku=f"SKU-{i}", price=100, stock=5,
            )
        response = api_client.get("/api/products/?page=1&page_size=5")
        assert len(response.data["data"]) == 5
        assert response.data["meta"]["total_items"] == 15
        assert response.data["meta"]["total_pages"] == 3

    def test_different_filters_have_separate_cache_keys(
        self, api_client, product, category
    ):
        """Different filter combos must not share cache entries."""
        response1 = api_client.get("/api/products/")
        response2 = api_client.get(f"/api/products/?category={category.slug}")
        assert response1.data["meta"]["source"] == "database"
        assert response2.data["meta"]["source"] == "database"


# ─── Product Detail Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductDetail:

    def test_get_product_detail_success(self, api_client, product):
        response = api_client.get(f"/api/products/{product.slug}/")
        assert response.status_code == 200
        assert response.data["data"]["sku"] == product.sku

    def test_product_detail_includes_compatible_bikes(
        self, api_client, product, bike_model
    ):
        response = api_client.get(f"/api/products/{product.slug}/")
        bikes = response.data["data"]["compatible_bikes"]
        assert len(bikes) == 1
        assert bikes[0]["id"] == bike_model.id

    def test_product_detail_cached_on_second_request(self, api_client, product):
        api_client.get(f"/api/products/{product.slug}/")
        response = api_client.get(f"/api/products/{product.slug}/")
        assert response.data["meta"]["source"] == "l1_memory"

    def test_get_nonexistent_product_404(self, api_client):
        response = api_client.get("/api/products/does-not-exist/")
        assert response.status_code == 404

    def test_update_product_as_admin_success(self, admin_client, product):
        response = admin_client.put(f"/api/products/{product.slug}/", {
            "price": 1800,
        }, format='json')
        assert response.status_code == 200
        product.refresh_from_db()
        assert product.price == 1800

    def test_update_product_as_customer_forbidden(self, customer_client, product):
        response = customer_client.put(f"/api/products/{product.slug}/", {
            "price": 1800,
        }, format='json')
        assert response.status_code == 403

    def test_update_product_unauthenticated_forbidden(self, api_client, product):
        response = api_client.put(f"/api/products/{product.slug}/", {
            "price": 1800,
        }, format='json')
        assert response.status_code == 403

    def test_update_invalidates_cache(self, api_client, admin_client, product):
        api_client.get(f"/api/products/{product.slug}/")  # warm cache
        admin_client.put(f"/api/products/{product.slug}/", {
            "price": 1800,
        }, format='json')
        response = api_client.get(f"/api/products/{product.slug}/")
        assert response.data["meta"]["source"] == "database"
        assert response.data["data"]["price"] == "1800.00"

    def test_delete_product_as_admin_success(self, admin_client, product):
        response = admin_client.delete(f"/api/products/{product.slug}/")
        assert response.status_code == 200
        assert not Product.objects.filter(id=product.id).exists()

    def test_delete_product_as_customer_forbidden(self, customer_client, product):
        response = customer_client.delete(f"/api/products/{product.slug}/")
        assert response.status_code == 403


# ─── Product Create Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductCreate:

    def test_create_product_as_admin_success(
        self, admin_client, category, brand
    ):
        response = admin_client.post("/api/products/create/", {
            "name": "Brake Pad Set",
            "category": category.id,
            "brand": brand.id,
            "sku": "BRK-PAD-001",
            "price": 800,
            "stock": 20,
        }, format='json')
        assert response.status_code == 201
        assert Product.objects.filter(sku="BRK-PAD-001").exists()

    def test_create_product_as_customer_forbidden(
        self, customer_client, category, brand
    ):
        response = customer_client.post("/api/products/create/", {
            "name": "Brake Pad Set",
            "category": category.id,
            "brand": brand.id,
            "sku": "BRK-PAD-002",
            "price": 800,
            "stock": 20,
        }, format='json')
        assert response.status_code == 403

    def test_create_product_duplicate_sku_fails(self, admin_client, product):
        response = admin_client.post("/api/products/create/", {
            "name": "Different Name",
            "category": product.category.id,
            "sku": product.sku,
            "price": 500,
            "stock": 5,
        }, format='json')
        assert response.status_code == 400
        assert "sku" in response.data["errors"]

    def test_create_product_discount_exceeds_price_fails(
        self, admin_client, category
    ):
        response = admin_client.post("/api/products/create/", {
            "name": "Test Part",
            "category": category.id,
            "sku": "TEST-001",
            "price": 500,
            "discount_price": 600,
            "stock": 5,
        }, format='json')
        assert response.status_code == 400
        assert "discount_price" in response.data["errors"]

    def test_create_product_invalidates_list_cache(
        self, api_client, admin_client, product, category
    ):
        api_client.get("/api/products/")  # warm cache
        admin_client.post("/api/products/create/", {
            "name": "New Part",
            "category": category.id,
            "sku": "NEW-001",
            "price": 300,
            "stock": 5,
        }, format='json')
        response = api_client.get("/api/products/")
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 2


# ─── Model Tests ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductModel:

    def test_slug_auto_generated(self, category):
        product = Product.objects.create(
            name="Test Part Name",
            category=category,
            sku="AUTO-001",
            price=100,
        )
        assert product.slug == "test-part-name"

    def test_current_price_without_discount(self, product):
        assert product.current_price == product.price

    def test_current_price_with_discount(self, category):
        product = Product.objects.create(
            name="Discounted Part",
            category=category,
            sku="DISC-001",
            price=1000,
            discount_price=800,
        )
        assert product.current_price == 800

    def test_has_discount_false_by_default(self, product):
        assert product.has_discount is False

    def test_discount_percentage_calculation(self, category):
        product = Product.objects.create(
            name="Discounted Part",
            category=category,
            sku="DISC-002",
            price=1000,
            discount_price=750,
        )
        assert product.discount_percentage == 25

    def test_is_in_stock_true(self, product):
        assert product.is_in_stock is True

    def test_is_in_stock_false_when_zero_stock(self, category):
        product = Product.objects.create(
            name="Out of Stock Part",
            category=category,
            sku="OOS-001",
            price=100,
            stock=0,
        )
        assert product.is_in_stock is False

    def test_is_compatible_with_bike(self, product, bike_model):
        assert product.is_compatible_with(bike_model.id) is True

    def test_is_compatible_with_wrong_bike(self, product, brand):
        other_bike = BikeModel.objects.create(
            brand=brand, name="CG125", year_start=2015,
        )
        assert product.is_compatible_with(other_bike.id) is False


@pytest.mark.django_db
class TestBikeModelModel:

    def test_str_includes_year_range(self, bike_model):
        assert "2018" in str(bike_model)
        assert "2023" in str(bike_model)

    def test_covers_year_within_range(self, bike_model):
        assert bike_model.covers_year(2020) is True

    def test_covers_year_outside_range(self, bike_model):
        assert bike_model.covers_year(2025) is False

    def test_covers_year_no_end_year(self, brand):
        current_model = BikeModel.objects.create(
            brand=brand, name="CB150R", year_start=2022,
        )
        assert current_model.covers_year(2030) is True


@pytest.mark.django_db
class TestProductImageModel:

    def test_only_one_primary_image_per_product(self, product):
        image1 = ProductImage.objects.create(product=product, is_primary=True)
        image2 = ProductImage.objects.create(product=product, is_primary=True)

        image1.refresh_from_db()
        assert image1.is_primary is False
        assert image2.is_primary is True