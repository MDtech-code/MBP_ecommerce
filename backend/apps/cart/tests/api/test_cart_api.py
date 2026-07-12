# apps/cart/tests/api/test_cart_api.py
"""
API integration tests for all cart endpoints.

Endpoints covered:
    GET    /api/cart/                  → CartDetailAPIView
    POST   /api/cart/items/            → AddToCartAPIView
    PATCH  /api/cart/items/<id>/       → UpdateCartItemAPIView.patch
    DELETE /api/cart/items/<id>/       → UpdateCartItemAPIView.delete
    DELETE /api/cart/clear/            → ClearCartAPIView

Test strategy:
    - Every endpoint tested for: success, auth, validation, ownership
    - Response envelope shape verified on every success response
    - Error shape verified on every error response
    - No mocking — real DB, real serializers, real views

Markers:
    integration — full HTTP stack
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.cart.models import Cart, CartItem
from apps.cart.tests.conftest import (
    CART_ADD_URL,
    CART_CLEAR_URL,
    CART_DETAIL_URL,
    cart_item_url,
)

pytestmark = pytest.mark.django_db


# ─── Response shape helpers ───────────────────────────────────────────────────

def assert_success_envelope(response, expected_status: int = 200):
    """Assert standard success envelope shape."""
    assert response.status_code == expected_status
    data = response.json()
    assert data["success"] is True
    assert data["message"] is not None
    assert data["errors"] is None
    assert "data" in data
    return data


def assert_error_envelope(response, expected_status: int = 400):
    """Assert standard error envelope shape."""
    assert response.status_code == expected_status
    data = response.json()
    assert data["success"] is False
    assert data["data"] is None
    assert data["errors"] is not None
    assert "code" in data["errors"]
    return data


# ─── GET /api/cart/ ───────────────────────────────────────────────────────────

class TestCartDetail:
    """Tests for GET /api/cart/ — CartDetailAPIView."""

    def test_get_cart_success(self, auth_client):
        """
        Authenticated user gets their cart with 200.

        Cart is empty — created by signal on user creation.
        """
        response = auth_client.get(CART_DETAIL_URL)
        data = assert_success_envelope(response, 200)

        cart_data = data["data"]
        assert "items" in cart_data
        assert "total_items" in cart_data
        assert "total_price" in cart_data
        assert "is_empty" in cart_data

    def test_empty_cart_response_shape(self, auth_client):
        """Empty cart returns is_empty=True and items=[]."""
        response = auth_client.get(CART_DETAIL_URL)
        cart_data = response.json()["data"]

        assert cart_data["is_empty"] is True
        assert cart_data["items"] == []
        assert cart_data["total_items"] == 0
        assert Decimal(cart_data["total_price"]) == Decimal("0.00")

    def test_cart_with_items_response(self, auth_client, cart_item):
        """Cart with items returns correct totals and item details."""
        response = auth_client.get(CART_DETAIL_URL)
        cart_data = response.json()["data"]

        assert cart_data["is_empty"] is False
        assert len(cart_data["items"]) == 1
        assert cart_data["total_items"] == 2  # cart_item.quantity = 2

    def test_cart_item_shape(self, auth_client, cart_item, product):
        """Cart item in response has all expected fields."""
        response = auth_client.get(CART_DETAIL_URL)
        item = response.json()["data"]["items"][0]

        expected_fields = {
            "id",
            "product_name",
            "product_slug",
            "product_price",
            "product_image",
            "is_in_stock",
            "quantity",
            "subtotal",
            "created_at",
            "updated_at",
        }
        assert expected_fields.issubset(set(item.keys()))
        assert item["product_name"] == product.name
        assert item["quantity"] == 2

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated request to cart returns 401."""
        response = api_client.get(CART_DETAIL_URL)
        assert response.status_code == 401

    def test_cart_belongs_to_requesting_user(
        self, auth_client, other_client, cart_item, other_cart_item
    ):
        """
        Each user sees only their own cart.

        auth_client has cart_item (product, qty=2)
        other_client has other_cart_item (same product, qty=1)
        """
        response = auth_client.get(CART_DETAIL_URL)
        cart_data = response.json()["data"]

        # auth_client's cart has 1 item with qty=2
        assert len(cart_data["items"]) == 1
        assert cart_data["total_items"] == 2

    def test_meta_contains_request_id(self, auth_client):
        """Every cart response includes request_id in meta."""
        response = auth_client.get(CART_DETAIL_URL)
        meta = response.json()["meta"]
        assert "request_id" in meta


