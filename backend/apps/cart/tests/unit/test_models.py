# apps/cart/tests/unit/test_models.py
"""
Unit tests for Cart and CartItem models.

Scope:
    - Model properties: total_items, total_price, is_empty, subtotal
    - CartItem.clean() stock validation
    - CartItem.save() calls full_clean()
    - CartItem.__str__ and Cart.__str__
    - unique_together constraint enforcement
    - Decimal precision on monetary values

Markers:
    unit — no HTTP, no serializer, pure model logic
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.cart.models import Cart, CartItem

pytestmark = pytest.mark.django_db


class TestCartModel:
    """Tests for Cart model properties and string representation."""

    # ── __str__ ───────────────────────────────────────────────────────────────

    def test_str_contains_user_email(self, cart, user):
        """Cart __str__ includes user email for admin readability."""
        assert user.email in str(cart)

    def test_str_format(self, cart, user):
        """Cart __str__ matches expected format."""
        assert str(cart) == f"Cart for {user.email}"

    # ── is_empty ──────────────────────────────────────────────────────────────

    def test_is_empty_true_when_no_items(self, cart):
        """Fresh cart with no items is empty."""
        cart_with_items = Cart.objects.prefetch_related("items").get(
            pk=cart.pk
        )
        assert cart_with_items.is_empty is True

    def test_is_empty_false_when_items_exist(self, cart, cart_item):
        """Cart with at least one item is not empty."""
        cart_with_items = Cart.objects.prefetch_related("items").get(
            pk=cart.pk
        )
        assert cart_with_items.is_empty is False

    # ── total_items ───────────────────────────────────────────────────────────

    def test_total_items_zero_for_empty_cart(self, cart):
        """Empty cart has total_items = 0."""
        cart_with_items = Cart.objects.prefetch_related("items").get(
            pk=cart.pk
        )
        assert cart_with_items.total_items == 0

    def test_total_items_sums_quantities(self, cart, cart_item, second_cart_item):
        """
        total_items sums all item quantities.

        cart_item.quantity = 2
        second_cart_item.quantity = 1
        Expected total_items = 3
        """
        cart_with_items = Cart.objects.prefetch_related("items").get(
            pk=cart.pk
        )
        assert cart_with_items.total_items == 3

    def test_total_items_reflects_quantity_update(self, cart, cart_item):
        """total_items updates when item quantity changes."""
        CartItem.objects.filter(pk=cart_item.pk).update(quantity=5)

        cart_with_items = Cart.objects.prefetch_related("items").get(
            pk=cart.pk
        )
        assert cart_with_items.total_items == 5

    # ── total_price ───────────────────────────────────────────────────────────

    def test_total_price_zero_for_empty_cart(self, cart):
        """Empty cart total_price returns Decimal('0.00')."""
        cart_with_items = Cart.objects.prefetch_related(
            "items__product"
        ).get(pk=cart.pk)
        assert cart_with_items.total_price == Decimal("0.00")

    def test_total_price_is_decimal(self, cart):
        """total_price is always Decimal — never float."""
        cart_with_items = Cart.objects.prefetch_related(
            "items__product"
        ).get(pk=cart.pk)
        assert isinstance(cart_with_items.total_price, Decimal)

    def test_total_price_sums_subtotals(self, cart, cart_item, second_cart_item):
        """
        total_price sums item subtotals correctly.

        cart_item: 2 × 850.00 = 1700.00
        second_cart_item: 1 × 350.00 = 350.00
        Expected total = 2050.00
        """
        cart_with_items = Cart.objects.prefetch_related(
            "items__product"
        ).get(pk=cart.pk)
        assert cart_with_items.total_price == Decimal("2050.00")

    def test_total_price_uses_current_price_not_original(
        self, cart, discounted_product, admin_user
    ):
        """
        total_price uses product.current_price (discount-aware).

        discounted_product: price=500.00, discount_price=400.00
        current_price = 400.00
        qty = 1 → subtotal = 400.00
        """
        CartItem.objects.create(
            cart=cart,
            product=discounted_product,
            quantity=1,
        )
        cart_with_items = Cart.objects.prefetch_related(
            "items__product"
        ).get(pk=cart.pk)
        assert cart_with_items.total_price == Decimal("400.00")


class TestCartItemModel:
    """Tests for CartItem model — validation, save, properties, constraints."""

    # ── __str__ ───────────────────────────────────────────────────────────────

    def test_str_format(self, cart_item, product, user):
        """CartItem __str__ shows quantity × product name (user email)."""
        expected = f"2 x {product.name} ({user.email})"
        assert str(cart_item) == expected

    # ── subtotal property ─────────────────────────────────────────────────────

    def test_subtotal_quantity_times_price(self, cart_item, product):
        """
        subtotal = quantity × product.current_price.

        cart_item.quantity = 2
        product.price = 850.00
        Expected subtotal = 1700.00
        """
        assert cart_item.subtotal == Decimal("1700.00")

    def test_subtotal_is_decimal(self, cart_item):
        """subtotal is always Decimal — never float."""
        assert isinstance(cart_item.subtotal, Decimal)

    def test_subtotal_uses_discounted_price(
        self, cart, discounted_product
    ):
        """
        subtotal uses current_price which respects discount.

        discounted_product: price=500.00, discount_price=400.00
        current_price = 400.00
        qty = 3 → subtotal = 1200.00
        """
        item = CartItem.objects.create(
            cart=cart,
            product=discounted_product,
            quantity=3,
        )
        assert item.subtotal == Decimal("1200.00")

    # ── clean() stock validation ───────────────────────────────────────────────

    def test_clean_raises_when_quantity_exceeds_stock(
        self, cart, product
    ):
        """
        clean() raises ValidationError when quantity > product.stock.

        product.stock = 10
        quantity = 11 → must raise ValidationError on quantity field
        """
        item = CartItem(cart=cart, product=product, quantity=11)

        with pytest.raises(ValidationError) as exc_info:
            item.clean()

        assert "quantity" in exc_info.value.message_dict

    def test_clean_passes_when_quantity_equals_stock(
        self, cart, product
    ):
        """
        clean() passes when quantity == product.stock (boundary).

        product.stock = 10
        quantity = 10 → valid
        """
        item = CartItem(cart=cart, product=product, quantity=10)
        item.clean()  # Must not raise

    def test_clean_passes_when_quantity_below_stock(
        self, cart, product
    ):
        """clean() passes for any quantity below stock."""
        item = CartItem(cart=cart, product=product, quantity=1)
        item.clean()  # Must not raise

    def test_clean_error_message_contains_stock_count(
        self, cart, product
    ):
        """ValidationError message includes the actual stock number."""
        item = CartItem(cart=cart, product=product, quantity=99)

        with pytest.raises(ValidationError) as exc_info:
            item.clean()

        error_msg = str(exc_info.value.message_dict["quantity"])
        assert "10" in error_msg  # product.stock = 10

    def test_clean_error_message_contains_product_name(
        self, cart, product
    ):
        """ValidationError message includes the product name."""
        item = CartItem(cart=cart, product=product, quantity=99)

        with pytest.raises(ValidationError) as exc_info:
            item.clean()

        error_msg = str(exc_info.value.message_dict["quantity"])
        assert product.name in error_msg

    # ── save() calls full_clean() ─────────────────────────────────────────────

    def test_save_raises_when_quantity_exceeds_stock(
        self, cart, product
    ):
        """
        save() calls full_clean() internally.

        Exceeding stock via save() must raise ValidationError —
        not silently write invalid data to DB.
        """
        item = CartItem(cart=cart, product=product, quantity=999)

        with pytest.raises(ValidationError):
            item.save()

    def test_save_succeeds_within_stock_limit(self, cart, product):
        """save() with valid quantity persists to DB."""
        item = CartItem(cart=cart, product=product, quantity=5)
        item.save()

        assert CartItem.objects.filter(pk=item.pk).exists()

    # ── unique_together constraint ─────────────────────────────────────────────

    def test_unique_together_prevents_duplicate_cart_product(
        self, cart, product, cart_item
    ):
        """
        Same product cannot appear twice in the same cart.

        unique_together = [["cart", "product"]]
        cart_item already has this product → second create must fail.
        """
        from django.db import IntegrityError

        with pytest.raises((IntegrityError, ValidationError)):
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=1,
            )

    def test_same_product_allowed_in_different_carts(
        self, cart, other_cart, product
    ):
        """
        Same product CAN appear in different users' carts.

        unique_together is per-cart, not global per-product.
        """
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        CartItem.objects.create(
            cart=other_cart, product=product, quantity=1
        )

        assert CartItem.objects.filter(product=product).count() == 2

    # ── ordering ──────────────────────────────────────────────────────────────

    def test_items_ordered_by_created_at_descending(
        self, cart, cart_item, second_cart_item
    ):
        """
        CartItem Meta ordering = ["-created_at"].

        Most recently added item appears first.
        second_cart_item was created after cart_item → appears first.
        """
        items = list(cart.items.all())
        assert items[0].pk == second_cart_item.pk
        assert items[1].pk == cart_item.pk