# apps/accounts/tests/unit/test_managers.py
"""
Unit tests for UserManager.

UserManager replaces Django's default username-based manager.
It is the single point of user creation across the entire system —
registration serializer, management commands, fixtures, tests all use it.

If email normalization breaks here, users cannot log in.
If password hashing breaks here, security fails silently.

Coverage:
    create_user()      — email normalization, required fields, password hashing
    create_superuser() — flag enforcement, role override, validation
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.common.choices.role import Role
from apps.accounts.tests.conftest import STRONG_PASSWORD

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateUser:
    """Tests for UserManager.create_user()."""

    def test_create_user_returns_user_instance(self, db):
        """create_user must return a User instance."""
        user = User.objects.create_user(
            email="test@example.com",
            full_name="Test User",
            password=STRONG_PASSWORD,
        )
        assert isinstance(user, User)

    def test_create_user_persists_to_db(self, db):
        """Created user must exist in the database."""
        User.objects.create_user(
            email="persist@example.com",
            full_name="Persist User",
            password=STRONG_PASSWORD,
        )
        assert User.objects.filter(email="persist@example.com").exists()

    def test_email_normalized_to_lowercase(self, db):
        """
        Email domain must be normalized to lowercase.

        BaseUserManager.normalize_email lowercases the domain part.
        Combined with our .lower().strip() the full email is lowercase.
        """
        user = User.objects.create_user(
            email="TEST@EXAMPLE.COM",
            full_name="Test User",
            password=STRONG_PASSWORD,
        )
        assert user.email == "test@example.com"

    def test_email_whitespace_stripped(self, db):
        """Leading/trailing whitespace in email must be stripped."""
        user = User.objects.create_user(
            email="  spaces@example.com  ",
            full_name="Spaces User",
            password=STRONG_PASSWORD,
        )
        assert user.email == "spaces@example.com"

    def test_full_name_whitespace_normalized(self, db):
        """
        Internal whitespace in full_name must be normalized.

        "John   Doe" → "John Doe" (multiple spaces collapsed).
        """
        user = User.objects.create_user(
            email="ws@example.com",
            full_name="  John   Doe  ",
            password=STRONG_PASSWORD,
        )
        assert user.full_name == "John Doe"

    def test_password_is_hashed(self, db):
        """
        Raw password must never be stored.
        check_password() must return True for the original password.
        """
        user = User.objects.create_user(
            email="hash@example.com",
            full_name="Hash User",
            password=STRONG_PASSWORD,
        )
        assert user.password != STRONG_PASSWORD
        assert user.check_password(STRONG_PASSWORD)

    def test_create_user_without_email_raises_valueerror(self, db):
        """create_user with empty email must raise ValueError."""
        with pytest.raises(ValueError, match="Email"):
            User.objects.create_user(
                email="",
                full_name="No Email",
                password=STRONG_PASSWORD,
            )

    def test_create_user_without_full_name_raises_valueerror(self, db):
        """create_user with empty full_name must raise ValueError."""
        with pytest.raises(ValueError, match="[Ff]ull name"):
            User.objects.create_user(
                email="nofullname@example.com",
                full_name="",
                password=STRONG_PASSWORD,
            )

    def test_create_user_default_role_is_customer(self, db):
        """Users created via create_user must default to CUSTOMER role."""
        user = User.objects.create_user(
            email="role@example.com",
            full_name="Role Test",
            password=STRONG_PASSWORD,
        )
        assert user.role == Role.CUSTOMER

    def test_create_user_is_not_staff_by_default(self, db):
        """Regular users must not have is_staff=True."""
        user = User.objects.create_user(
            email="staff@example.com",
            full_name="Staff Test",
            password=STRONG_PASSWORD,
        )
        assert user.is_staff is False

    def test_create_user_is_not_superuser_by_default(self, db):
        """Regular users must not have is_superuser=True."""
        user = User.objects.create_user(
            email="super@example.com",
            full_name="Super Test",
            password=STRONG_PASSWORD,
        )
        assert user.is_superuser is False

    def test_create_user_with_none_password_sets_unusable(self, db):
        """
        create_user with password=None must set unusable password.

        Enables social-auth users who have no local password.
        check_password() must return False for any string.
        """
        user = User.objects.create_user(
            email="nopw@example.com",
            full_name="No Password",
            password=None,
        )
        assert not user.has_usable_password()

    def test_extra_fields_passed_through(self, db):
        """
        Extra keyword arguments must be passed to the model.

        Example: is_verified=True can be passed directly.
        """
        user = User.objects.create_user(
            email="extra@example.com",
            full_name="Extra Fields",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        assert user.is_verified is True


@pytest.mark.unit
@pytest.mark.django_db
class TestCreateSuperuser:
    """Tests for UserManager.create_superuser()."""

    def test_create_superuser_sets_is_staff(self, db):
        """create_superuser must set is_staff=True."""
        admin = User.objects.create_superuser(
            email="admin1@example.com",
            full_name="Admin One",
            password=STRONG_PASSWORD,
        )
        assert admin.is_staff is True

    def test_create_superuser_sets_is_superuser(self, db):
        """create_superuser must set is_superuser=True."""
        admin = User.objects.create_superuser(
            email="admin2@example.com",
            full_name="Admin Two",
            password=STRONG_PASSWORD,
        )
        assert admin.is_superuser is True

    def test_create_superuser_sets_is_verified(self, db):
        """create_superuser must set is_verified=True."""
        admin = User.objects.create_superuser(
            email="admin3@example.com",
            full_name="Admin Three",
            password=STRONG_PASSWORD,
        )
        assert admin.is_verified is True

    def test_create_superuser_role_is_admin(self, db):
        """create_superuser must force role=ADMIN."""
        admin = User.objects.create_superuser(
            email="admin4@example.com",
            full_name="Admin Four",
            password=STRONG_PASSWORD,
        )
        assert admin.role == Role.ADMIN

    def test_create_superuser_overrides_non_admin_role(self, db):
        """
        Passing a non-ADMIN role to create_superuser must be overridden.

        Manager logs warning and forces ADMIN role regardless.
        """
        admin = User.objects.create_superuser(
            email="admin5@example.com",
            full_name="Admin Five",
            password=STRONG_PASSWORD,
            role=Role.CUSTOMER,
        )
        assert admin.role == Role.ADMIN

    def test_create_superuser_with_is_staff_false_raises(self, db):
        """
        Explicitly passing is_staff=False to create_superuser must raise ValueError.

        Superuser cannot be staff=False — contradictory state.
        """
        with pytest.raises(ValueError, match="is_staff"):
            User.objects.create_superuser(
                email="admin6@example.com",
                full_name="Admin Six",
                password=STRONG_PASSWORD,
                is_staff=False,
            )

    def test_create_superuser_with_is_superuser_false_raises(self, db):
        """
        Explicitly passing is_superuser=False to create_superuser must raise ValueError.
        """
        with pytest.raises(ValueError, match="is_superuser"):
            User.objects.create_superuser(
                email="admin7@example.com",
                full_name="Admin Seven",
                password=STRONG_PASSWORD,
                is_superuser=False,
            )

    def test_create_superuser_email_normalized(self, db):
        """Email normalization must also apply to superusers."""
        admin = User.objects.create_superuser(
            email="ADMIN8@EXAMPLE.COM",
            full_name="Admin Eight",
            password=STRONG_PASSWORD,
        )
        assert admin.email == "admin8@example.com"

    def test_create_superuser_password_hashed(self, db):
        """Password must be hashed for superusers too."""
        admin = User.objects.create_superuser(
            email="admin9@example.com",
            full_name="Admin Nine",
            password=STRONG_PASSWORD,
        )
        assert admin.check_password(STRONG_PASSWORD)
        assert admin.password != STRONG_PASSWORD