# ─── POST /api/cart/items/ ────────────────────────────────────────────────────

class TestAddToCart:
    """Tests for POST /api/cart/items/ — AddToCartAPIView."""

    def test_add_product_creates_cart_item(self, auth_client, product):
        """
        POST with valid product_id and quantity creates CartItem.

        Returns 201 with full cart data.
        """
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 1},
            format="json",
        )
        data = assert_success_envelope(response, 201)
        assert len(data["data"]["items"]) == 1

    def test_add_product_returns_201(self, auth_client, product):
        """Successful add returns 201 Created."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 2},
            format="json",
        )
        assert response.status_code == 201

    def test_added_item_quantity_correct(self, auth_client, product):
        """Added item has the requested quantity."""
        auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 3},
            format="json",
        )
        item = CartItem.objects.get(product=product)
        assert item.quantity == 3

    def test_upsert_increases_quantity_for_existing_item(
        self, auth_client, product, cart_item
    ):
        """
        Adding same product again increases quantity — no duplicate item.

        cart_item already has quantity=2.
        Adding 3 more → quantity becomes 5.
        """
        auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 3},
            format="json",
        )
        cart_item.refresh_from_db()
        assert cart_item.quantity == 5
        assert CartItem.objects.filter(product=product).count() == 1

    def test_upsert_returns_updated_cart(self, auth_client, product, cart_item):
        """Upsert response contains updated total_items."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 1},
            format="json",
        )
        cart_data = response.json()["data"]
        # cart_item.quantity=2 + added 1 = 3
        assert cart_data["total_items"] == 3

    def test_add_multiple_different_products(
        self, auth_client, product, second_product
    ):
        """Multiple different products can be added to cart."""
        auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 1},
            format="json",
        )
        auth_client.post(
            CART_ADD_URL,
            data={"product_id": second_product.id, "quantity": 2},
            format="json",
        )
        response = auth_client.get(CART_DETAIL_URL)
        cart_data = response.json()["data"]
        assert len(cart_data["items"]) == 2
        assert cart_data["total_items"] == 3

    def test_unauthenticated_returns_401(self, api_client, product):
        """Unauthenticated add to cart returns 401."""
        response = api_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 1},
            format="json",
        )
        assert response.status_code == 401

    def test_nonexistent_product_returns_400(self, auth_client):
        """Non-existent product_id returns 400 with structured errors."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": 99999, "quantity": 1},
            format="json",
        )
        data = assert_error_envelope(response, 400)
        assert data["errors"]["fields"] is not None
        assert "product_id" in data["errors"]["fields"]

    def test_unavailable_product_returns_400(
        self, auth_client, unavailable_product
    ):
        """OUT_OF_STOCK product returns 400."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": unavailable_product.id, "quantity": 1},
            format="json",
        )
        assert_error_envelope(response, 400)

    def test_quantity_exceeding_stock_returns_400(self, auth_client, product):
        """Quantity greater than stock returns 400 with quantity error."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": product.stock + 1},
            format="json",
        )
        data = assert_error_envelope(response, 400)
        assert "quantity" in data["errors"]["fields"]

    def test_upsert_exceeding_stock_returns_400(
        self, auth_client, low_stock_product, cart
    ):
        """
        Upsert that would exceed stock returns 400.

        low_stock_product.stock = 2
        existing item quantity = 1
        adding 2 more → total 3 > stock 2 → must fail
        """
        CartItem.objects.create(
            cart=cart, product=low_stock_product, quantity=1
        )
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": low_stock_product.id, "quantity": 2},
            format="json",
        )
        data = assert_error_envelope(response, 400)
        assert "quantity" in data["errors"]["fields"]

    def test_missing_product_id_returns_400(self, auth_client):
        """Missing product_id returns 400."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"quantity": 1},
            format="json",
        )
        assert_error_envelope(response, 400)

    def test_zero_quantity_returns_400(self, auth_client, product):
        """quantity=0 rejected by AddToCartSerializer."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 0},
            format="json",
        )
        assert_error_envelope(response, 400)

    def test_response_envelope_shape(self, auth_client, product):
        """Success response has correct envelope structure."""
        response = auth_client.post(
            CART_ADD_URL,
            data={"product_id": product.id, "quantity": 1},
            format="json",
        )
        body = response.json()
        assert body["success"] is True
        assert body["errors"] is None
        assert "meta" in body
        assert "request_id" in body["meta"]


# ─── PATCH /api/cart/items/<id>/ ──────────────────────────────────────────────

class TestUpdateCartItem:
    """Tests for PATCH /api/cart/items/<id>/ — UpdateCartItemAPIView.patch."""

    def test_update_quantity_success(self, auth_client, cart_item):
        """
        PATCH with valid quantity updates cart item.

        cart_item.quantity = 2 → update to 4
        """
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": 4},
            format="json",
        )
        assert_success_envelope(response, 200)
        cart_item.refresh_from_db()
        assert cart_item.quantity == 4

    def test_update_returns_full_cart(self, auth_client, cart_item):
        """PATCH returns full updated cart, not just the item."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": 5},
            format="json",
        )
        data = response.json()["data"]
        assert "total_items" in data
        assert "total_price" in data
        assert "items" in data

    def test_update_total_items_reflects_new_quantity(
        self, auth_client, cart_item
    ):
        """total_items in response reflects new quantity."""
        auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": 7},
            format="json",
        )
        response = auth_client.get(CART_DETAIL_URL)
        assert response.json()["data"]["total_items"] == 7

    def test_unauthenticated_returns_401(self, api_client, cart_item):
        """Unauthenticated PATCH returns 401."""
        response = api_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": 3},
            format="json",
        )
        assert response.status_code == 401

    def test_other_users_item_returns_404(
        self, auth_client, other_cart_item
    ):
        """
        User cannot PATCH another user's cart item.

        Ownership enforced via cart__user=request.user filter.
        Returns 404 — not 403 — to prevent item enumeration.
        """
        response = auth_client.patch(
            cart_item_url(other_cart_item.id),
            data={"quantity": 1},
            format="json",
        )
        assert response.status_code == 404

    def test_nonexistent_item_returns_404(self, auth_client):
        """Non-existent item_id returns 404."""
        response = auth_client.patch(
            cart_item_url(99999),
            data={"quantity": 1},
            format="json",
        )
        assert response.status_code == 404

    def test_quantity_exceeding_stock_returns_400(
        self, auth_client, cart_item, product
    ):
        """
        PATCH quantity > stock returns 400.

        product.stock = 10
        Requesting quantity = 11 → must fail
        """
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": product.stock + 1},
            format="json",
        )
        data = assert_error_envelope(response, 400)
        assert "quantity" in data["errors"]["fields"]

    def test_negative_quantity_returns_400(self, auth_client, cart_item):
        """Negative quantity returns 400."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": -1},
            format="json",
        )
        assert_error_envelope(response, 400)

    def test_missing_quantity_returns_400(self, auth_client, cart_item):
        """Missing quantity field returns 400."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={},
            format="json",
        )
        assert_error_envelope(response, 400)

    def test_quantity_zero_auto_deletes_item(self, auth_client, cart_item):
        """
        PATCH with quantity=0 auto-deletes the item.

        UX: user decrements at qty=1 → frontend sends 0 → item removed.
        Returns 200 with updated cart (not 204 No Content).
        """
        item_id = cart_item.id
        response = auth_client.patch(
            cart_item_url(item_id),
            data={"quantity": 0},
            format="json",
        )
        assert response.status_code == 200
        assert not CartItem.objects.filter(pk=item_id).exists()

    def test_quantity_zero_returns_updated_cart(
        self, auth_client, cart_item
    ):
        """quantity=0 delete returns cart with item removed."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": 0},
            format="json",
        )
        cart_data = response.json()["data"]
        assert cart_data["items"] == []
        assert cart_data["is_empty"] is True

    def test_quantity_zero_success_message(self, auth_client, cart_item):
        """quantity=0 returns 'Item removed from cart.' message."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            data={"quantity": 0},
            format="json",
        )
        assert response.json()["message"] == "Item removed from cart."


