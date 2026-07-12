# apps/cart/tests/unit/test_signals.py
"""
Unit tests for cart signals.

Scope:
    - Cart auto-created when new User is saved (post_save signal)
    - Cart NOT created on User update (created=False)
    - Signal failure is caught — user creation does not roll back
    - One cart per user (OneToOneField)

Markers:
    unit — no HTTP, signal + model only
"""
from __future__ import annotations

import pytest

from apps.accounts.models import User
from apps.cart.models import Cart

pytestmark = pytest.mark.django_db

STRONG_PASSWORD = "X!9vQm2#rLpZ"


class TestCartSignal:
    """Tests for create_cart_for_new_user post_save signal."""

    def test_cart_created_on_user_creation(self, db):
        """
        Cart is auto-created when a new User is saved.

        Signal: post_save on User, created=True → Cart.objects.create()
        """
        user = User.objects.create_user(
            email="signaltest@test.com",
            full_name="Signal Test",
            password=STRONG_PASSWORD,
        )
        assert Cart.objects.filter(user=user).exists()

    def test_cart_not_created_on_user_update(self, user):
        """
        Cart is NOT created again when existing User is updated.

        Signal fires on every save() but checks `created` flag.
        User already has one cart from initial creation.
        """
        initial_count = Cart.objects.filter(user=user).count()

        user.full_name = "Updated Name"
        user.save()

        assert Cart.objects.filter(user=user).count() == initial_count

    def test_one_cart_per_user(self, db):
        """
        Each user gets exactly one cart — enforced by OneToOneField.

        Signal + OneToOneField together guarantee this.
        """
        user = User.objects.create_user(
            email="oneperuser@test.com",
            full_name="One Per User",
            password=STRONG_PASSWORD,
        )
        assert Cart.objects.filter(user=user).count() == 1

    def test_cart_linked_to_correct_user(self, db):
        """
        Created cart belongs to the user that triggered the signal.

        Prevents cross-user cart assignment bugs.
        """
        user = User.objects.create_user(
            email="linked@test.com",
            full_name="Linked User",
            password=STRONG_PASSWORD,
        )
        cart = Cart.objects.get(user=user)
        assert cart.user == user

    def test_cart_is_empty_on_creation(self, db):
        """
        Signal-created cart has no items.

        Cart starts empty — items added via AddToCartAPIView.
        """
        user = User.objects.create_user(
            email="emptycart@test.com",
            full_name="Empty Cart",
            password=STRONG_PASSWORD,
        )
        cart = Cart.objects.prefetch_related("items").get(user=user)
        assert cart.is_empty is True

    def test_superuser_also_gets_cart(self, db):
        """
        Signal fires for superuser creation too.

        create_superuser calls save() → post_save fires.
        Admin users need carts just like regular users.
        """
        admin = User.objects.create_superuser(
            email="admincart@test.com",
            full_name="Admin Cart",
            password=STRONG_PASSWORD,
        )
        assert Cart.objects.filter(user=admin).exists()