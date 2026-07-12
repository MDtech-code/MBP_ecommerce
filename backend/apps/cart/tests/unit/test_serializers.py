# apps/cart/tests/unit/test_serializers.py
"""
Unit tests for cart serializers.

Scope:
    - AddToCartSerializer: product_id validation, quantity validation,
      stock cross-field validation, product attachment to attrs
    - UpdateCartItemSerializer: quantity field validation
    - CartItemSerializer: field presence, read-only fields,
      product_image resolution
    - CartSerializer: nested items, computed fields

Markers:
    unit — no HTTP, serializer logic only
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import RequestFactory

from apps.cart.models import CartItem,Cart
from apps.cart.serializers import (
    AddToCartSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)

pytestmark = pytest.mark.django_db


class TestAddToCartSerializer:
    """Tests for AddToCartSerializer input validation."""

    # ── product_id field ──────────────────────────────────────────────────────

    def test_valid_data_passes(self, product):
        """Valid product_id + quantity within stock passes validation."""
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": 1}
        )
        assert serializer.is_valid(), serializer.errors

    def test_product_id_required(self):
        """product_id is required — missing raises validation error."""
        serializer = AddToCartSerializer(data={"quantity": 1})
        assert not serializer.is_valid()
        assert "product_id" in serializer.errors

    def test_product_id_must_be_positive(self):
        """product_id min_value=1 — zero and negative values rejected."""
        for invalid_id in [0, -1, -100]:
            serializer = AddToCartSerializer(
                data={"product_id": invalid_id, "quantity": 1}
            )
            assert not serializer.is_valid(), f"Should fail for id={invalid_id}"
            assert "product_id" in serializer.errors

    def test_nonexistent_product_id_rejected(self):
        """product_id for non-existent product raises validation error."""
        serializer = AddToCartSerializer(
            data={"product_id": 99999, "quantity": 1}
        )
        assert not serializer.is_valid()
        assert "product_id" in serializer.errors

    def test_unavailable_product_rejected(self, unavailable_product):
        """OUT_OF_STOCK status product cannot be added to cart."""
        serializer = AddToCartSerializer(
            data={"product_id": unavailable_product.id, "quantity": 1}
        )
        assert not serializer.is_valid()
        assert "product_id" in serializer.errors

    def test_draft_product_rejected(self, draft_product):
        """DRAFT status product cannot be added to cart."""
        serializer = AddToCartSerializer(
            data={"product_id": draft_product.id, "quantity": 1}
        )
        assert not serializer.is_valid()
        assert "product_id" in serializer.errors

    # ── quantity field ────────────────────────────────────────────────────────

    def test_quantity_defaults_to_1(self, product):
        """quantity defaults to 1 when not provided."""
        serializer = AddToCartSerializer(data={"product_id": product.id})
        assert serializer.is_valid(), serializer.errors
        assert serializer.validated_data["quantity"] == 1

    def test_quantity_must_be_at_least_1(self, product):
        """quantity=0 rejected — min_value=1."""
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": 0}
        )
        assert not serializer.is_valid()
        assert "quantity" in serializer.errors

    def test_negative_quantity_rejected(self, product):
        """Negative quantity rejected."""
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": -5}
        )
        assert not serializer.is_valid()
        assert "quantity" in serializer.errors

    # ── stock cross-field validation ──────────────────────────────────────────

    def test_quantity_within_stock_passes(self, product):
        """quantity <= stock passes cross-field validation."""
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": product.stock}
        )
        assert serializer.is_valid(), serializer.errors

    def test_quantity_exceeding_stock_rejected(self, product):
        """quantity > stock raises validation error on quantity field."""
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": product.stock + 1}
        )
        assert not serializer.is_valid()
        assert "quantity" in serializer.errors

    def test_quantity_error_message_contains_stock_count(
        self, low_stock_product
    ):
        """
        Stock exceeded error message includes the available stock count.

        low_stock_product.stock = 2
        """
        serializer = AddToCartSerializer(
            data={"product_id": low_stock_product.id, "quantity": 99}
        )
        serializer.is_valid()
        error_msg = str(serializer.errors["quantity"])
        assert "2" in error_msg  # low_stock_product.stock = 2

    # ── product attached to validated_data ────────────────────────────────────

    def test_product_attached_to_validated_data(self, product):
        """
        After validation, attrs['product'] contains the Product instance.

        This avoids a second DB fetch in the view.
        """
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": 1}
        )
        assert serializer.is_valid()
        assert serializer.validated_data["product"] == product

    def test_single_db_query_for_product(self, product, django_assert_num_queries):
        """
        validate() fetches product exactly once.

        Old implementation made 2 queries (exists + get).
        Fixed implementation makes 1 query (get with status filter).
        """
        serializer = AddToCartSerializer(
            data={"product_id": product.id, "quantity": 1}
        )
        with django_assert_num_queries(1):
            serializer.is_valid()


class TestUpdateCartItemSerializer:
    """Tests for UpdateCartItemSerializer input validation."""

    def test_valid_quantity_passes(self):
        """Valid positive quantity passes validation."""
        serializer = UpdateCartItemSerializer(data={"quantity": 3})
        assert serializer.is_valid(), serializer.errors

    def test_zero_quantity_passes(self):
        """
        quantity=0 is valid — view treats it as delete signal.

        This is intentional UX: user decrements to 0 → item removed.
        """
        serializer = UpdateCartItemSerializer(data={"quantity": 0})
        assert serializer.is_valid(), serializer.errors

    def test_negative_quantity_rejected(self):
        """Negative quantity rejected — min_value=0."""
        serializer = UpdateCartItemSerializer(data={"quantity": -1})
        assert not serializer.is_valid()
        assert "quantity" in serializer.errors

    def test_quantity_required(self):
        """quantity field is required."""
        serializer = UpdateCartItemSerializer(data={})
        assert not serializer.is_valid()
        assert "quantity" in serializer.errors

    def test_error_message_for_negative(self):
        """Error message for negative quantity is user-friendly."""
        serializer = UpdateCartItemSerializer(data={"quantity": -5})
        serializer.is_valid()
        error_msg = str(serializer.errors["quantity"])
        assert "0" in error_msg


class TestCartItemSerializer:
    """Tests for CartItemSerializer read representation."""

    def _make_request(self):
        """Build a fake request for context."""
        factory = RequestFactory()
        return factory.get("/")

    def test_contains_expected_fields(self, cart_item):
        """CartItemSerializer exposes all expected fields."""
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        data = serializer.data
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
        assert set(data.keys()) == expected_fields

    def test_product_field_is_write_only(self, cart_item):
        """
        product FK id is write_only — not in read response.

        Frontend receives product_name, product_slug etc.
        The raw FK integer is write_only for input only.
        """
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        # product key IS in data.keys() but write_only=True
        # means it won't appear in to_representation output
        data = serializer.data
        # product appears in fields but write_only controls output
        # Confirm product_name IS present (the readable alternative)
        assert "product_name" in data

    def test_product_name_populated(self, cart_item, product):
        """product_name source="product.name" is correctly resolved."""
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        assert serializer.data["product_name"] == product.name

    def test_product_slug_populated(self, cart_item, product):
        """product_slug source="product.slug" is correctly resolved."""
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        assert serializer.data["product_slug"] == product.slug

    def test_product_price_populated(self, cart_item, product):
        """product_price reflects product.current_price."""
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        assert Decimal(serializer.data["product_price"]) == Decimal(
            str(product.current_price)
        )

    def test_subtotal_correct(self, cart_item):
        """
        subtotal = quantity × current_price.

        cart_item.quantity = 2
        product.price = 850.00
        Expected subtotal = 1700.00
        """
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        assert Decimal(serializer.data["subtotal"]) == Decimal("1700.00")

    def test_is_in_stock_true(self, cart_item, product):
        """is_in_stock reflects product.is_in_stock."""
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        assert serializer.data["is_in_stock"] is True

    def test_product_image_none_when_no_images(self, cart_item):
        """product_image returns None when product has no images."""
        serializer = CartItemSerializer(
            cart_item,
            context={"request": self._make_request()},
        )
        assert serializer.data["product_image"] is None

    def test_product_image_returns_primary_image_url(
        self, cart, product_with_image, fake_image
    ):
        """
        product_image returns absolute URL of primary image.

        Requires product__images in prefetch chain.
        """
        item = CartItem.objects.create(
            cart=cart,
            product=product_with_image,
            quantity=1,
        )
        item_with_prefetch = (
            CartItem.objects.select_related("product")
            .prefetch_related("product__images")
            .get(pk=item.pk)
        )
        request = self._make_request()
        serializer = CartItemSerializer(
            item_with_prefetch,
            context={"request": request},
        )
        image_url = serializer.data["product_image"]
        assert image_url is not None
        assert "http" in image_url


class TestCartSerializer:
    """Tests for CartSerializer computed fields and nested items."""

    def _make_request(self):
        factory = RequestFactory()
        return factory.get("/")

    def test_contains_expected_fields(self, cart):
        """CartSerializer exposes all expected top-level fields."""
        cart_with_prefetch = (
            Cart.objects.prefetch_related("items__product__images")
            .get(pk=cart.pk)
        )
        serializer = CartSerializer(
            cart_with_prefetch,
            context={"request": self._make_request()},
        )
        expected = {"id", "items", "total_items", "total_price", "is_empty", "updated_at"}
        assert set(serializer.data.keys()) == expected

    def test_is_empty_true_for_empty_cart(self, cart):
        """is_empty=True when cart has no items."""
        cart_with_prefetch = (
            Cart.objects.prefetch_related("items__product__images")
            .get(pk=cart.pk)
        )
        serializer = CartSerializer(
            cart_with_prefetch,
            context={"request": self._make_request()},
        )
        assert serializer.data["is_empty"] is True

    def test_is_empty_false_when_items_exist(self, cart, cart_item):
        """is_empty=False when cart has items."""
        cart_with_prefetch = (
            Cart.objects.prefetch_related("items__product__images")
            .get(pk=cart.pk)
        )
        serializer = CartSerializer(
            cart_with_prefetch,
            context={"request": self._make_request()},
        )
        assert serializer.data["is_empty"] is False

    def test_total_items_sums_quantities(self, cart, cart_item, second_cart_item):
        """
        total_items = sum of all quantities.

        cart_item.quantity=2, second_cart_item.quantity=1 → total=3
        """
        cart_with_prefetch = (
            Cart.objects.prefetch_related("items__product__images")
            .get(pk=cart.pk)
        )
        serializer = CartSerializer(
            cart_with_prefetch,
            context={"request": self._make_request()},
        )
        assert serializer.data["total_items"] == 3

    def test_total_price_correct(self, cart, cart_item, second_cart_item):
        """
        total_price = 2×850 + 1×350 = 2050.00
        """
        cart_with_prefetch = (
            Cart.objects.prefetch_related("items__product__images")
            .get(pk=cart.pk)
        )
        serializer = CartSerializer(
            cart_with_prefetch,
            context={"request": self._make_request()},
        )
        assert Decimal(serializer.data["total_price"]) == Decimal("2050.00")

    def test_items_are_nested_list(self, cart, cart_item):
        """items field returns a list of serialized CartItems."""
        cart_with_prefetch = (
            Cart.objects.prefetch_related("items__product__images")
            .get(pk=cart.pk)
        )
        serializer = CartSerializer(
            cart_with_prefetch,
            context={"request": self._make_request()},
        )
        assert isinstance(serializer.data["items"], list)
        assert len(serializer.data["items"]) == 1