# ─── DELETE /api/cart/items/<id>/ ─────────────────────────────────────────────

class TestDeleteCartItem:
    """Tests for DELETE /api/cart/items/<id>/ — UpdateCartItemAPIView.delete."""

    def test_delete_item_success(self, auth_client, cart_item):
        """DELETE removes the cart item and returns 200 with updated cart."""
        item_id = cart_item.id
        response = auth_client.delete(cart_item_url(item_id))
        assert response.status_code == 200
        assert not CartItem.objects.filter(pk=item_id).exists()

    def test_delete_returns_updated_cart(
        self, auth_client, cart_item, second_cart_item
    ):
        """
        DELETE returns full cart with remaining items.

        cart has 2 items — delete first → cart shows 1 item.
        """
        response = auth_client.delete(cart_item_url(cart_item.id))
        cart_data = response.json()["data"]

        assert len(cart_data["items"]) == 1
        assert cart_data["items"][0]["id"] == second_cart_item.id

    def test_delete_updates_total_price(
        self, auth_client, cart_item, second_cart_item
    ):
        """
        total_price updates after item deletion.

        Before: 2×850 + 1×350 = 2050
        After deleting cart_item: 1×350 = 350
        """
        auth_client.delete(cart_item_url(cart_item.id))
        response = auth_client.get(CART_DETAIL_URL)
        cart_data = response.json()["data"]
        assert Decimal(cart_data["total_price"]) == Decimal("350.00")

    def test_unauthenticated_returns_401(self, api_client, cart_item):
        """Unauthenticated DELETE returns 401."""
        response = api_client.delete(cart_item_url(cart_item.id))
        assert response.status_code == 401

    def test_other_users_item_returns_404(
        self, auth_client, other_cart_item
    ):
        """User cannot DELETE another user's cart item — returns 404."""
        response = auth_client.delete(cart_item_url(other_cart_item.id))
        assert response.status_code == 404

    def test_nonexistent_item_returns_404(self, auth_client):
        """Non-existent item returns 404."""
        response = auth_client.delete(cart_item_url(99999))
        assert response.status_code == 404

    def test_delete_success_message(self, auth_client, cart_item):
        """DELETE returns correct success message."""
        response = auth_client.delete(cart_item_url(cart_item.id))
        assert "removed" in response.json()["message"].lower()

    def test_delete_cart_becomes_empty(self, auth_client, cart_item):
        """Deleting last item makes cart empty."""
        auth_client.delete(cart_item_url(cart_item.id))
        response = auth_client.get(CART_DETAIL_URL)
        assert response.json()["data"]["is_empty"] is True


