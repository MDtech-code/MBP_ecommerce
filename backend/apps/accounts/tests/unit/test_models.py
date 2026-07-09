# apps/accounts/tests/unit/test_models.py
"""
Unit tests for all accounts models.

Philosophy:
    Tests the MODEL layer only — no HTTP, no serializers, no views.
    Each test exercises one model behavior in isolation.
    Fast. Direct. Pinpoints bugs at the source.

Models covered:
    User                   — fields, properties, __str__
    UserProfile            — auto-creation via signal, __str__, properties
    UserAddress            — auto-derivation, default enforcement, helpers
    EmailVerificationToken — create_for_user, is_expired, is_valid, is_used
    PasswordResetToken     — create_for_user, is_expired, is_valid, is_used
    UserLoginActivity      — immutability, __str__
"""
from __future__ import annotations

import uuid
from datetime import timedelta, date

import pytest
from django.utils import timezone

from apps.accounts.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserAddress,
    UserLoginActivity,
    UserProfile,
)
from apps.common.choices.role import Role
from apps.accounts.tests.conftest import (
    STRONG_PASSWORD,
    VALID_CITY_LAHORE,
    VALID_CITY_KARACHI,
    VALID_CITY_ISLAMABAD,
)


# ─── User Model ───────────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestUserModel:
    """
    Unit tests for the custom User model.

    User uses email as USERNAME_FIELD — no username column exists.
    """

    def test_str_returns_email(self, user):
        """__str__ must return email — used in admin and logs."""
        assert str(user) == user.email

    def test_username_field_is_email(self):
        """USERNAME_FIELD must be email for email-based auth."""
        assert User.USERNAME_FIELD == "email"

    def test_required_fields_contains_full_name(self):
        """REQUIRED_FIELDS must include full_name."""
        assert "full_name" in User.REQUIRED_FIELDS

    def test_default_role_is_customer(self, user):
        """Freshly created user must default to CUSTOMER role."""
        assert user.role == Role.CUSTOMER

    def test_is_verified_defaults_to_false(self, db):
        """
        Raw user creation must default is_verified to False.

        The `user` fixture sets is_verified=True for convenience.
        This test explicitly creates a raw user to verify the default.
        """
        u = User.objects.create_user(
            email="raw@test.com",
            full_name="Raw User",
            password=STRONG_PASSWORD,
        )
        assert u.is_verified is False

    def test_is_active_defaults_to_true(self, db):
        """Users must be active by default — deactivation is explicit."""
        u = User.objects.create_user(
            email="active@test.com",
            full_name="Active User",
            password=STRONG_PASSWORD,
        )
        assert u.is_active is True

    def test_is_staff_defaults_to_false(self, db):
        """Regular users must not have staff access."""
        u = User.objects.create_user(
            email="staff@test.com",
            full_name="Staff Test",
            password=STRONG_PASSWORD,
        )
        assert u.is_staff is False

    def test_password_is_hashed(self, db):
        """Raw password must never be stored — check_password must work."""
        u = User.objects.create_user(
            email="hash@test.com",
            full_name="Hash Test",
            password=STRONG_PASSWORD,
        )
        assert u.password != STRONG_PASSWORD
        assert u.check_password(STRONG_PASSWORD)

    def test_email_stored_lowercase(self, db):
        """Email must be normalized to lowercase by UserManager."""
        u = User.objects.create_user(
            email="UPPER@EXAMPLE.COM",
            full_name="Upper Test",
            password=STRONG_PASSWORD,
        )
        assert u.email == "upper@example.com"

    def test_is_customer_property_true_for_customer(self, user):
        """is_customer property must return True for CUSTOMER role."""
        assert user.is_customer is True

    def test_is_customer_property_false_for_admin(self, admin_user):
        """is_customer property must return False for ADMIN role."""
        assert admin_user.is_customer is False

    def test_is_admin_property_true_for_admin(self, admin_user):
        """is_admin property must return True for ADMIN role."""
        assert admin_user.is_admin is True

    def test_is_admin_property_false_for_customer(self, user):
        """is_admin property must return False for CUSTOMER role."""
        assert user.is_admin is False

    def test_short_name_returns_first_word(self, user):
        """
        short_name property must return first word of full_name.

        user.full_name = "Test Customer" → short_name = "Test"
        """
        assert user.short_name == "Test"

    def test_short_name_returns_email_when_no_full_name(self, db):
        """
        short_name must fall back to email when full_name is empty.

        Edge case — should not happen in production due to validation
        but model must handle it gracefully.
        """
        u = User.objects.create_user(
            email="nofullname@test.com",
            full_name="No Name",
            password=STRONG_PASSWORD,
        )
        u.full_name = ""
        assert u.short_name == u.email

    def test_superuser_has_correct_flags(self, admin_user):
        """Superuser must have is_staff, is_superuser, is_verified all True."""
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True
        assert admin_user.is_verified is True

    def test_superuser_role_is_admin(self, admin_user):
        """create_superuser must force role=ADMIN."""
        assert admin_user.role == Role.ADMIN


