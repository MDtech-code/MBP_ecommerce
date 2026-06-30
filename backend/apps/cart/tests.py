from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.products.models import Category, Brand, Product
from .models import Cart, CartItem


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def api_client() -> APIClient:
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
def product(db, category) -> Product:
    return Product.objects.create(
        name="Piston Ring Set",
        category=category,
        sku="ENG-PIS-001",
        price=1500,
        stock=10,
    )


@pytest.fixture
def low_stock_product(db, category) -> Product:
    return Product.objects.create(
        name="Rare Sensor",
        category=category,
        sku="SEN-001",
        price=2000,
        stock=2,
    )


# ─── Cart Auto-Creation Tests ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartCreation:

    def test_cart_created_automatically_on_user_creation(self, customer):
        assert Cart.objects.filter(user=customer).exists()

    def test_new_cart_is_empty(self, customer):
        assert customer.cart.is_empty is True
        assert customer.cart.total_items == 0


# ─── Cart Detail Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartDetail:

    def test_get_empty_cart(self, customer_client):
        response = customer_client.get("/api/cart/")
        assert response.status_code == 200
        assert response.data["data"]["is_empty"] is True

    def test_get_cart_unauthenticated_fails(self, api_client):
        response = api_client.get("/api/cart/")
        assert response.status_code == 401


# ─── Add To Cart Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAddToCart:

    def test_add_item_success(self, customer_client, product):
        response = customer_client.post("/api/cart/items/", {
            "product_id": product.id,
            "quantity": 2,
        }, format='json')
        assert response.status_code == 201
        assert response.data["data"]["total_items"] == 2

    def test_add_item_default_quantity_is_one(self, customer_client, product):
        response = customer_client.post("/api/cart/items/", {
            "product_id": product.id,
        }, format='json')
        assert response.status_code == 201
        assert response.data["data"]["total_items"] == 1

    def test_add_same_product_twice_increases_quantity(self, customer_client, product):
        customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 2,
        }, format='json')
        response = customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 3,
        }, format='json')
        assert response.data["data"]["total_items"] == 5
        assert CartItem.objects.filter(product=product).count() == 1

    def test_add_item_exceeding_stock_fails(self, customer_client, low_stock_product):
        response = customer_client.post("/api/cart/items/", {
            "product_id": low_stock_product.id,
            "quantity": 10,
        }, format='json')
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    def test_add_item_then_exceed_stock_on_second_add_fails(
        self, customer_client, low_stock_product
    ):
        customer_client.post("/api/cart/items/", {
            "product_id": low_stock_product.id, "quantity": 1,
        }, format='json')
        response = customer_client.post("/api/cart/items/", {
            "product_id": low_stock_product.id, "quantity": 5,
        }, format='json')
        assert response.status_code == 400

    def test_add_nonexistent_product_fails(self, customer_client):
        response = customer_client.post("/api/cart/items/", {
            "product_id": 9999, "quantity": 1,
        }, format='json')
        assert response.status_code == 400

    def test_add_unavailable_product_fails(self, customer_client, product):
        product.status = Product.Status.DISCONTINUED
        product.save()
        response = customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 1,
        }, format='json')
        assert response.status_code == 400

    def test_add_zero_quantity_fails(self, customer_client, product):
        response = customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 0,
        }, format='json')
        assert response.status_code == 400

    def test_add_item_unauthenticated_fails(self, api_client, product):
        response = api_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 1,
        }, format='json')
        assert response.status_code == 401


# ─── Update Cart Item Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpdateCartItem:

    def test_update_quantity_success(self, customer_client, product):
        add_response = customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 1,
        }, format='json')
        item_id = add_response.data["data"]["items"][0]["id"]

        response = customer_client.put(f"/api/cart/items/{item_id}/", {
            "quantity": 5,
        }, format='json')
        assert response.status_code == 200
        assert response.data["data"]["total_items"] == 5

    def test_update_quantity_exceeding_stock_fails(
        self, customer_client, low_stock_product
    ):
        add_response = customer_client.post("/api/cart/items/", {
            "product_id": low_stock_product.id, "quantity": 1,
        }, format='json')
        item_id = add_response.data["data"]["items"][0]["id"]

        response = customer_client.put(f"/api/cart/items/{item_id}/", {
            "quantity": 99,
        }, format='json')
        assert response.status_code == 400

    def test_update_other_users_item_404(self, customer_client, product, api_client, db):
        other_user = User.objects.create_user(
            email="other@test.com", full_name="Other User",
            password="Pass12345", is_verified=True,
        )
        other_cart = other_user.cart
        other_item = CartItem.objects.create(
            cart=other_cart, product=product, quantity=1,
        )

        response = customer_client.put(f"/api/cart/items/{other_item.id}/", {
            "quantity": 2,
        }, format='json')
        assert response.status_code == 404

    def test_remove_item_success(self, customer_client, product):
        add_response = customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 1,
        }, format='json')
        item_id = add_response.data["data"]["items"][0]["id"]

        response = customer_client.delete(f"/api/cart/items/{item_id}/")
        assert response.status_code == 200
        assert response.data["data"]["is_empty"] is True

    def test_remove_nonexistent_item_404(self, customer_client):
        response = customer_client.delete("/api/cart/items/9999/")
        assert response.status_code == 404


# ─── Clear Cart Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClearCart:

    def test_clear_cart_success(self, customer_client, product, low_stock_product):
        customer_client.post("/api/cart/items/", {
            "product_id": product.id, "quantity": 1,
        }, format='json')
        customer_client.post("/api/cart/items/", {
            "product_id": low_stock_product.id, "quantity": 1,
        }, format='json')

        response = customer_client.delete("/api/cart/clear/")
        assert response.status_code == 200
        assert response.data["data"]["is_empty"] is True

    def test_clear_empty_cart_does_not_error(self, customer_client):
        response = customer_client.delete("/api/cart/clear/")
        assert response.status_code == 200


# ─── Model Tests ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartModel:

    def test_total_price_calculation(self, customer, product):
        CartItem.objects.create(cart=customer.cart, product=product, quantity=2)
        assert customer.cart.total_price == 3000.0

    def test_total_price_uses_discount_price_when_set(self, customer, category):
        discounted = Product.objects.create(
            name="Sale Item", category=category, sku="SALE-001",
            price=1000, discount_price=700, stock=5,
        )
        CartItem.objects.create(cart=customer.cart, product=discounted, quantity=2)
        assert customer.cart.total_price == 1400.0

    def test_cart_item_subtotal(self, customer, product):
        item = CartItem.objects.create(cart=customer.cart, product=product, quantity=3)
        assert item.subtotal == 4500.0

    def test_cart_item_quantity_exceeding_stock_raises_on_save(self, customer, low_stock_product):
        from django.core.exceptions import ValidationError
        item = CartItem(cart=customer.cart, product=low_stock_product, quantity=10)
        with pytest.raises(ValidationError):
            item.save()

    def test_unique_together_prevents_duplicate_product_rows(self, customer, product):
        CartItem.objects.create(cart=customer.cart, product=product, quantity=1)
        with pytest.raises(Exception):
            CartItem.objects.create(cart=customer.cart, product=product, quantity=1)