# ─── DELETE /api/cart/clear/ ──────────────────────────────────────────────────

class TestClearCart:
    """Tests for DELETE /api/cart/clear/ — ClearCartAPIView."""

    def test_clear_empty_cart_success(self, auth_client):
        """Clearing an already-empty cart returns 200."""
        response = auth_client.delete(CART_CLEAR_URL)
        assert response.status_code == 200

    def test_clear_removes_all_items(
        self, auth_client, cart_item, second_cart_item, cart
    ):
        """
        Clear removes ALL items from the cart.

        cart has 2 items before clear → 0 items after.
        """
        response = auth_client.delete(CART_CLEAR_URL)
        assert response.status_code == 200
        assert not CartItem.objects.filter(cart=cart).exists()

    def test_clear_returns_empty_cart(
        self, auth_client, cart_item, second_cart_item
    ):
        """Clear response contains empty cart data."""
        response = auth_client.delete(CART_CLEAR_URL)
        cart_data = response.json()["data"]

        assert cart_data["items"] == []
        assert cart_data["total_items"] == 0
        assert cart_data["is_empty"] is True
        assert Decimal(cart_data["total_price"]) == Decimal("0.00")

    def test_clear_success_message(self, auth_client, cart_item):
        """Clear returns correct success message."""
        response = auth_client.delete(CART_CLEAR_URL)
        assert "cleared" in response.json()["message"].lower()

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated clear returns 401."""
        response = api_client.delete(CART_CLEAR_URL)
        assert response.status_code == 401

    def test_other_users_items_not_affected(
        self, auth_client, cart_item, other_cart_item
    ):
        """
        Clearing user's cart does not affect other users' carts.

        auth_client clears their own cart.
        other_cart_item must still exist.
        """
        auth_client.delete(CART_CLEAR_URL)
        assert CartItem.objects.filter(pk=other_cart_item.id).exists()

    def test_clear_only_clears_requesting_users_cart(
        self, auth_client, other_client, product, second_product, cart, other_cart
    ):
        """
        Clear is scoped to requesting user's cart only.

        User A clears → User B's cart untouched.
        """
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        CartItem.objects.create(
            cart=other_cart, product=second_product, quantity=2
        )

        auth_client.delete(CART_CLEAR_URL)

        assert not CartItem.objects.filter(cart=cart).exists()
        assert CartItem.objects.filter(cart=other_cart).count() == 1

    def test_response_envelope_shape(self, auth_client):
        """Clear response has correct envelope structure."""
        response = auth_client.delete(CART_CLEAR_URL)
        body = response.json()
        assert body["success"] is True
        assert body["errors"] is None
        assert "meta" in body
        assert "request_id" in body["meta"]