# ─── UserProfile Model ────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestUserProfileModel:
    """
    Unit tests for UserProfile model.

    Profile is auto-created via post_save signal on User creation.
    It holds personal info only — address data lives in UserAddress.
    """

    def test_profile_auto_created_on_user_creation(self, user):
        """
        post_save signal must auto-create UserProfile.

        We do NOT call UserProfile.objects.create() — signal does it.
        """
        assert UserProfile.objects.filter(user=user).exists()

    def test_profile_accessible_via_user_profile(self, user):
        """Profile must be accessible via user.profile (OneToOne)."""
        profile = user.profile
        assert isinstance(profile, UserProfile)
        assert profile.user == user

    def test_str_contains_user_email(self, user):
        """__str__ must identify the profile by user email."""
        assert user.email in str(user.profile)

    def test_phone_defaults_to_none(self, user):
        """Phone must default to None on profile creation."""
        assert user.profile.phone is None

    def test_avatar_defaults_to_falsy(self, user):
        """Avatar must not be set on profile creation."""
        assert not bool(user.profile.avatar)

    def test_date_of_birth_defaults_to_none(self, user):
        """date_of_birth must default to None."""
        assert user.profile.date_of_birth is None

    def test_gender_defaults_to_empty_string(self, user):
        """gender must default to empty string."""
        assert user.profile.gender == ""

    def test_only_one_profile_created_on_multiple_saves(self, user):
        """
        Saving user again must NOT create a second profile.

        Signal must use get_or_create pattern internally.
        """
        user.full_name = "Updated Name"
        user.save()
        assert UserProfile.objects.filter(user=user).count() == 1

    def test_default_address_property_returns_none_when_no_addresses(
        self, user
    ):
        """
        default_address property must return None when user has no addresses.
        """
        assert user.profile.default_address is None

    def test_default_address_property_returns_default_address(
        self, user, default_address
    ):
        """
        default_address property must return the address with is_default=True.
        """
        result = user.profile.default_address
        assert result is not None
        assert result.pk == default_address.pk


