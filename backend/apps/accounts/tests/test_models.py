# apps/accounts/tests/test_models.py
from __future__ import annotations

import pytest
from django.db import IntegrityError

from apps.common.tests.factories import UserFactory


@pytest.mark.django_db
class TestUserModel:

    # ── String representation ─────────────────────────────────────────────────

    def test_str_returns_email(self):
        user = UserFactory()
        assert str(user) == user.email

    # ── short_name property ───────────────────────────────────────────────────

    def test_short_name_returns_first_word(self):
        user = UserFactory(full_name="John Doe")
        assert user.short_name == "John"

    def test_short_name_falls_back_to_email_when_full_name_empty(self):
        user = UserFactory(full_name="")
        assert user.short_name == user.email

    # ── Role properties ───────────────────────────────────────────────────────

    def test_is_customer_true_for_customer_role(self):
        user = UserFactory()
        assert user.is_customer is True

    def test_is_admin_false_for_customer_role(self):
        user = UserFactory()
        assert user.is_admin is False

    def test_is_admin_true_for_admin_trait(self):
        user = UserFactory(admin=True)
        assert user.is_admin is True

    # ── Defaults ──────────────────────────────────────────────────────────────

    def test_is_active_default_true(self):
        user = UserFactory()
        assert user.is_active is True

    def test_is_verified_default_false(self):
        user = UserFactory()
        assert user.is_verified is False

    def test_is_staff_default_false(self):
        user = UserFactory()
        assert user.is_staff is False

    # ── DB constraints ────────────────────────────────────────────────────────

    def test_email_unique_constraint_enforced(self):
        UserFactory(email="duplicate@example.com")
        with pytest.raises(IntegrityError):
            # bypass set_password — raw create to hit DB constraint
            UserFactory(email="duplicate@example.com")

    def test_create_superuser_sets_is_staff_and_is_superuser(self):
        from apps.accounts.models import User
        user = User.objects.create_superuser(
            email="super@example.com",
            full_name="Super User",
            password="StrongPass123!",
        )
        assert user.is_staff is True
        assert user.is_superuser is True