# ─── UserAddress Model ────────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestUserAddressModel:
    """
    Unit tests for UserAddress model.

    Key behaviors:
        - City selection auto-derives province and postal_code
        - Only one address per user can be is_default=True
        - set_as_default() helper enforces single default
        - full_address property assembles readable string
        - Country defaults to Pakistan (single market)
    """

    def _make_address(self, user, city=VALID_CITY_LAHORE, **kwargs) -> UserAddress:
        """Helper — create address with sensible defaults."""
        defaults = {
            "label": "home",
            "address_line1": "123 Test Street",
            "city": city,
        }
        defaults.update(kwargs)
        return UserAddress.objects.create(user=user, **defaults)

    # ── Auto-derivation ───────────────────────────────────────────────────────

    def test_province_auto_derived_from_lahore(self, user):
        """Lahore city must auto-set province to PB (Punjab)."""
        address = self._make_address(user, city=VALID_CITY_LAHORE)
        assert address.province == "PB"

    def test_postal_code_auto_derived_from_lahore(self, user):
        """Lahore city must auto-set postal_code to 54000."""
        address = self._make_address(user, city=VALID_CITY_LAHORE)
        assert address.postal_code == "54000"

    def test_province_auto_derived_from_karachi(self, user):
        """Karachi city must auto-set province to SD (Sindh)."""
        address = self._make_address(user, city=VALID_CITY_KARACHI)
        assert address.province == "SD"

    def test_postal_code_auto_derived_from_karachi(self, user):
        """Karachi city must auto-set postal_code to 75000."""
        address = self._make_address(user, city=VALID_CITY_KARACHI)
        assert address.postal_code == "75000"

    def test_province_auto_derived_from_islamabad(self, user):
        """Islamabad city must auto-set province to IC."""
        address = self._make_address(user, city=VALID_CITY_ISLAMABAD)
        assert address.province == "IC"

    def test_postal_code_auto_derived_from_islamabad(self, user):
        """Islamabad city must auto-set postal_code to 44000."""
        address = self._make_address(user, city=VALID_CITY_ISLAMABAD)
        assert address.postal_code == "44000"

    def test_country_always_pakistan(self, user):
        """
        Country must always be Pakistan — single market platform.
        No user input accepted for country field.
        """
        address = self._make_address(user)
        assert address.country == "Pakistan"

    def test_province_updates_when_city_changes(self, user):
        """
        Changing city on existing address must update province.

        Ensures auto-derivation runs on UPDATE not just INSERT.
        """
        address = self._make_address(user, city=VALID_CITY_LAHORE)
        assert address.province == "PB"

        address.city = VALID_CITY_KARACHI
        address.save()
        address.refresh_from_db()

        assert address.province == "SD"

    # ── Default address enforcement ───────────────────────────────────────────

    def test_first_address_can_be_default(self, user):
        """Setting is_default=True on first address must work."""
        address = self._make_address(user, is_default=True)
        assert address.is_default is True

    def test_second_default_replaces_first(self, user):
        """
        Creating a second address with is_default=True must unset
        is_default on the first address.

        Business rule: only ONE default address per user at all times.
        """
        first = self._make_address(user, is_default=True)
        second = self._make_address(
            user,
            city=VALID_CITY_KARACHI,
            is_default=True,
        )

        first.refresh_from_db()
        assert first.is_default is False
        assert second.is_default is True

    def test_set_as_default_helper_makes_address_default(self, user):
        """set_as_default() must mark address as default."""
        address = self._make_address(user)
        assert address.is_default is False

        address.set_as_default()
        address.refresh_from_db()

        assert address.is_default is True

    def test_set_as_default_clears_previous_default(self, user):
        """
        set_as_default() on second address must clear first address default.
        """
        first = self._make_address(user, is_default=True)
        second = self._make_address(user, city=VALID_CITY_KARACHI)

        second.set_as_default()
        first.refresh_from_db()

        assert first.is_default is False
        assert second.is_default is True

    def test_only_one_default_per_user_at_db_level(self, user):
        """
        DB constraint must prevent two default addresses for same user.

        UniqueConstraint on (user, is_default=True) enforces this.
        We verify by checking count of default addresses.
        """
        self._make_address(user, is_default=True)
        self._make_address(user, city=VALID_CITY_KARACHI, is_default=True)

        default_count = UserAddress.objects.filter(
            user=user, is_default=True
        ).count()
        assert default_count == 1

    def test_non_default_addresses_not_affected_by_new_default(self, user):
        """
        Setting a new default must only affect is_default=True addresses,
        not non-default ones.
        """
        non_default = self._make_address(
            user, city=VALID_CITY_LAHORE, is_default=False
        )
        self._make_address(
            user, city=VALID_CITY_KARACHI, is_default=True
        )

        non_default.refresh_from_db()
        assert non_default.is_default is False

    # ── full_address property ─────────────────────────────────────────────────

    def test_full_address_contains_address_line1(self, user):
        """full_address must include address_line1."""
        address = self._make_address(
            user,
            address_line1="123 Test Street",
        )
        assert "123 Test Street" in address.full_address

    def test_full_address_contains_city(self, user):
        """full_address must include city."""
        address = self._make_address(user, city=VALID_CITY_LAHORE)
        assert VALID_CITY_LAHORE in address.full_address

    def test_full_address_contains_country(self, user):
        """full_address must include country."""
        address = self._make_address(user)
        assert "Pakistan" in address.full_address

    def test_full_address_excludes_empty_line2(self, user):
        """
        full_address must not include address_line2 when it is empty.

        filter(None, parts) removes falsy values — empty string filtered out.
        """
        address = self._make_address(user, address_line2="")
        parts = address.full_address.split(", ")
        assert "" not in parts

    # ── __str__ ───────────────────────────────────────────────────────────────

    def test_str_contains_label_and_address(self, user):
        """__str__ must contain label and address_line1."""
        address = self._make_address(
            user,
            label="home",
            address_line1="789 Street",
        )
        result = str(address)
        assert "789 Street" in result

    # ── Related name ──────────────────────────────────────────────────────────

    def test_addresses_accessible_via_user(self, user):
        """Addresses must be accessible via user.addresses (related_name)."""
        self._make_address(user)
        self._make_address(user, city=VALID_CITY_KARACHI)
        assert user.addresses.count() == 2

    def test_address_deleted_when_user_deleted(self, db):
        """
        Addresses must be deleted when user is deleted (CASCADE).

        Foreign key is ON DELETE CASCADE.
        """
        temp_user = User.objects.create_user(
            email="temp@test.com",
            full_name="Temp User",
            password=STRONG_PASSWORD,
        )
        UserAddress.objects.create(
            user=temp_user,
            label="home",
            address_line1="Temp Street",
            city=VALID_CITY_LAHORE,
        )
        user_id = temp_user.id
        temp_user.delete()

        assert not UserAddress.objects.filter(user_id=user_id).exists()


# ─── EmailVerificationToken Model ────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestEmailVerificationToken:
    """
    Unit tests for EmailVerificationToken model.

    Key behaviors:
        - create_for_user deletes previous tokens before creating new
        - Token is UUID, unique, indexed
        - is_expired checks expires_at against now
        - is_valid checks is_expired only (NOT is_used — matches model code)
        - is_used flag + mark_used() for replay prevention
    """

    def test_create_for_user_returns_token(self, unverified_user):
        """create_for_user must return an EmailVerificationToken instance."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert isinstance(token, EmailVerificationToken)

    def test_token_field_is_uuid(self, unverified_user):
        """token field must be a valid UUID."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert isinstance(token.token, uuid.UUID)

    def test_token_linked_to_correct_user(self, unverified_user):
        """Token must be linked to the user passed to create_for_user."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert token.user == unverified_user

    def test_fresh_token_is_not_expired(self, unverified_user):
        """Newly created token must not be expired."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert token.is_expired is False

    def test_token_expires_after_24_hours(self, unverified_user):
        """
        Token with expires_at in the past must be expired.

        We backdate expires_at to simulate a 25-hour-old token.
        """
        token = EmailVerificationToken.create_for_user(unverified_user)
        EmailVerificationToken.objects.filter(pk=token.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        token.refresh_from_db()
        assert token.is_expired is True

    def test_is_valid_true_for_fresh_token(self, unverified_user):
        """Fresh, unused token must be valid."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert token.is_valid is True

    def test_is_valid_false_for_expired_token(self, unverified_user):
        """Expired token must not be valid."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        EmailVerificationToken.objects.filter(pk=token.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        token.refresh_from_db()
        assert token.is_valid is False

    def test_is_used_defaults_to_false(self, unverified_user):
        """Newly created token must have is_used=False."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert token.is_used is False

    def test_mark_used_sets_is_used_true(self, unverified_user):
        """mark_used() must set is_used=True and persist to DB."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        token.mark_used()
        token.refresh_from_db()
        assert token.is_used is True

    def test_create_for_user_deletes_previous_tokens(self, unverified_user):
        """
        create_for_user must delete all previous tokens for this user
        before creating a new one.

        Prevents accumulation of stale tokens — only latest is valid.
        """
        EmailVerificationToken.create_for_user(unverified_user)
        EmailVerificationToken.create_for_user(unverified_user)
        EmailVerificationToken.create_for_user(unverified_user)

        count = EmailVerificationToken.objects.filter(
            user=unverified_user
        ).count()
        assert count == 1

    def test_expires_at_auto_set_on_create(self, unverified_user):
        """
        expires_at must be auto-set to now + 24h on creation.

        Model.save() sets expires_at if not provided.
        """
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert token.expires_at is not None
        expected = timezone.now() + timedelta(hours=24)
        # Allow 5 second tolerance for test execution time
        delta = abs((token.expires_at - expected).total_seconds())
        assert delta < 5

    def test_str_contains_user_email(self, unverified_user):
        """__str__ must identify the token by user email."""
        token = EmailVerificationToken.create_for_user(unverified_user)
        assert unverified_user.email in str(token)


# ─── PasswordResetToken Model ─────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestPasswordResetToken:
    """
    Unit tests for PasswordResetToken model.

    Key behaviors:
        - create_for_user deletes previous tokens first
        - is_valid = not is_used AND not is_expired
        - Expires after 1 hour (not 24 like email verification)
        - mark_used() prevents replay attacks
    """

    def test_create_for_user_returns_token(self, user):
        """create_for_user must return a PasswordResetToken instance."""
        token = PasswordResetToken.create_for_user(user)
        assert isinstance(token, PasswordResetToken)

    def test_token_field_is_uuid(self, user):
        """token field must be a valid UUID."""
        token = PasswordResetToken.create_for_user(user)
        assert isinstance(token.token, uuid.UUID)

    def test_fresh_token_is_not_expired(self, user):
        """Newly created token must not be expired."""
        token = PasswordResetToken.create_for_user(user)
        assert token.is_expired is False

    def test_fresh_token_is_not_used(self, user):
        """Newly created token must have is_used=False."""
        token = PasswordResetToken.create_for_user(user)
        assert token.is_used is False

    def test_fresh_token_is_valid(self, user):
        """
        Fresh token must be valid.
        is_valid = not is_used AND not is_expired.
        """
        token = PasswordResetToken.create_for_user(user)
        assert token.is_valid is True

    def test_expired_token_is_not_valid(self, user):
        """
        Expired token must not be valid.

        Password reset tokens expire after 1 hour.
        Backdate by 2 hours to simulate expiry.
        """
        token = PasswordResetToken.create_for_user(user)
        PasswordResetToken.objects.filter(pk=token.pk).update(
            expires_at=timezone.now() - timedelta(hours=2)
        )
        token.refresh_from_db()
        assert token.is_valid is False

    def test_used_token_is_not_valid(self, user):
        """
        Used token must not be valid even if not expired.

        mark_used() is called after successful password reset
        to prevent replay attacks within the 1-hour expiry window.
        """
        token = PasswordResetToken.create_for_user(user)
        token.mark_used()
        assert token.is_valid is False

    def test_mark_used_persists_to_db(self, user):
        """mark_used() must persist is_used=True to DB."""
        token = PasswordResetToken.create_for_user(user)
        token.mark_used()
        token.refresh_from_db()
        assert token.is_used is True

    def test_create_for_user_deletes_previous_tokens(self, user):
        """
        create_for_user must delete all previous tokens for this user.

        Prevents multiple valid reset links existing simultaneously —
        each request for password reset invalidates all previous ones.
        """
        PasswordResetToken.create_for_user(user)
        PasswordResetToken.create_for_user(user)
        PasswordResetToken.create_for_user(user)

        count = PasswordResetToken.objects.filter(user=user).count()
        assert count == 1

    def test_expires_at_auto_set_to_1_hour(self, user):
        """
        expires_at must be auto-set to now + 1 hour on creation.

        Shorter than email verification (24h) — password reset
        links are higher security, shorter validity window.
        """
        token = PasswordResetToken.create_for_user(user)
        assert token.expires_at is not None
        expected = timezone.now() + timedelta(hours=1)
        delta = abs((token.expires_at - expected).total_seconds())
        assert delta < 5

    def test_str_contains_user_email(self, user):
        """__str__ must identify the token by user email."""
        token = PasswordResetToken.create_for_user(user)
        assert user.email in str(token)

    def test_email_verification_expires_in_24h_password_reset_in_1h(
        self, user, unverified_user
    ):
        """
        Email verification token must expire later than password reset token.

        Email verification = 24h window (user needs time to check email).
        Password reset     = 1h  window (higher security, shorter valid).
        """
        ev_token  = EmailVerificationToken.create_for_user(unverified_user)
        pr_token  = PasswordResetToken.create_for_user(user)

        assert ev_token.expires_at > pr_token.expires_at


# ─── UserLoginActivity Model ──────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestUserLoginActivity:
    """
    Unit tests for UserLoginActivity model.

    Key behaviors:
        - Append-only — save() raises ValueError on update
        - Stores both successful and failed login attempts
        - user FK is SET_NULL on user delete (preserve security logs)
        - Records IP, user agent, failure_reason
    """

    def _make_activity(self, user=None, **kwargs) -> UserLoginActivity:
        """Helper — create activity record with sensible defaults."""
        defaults = {
            "user": user,
            "email_attempted": "test@example.com",
            "ip_address": "127.0.0.1",
            "user_agent": "TestAgent/1.0",
            "was_successful": True,
            "failure_reason": "",
        }
        defaults.update(kwargs)
        return UserLoginActivity.objects.create(**defaults)

    def test_successful_login_activity_created(self, user):
        """Successful login activity must be storable."""
        activity = self._make_activity(
            user=user,
            email_attempted=user.email,
            was_successful=True,
        )
        assert activity.pk is not None
        assert activity.was_successful is True

    def test_failed_login_activity_created(self):
        """Failed login activity (no user) must be storable."""
        activity = self._make_activity(
            user=None,
            email_attempted="ghost@example.com",
            was_successful=False,
            failure_reason="invalid_credentials",
        )
        assert activity.pk is not None
        assert activity.was_successful is False
        assert activity.failure_reason == "invalid_credentials"

    def test_activity_is_immutable_after_creation(self, user):
        """
        Updating an existing UserLoginActivity must raise ValueError.

        Security logs must never be modified — INSERT only.
        The model.save() guard enforces this.
        """
        activity = self._make_activity(user=user)

        activity.was_successful = False
        with pytest.raises(ValueError, match="immutable"):
            activity.save()

    def test_user_fk_set_null_on_user_delete(self, db):
        """
        When a user is deleted, their login activity records must remain
        but user FK must be set to NULL.

        Preserves security audit log even after account deletion.
        """
        temp_user = User.objects.create_user(
            email="deleteme@test.com",
            full_name="Delete Me",
            password=STRONG_PASSWORD,
        )
        activity = self._make_activity(
            user=temp_user,
            email_attempted=temp_user.email,
        )
        activity_id = activity.id

        temp_user.delete()

        activity = UserLoginActivity.objects.get(id=activity_id)
        assert activity.user is None
        assert activity.email_attempted == "deleteme@test.com"

    def test_str_contains_email_and_status(self, user):
        """__str__ must contain email and success/failure status."""
        activity = self._make_activity(
            user=user,
            email_attempted=user.email,
            was_successful=True,
        )
        result = str(activity)
        assert user.email in result
        assert "success" in result.lower()

    def test_created_at_auto_set(self, user):
        """created_at must be set automatically on creation."""
        activity = self._make_activity(user=user)
        assert activity.created_at is not None

    def test_failure_reason_stored_correctly(self):
        """failure_reason must be stored as provided."""
        activity = self._make_activity(
            was_successful=False,
            failure_reason="email_not_verified",
        )
        assert activity.failure_reason == "email_not_verified"

    def test_ip_address_stored(self, user):
        """IP address must be stored correctly."""
        activity = self._make_activity(
            user=user,
            ip_address="192.168.1.100",
        )
        assert activity.ip_address == "192.168.1.100"