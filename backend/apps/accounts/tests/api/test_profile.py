# backend/apps/accounts/tests/api/test_profile.py
"""
Profile endpoint tests.

Endpoints:
    GET   /api/accounts/profile/        — retrieve own profile
    PATCH /api/accounts/profile/        — partial update own profile
    PUT   /api/accounts/profile/        — alias for PATCH
    POST  /api/accounts/profile/avatar/ — upload avatar

Views:
    ProfileView
    AvatarUploadView

Serializers exercised:
    UserSerializer         — read-only envelope (id, email, profile, addresses,
                             default_address, short_name, role_display)
    ProfileUpdateSerializer — writable profile fields (phone, dob, gender)
    AvatarUploadSerializer  — file validation

Covers:
    - Authentication enforcement (all endpoints)
    - GET: response shape, all UserSerializer fields including
           addresses list and default_address method field
    - PATCH/PUT: partial update, DB persistence, response reflects save
    - Phone validation (Pakistani format)
    - Date of birth validation (past only)
    - Gender choice validation
    - Avatar: happy path, size limit, MIME type, DB persistence
    - Address fields NO LONGER on profile (regression guard)
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from apps.accounts.models import UserAddress
from apps.accounts.tests.conftest import (
    AVATAR_UPLOAD_URL,
    PROFILE_URL,
    STRONG_PASSWORD,
    VALID_CITY_KARACHI,
    VALID_CITY_LAHORE,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GET PROFILE  —  GET /api/accounts/profile/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestProfileGetAuthentication:

    def test_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated GET."""
        response = api_client.get(PROFILE_URL)
        assert response.status_code == 401

    def test_authenticated_returns_200(self, auth_client):
        """Authenticated user must receive 200."""
        response = auth_client.get(PROFILE_URL)
        assert response.status_code == 200
        assert response.data["success"] is True


@pytest.mark.django_db
class TestProfileGetResponseShape:
    """
    Envelope + field presence tests.

    Why test field presence separately from values:
        If a field is accidentally removed from UserSerializer.Meta.fields
        or a SerializerMethodField is broken, these tests catch it immediately
        without needing specific value assertions.
    """

    def test_envelope_keys_present(self, auth_client):
        """Standard envelope must contain all five keys."""
        response = auth_client.get(PROFILE_URL)
        data = response.data
        for key in ("success", "message", "data", "errors", "meta"):
            assert key in data, f"Missing envelope key: '{key}'"

    def test_core_user_fields_present(self, auth_client, user):
        """
        Core user fields from UserSerializer must be in response data.

        Covers: id, email, full_name, short_name, role,
                role_display, is_verified, date_joined.
        """
        response = auth_client.get(PROFILE_URL)
        data = response.data["data"]

        expected = [
            "id", "email", "full_name", "short_name",
            "role", "role_display", "is_verified", "date_joined",
        ]
        for field in expected:
            assert field in data, f"Missing user field: '{field}'"

    def test_core_user_field_values(self, auth_client, user):
        """Core user field values must match the authenticated user."""
        response = auth_client.get(PROFILE_URL)
        data = response.data["data"]

        assert data["email"] == user.email
        assert data["full_name"] == user.full_name
        assert data["is_verified"] == user.is_verified

    def test_short_name_present_and_non_empty(self, auth_client):
        """
        short_name is a model property — must be non-empty string.

        'Test Customer' → short_name = 'Test' (first word).
        If the property breaks, this catches it immediately.
        """
        response = auth_client.get(PROFILE_URL)
        short_name = response.data["data"]["short_name"]
        assert short_name
        assert isinstance(short_name, str)

    def test_role_display_present_and_non_empty(self, auth_client):
        """
        role_display is get_role_display() — human-readable role label.
        Must be non-empty for all valid roles.
        """
        response = auth_client.get(PROFILE_URL)
        role_display = response.data["data"]["role_display"]
        assert role_display
        assert isinstance(role_display, str)

    def test_nested_profile_object_present(self, auth_client):
        """
        profile must be a nested object, not null.
        Signal creates it on user creation — must always exist.
        """
        response = auth_client.get(PROFILE_URL)
        profile = response.data["data"]["profile"]
        assert profile is not None
        assert isinstance(profile, dict)

    def test_nested_profile_fields_present(self, auth_client):
        """
        UserProfileSerializer fields must all be present in nested profile.
        """
        response = auth_client.get(PROFILE_URL)
        profile = response.data["data"]["profile"]

        expected_profile_fields = [
            "phone", "date_of_birth", "gender",
            "gender_display", "avatar", "created_at", "updated_at",
        ]
        for field in expected_profile_fields:
            assert field in profile, (
                f"Missing profile field: '{field}'"
            )

    def test_addresses_field_is_list(self, auth_client):
        """
        addresses must be a list in the response.
        Empty list for user with no addresses — not null, not missing.

        Why: Frontend iterates over addresses — null would crash JS.
        """
        response = auth_client.get(PROFILE_URL)
        addresses = response.data["data"]["addresses"]
        assert isinstance(addresses, list)

    def test_addresses_empty_when_no_addresses(self, auth_client):
        """
        User with no addresses must have addresses = [].
        """
        response = auth_client.get(PROFILE_URL)
        assert response.data["data"]["addresses"] == []

    def test_addresses_populated_when_addresses_exist(
        self,
        auth_client,
        user,
        user_address,
    ):
        """
        Addresses belonging to the user must appear in the list.
        Count must match.
        """
        response = auth_client.get(PROFILE_URL)
        addresses = response.data["data"]["addresses"]
        assert len(addresses) == 1
        assert addresses[0]["id"] == user_address.pk

    def test_default_address_is_none_when_no_default(self, auth_client):
        """
        default_address must be null when no address has is_default=True.

        Why: Frontend shows 'no default address set' UI based on null.
        """
        response = auth_client.get(PROFILE_URL)
        assert response.data["data"]["default_address"] is None

    def test_default_address_returned_when_set(
        self,
        auth_client,
        user,
        default_address,
    ):
        """
        default_address must contain the serialized default address.

        default_address fixture creates an address with is_default=True.
        get_default_address() SerializerMethodField must find and return it.
        """
        response = auth_client.get(PROFILE_URL)
        default = response.data["data"]["default_address"]

        assert default is not None
        assert default["id"] == default_address.pk
        assert default["is_default"] is True

    def test_default_address_matches_correct_address(
        self,
        auth_client,
        user,
    ):
        """
        When multiple addresses exist, only the default one is returned
        in default_address — not the first or last.
        """
        # Non-default address
        UserAddress.objects.create(
            user=user,
            label="home",
            address_line1="10 First Street",
            city=VALID_CITY_LAHORE,
            is_default=False,
        )
        # Default address
        default = UserAddress.objects.create(
            user=user,
            label="office",
            address_line1="20 Default Avenue",
            city=VALID_CITY_KARACHI,
            is_default=True,
        )

        response = auth_client.get(PROFILE_URL)
        returned_default = response.data["data"]["default_address"]

        assert returned_default is not None
        assert returned_default["id"] == default.pk

    def test_profile_does_not_contain_address_fields_directly(
        self,
        auth_client,
    ):
        """
        Regression guard: address fields must NOT appear directly
        on the profile object after the UserAddress model extraction.

        Before refactor: profile had city, province, postal_code, etc.
        After refactor: those fields live on UserAddress, not UserProfile.
        If someone accidentally adds them back to UserProfileSerializer,
        this test catches it.
        """
        response = auth_client.get(PROFILE_URL)
        profile = response.data["data"]["profile"]

        removed_fields = [
            "city", "province", "postal_code",
            "country", "address_line1", "address_line2",
        ]
        for field in removed_fields:
            assert field not in profile, (
                f"Field '{field}' must not be on profile — "
                f"it belongs to UserAddress now."
            )


# ═══════════════════════════════════════════════════════════════════════════════
# UPDATE PROFILE  —  PATCH /api/accounts/profile/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestProfileUpdateAuthentication:

    def test_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated PATCH."""
        response = api_client.patch(
            PROFILE_URL,
            {"phone": "03001234567"},
            format="json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestProfileUpdateHappyPath:

    def test_patch_returns_200(self, auth_client):
        """Valid partial update must return 200."""
        response = auth_client.patch(
            PROFILE_URL,
            {"phone": "03001234567"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_patch_response_envelope_shape(self, auth_client):
        """Response must conform to standardized envelope."""
        response = auth_client.patch(
            PROFILE_URL,
            {"phone": "03001234567"},
            format="json",
        )
        data = response.data
        for key in ("success", "message", "data", "errors", "meta"):
            assert key in data, f"Missing envelope key: '{key}'"

    def test_patch_persists_phone_to_db(self, auth_client, user):
        """Updated phone must be persisted — re-fetch from DB to confirm."""
        auth_client.patch(
            PROFILE_URL,
            {"phone": "03001234588"},
            format="json",
        )
        user.profile.refresh_from_db()
        assert user.profile.phone == "03001234588"

    def test_patch_response_reflects_updated_phone(self, auth_client):
        """
        Response data must contain the newly saved phone value.

        Why: Do not trust the DB assertion alone — the response could
        return stale data if the view does not re-fetch after save.
        ProfileView re-fetches via _get_user_with_profile_address()
        — this test confirms that re-fetch is working.
        """
        response = auth_client.patch(
            PROFILE_URL,
            {"phone": "03001234599"},
            format="json",
        )
        assert response.data["data"]["profile"]["phone"] == "03001234599"

    def test_patch_persists_date_of_birth(self, auth_client, user):
        """Date of birth update must be persisted."""
        auth_client.patch(
            PROFILE_URL,
            {"date_of_birth": "1990-06-15"},
            format="json",
        )
        user.profile.refresh_from_db()
        assert str(user.profile.date_of_birth) == "1990-06-15"

    def test_patch_persists_gender(self, auth_client, user):
        """Gender update must be persisted."""
        auth_client.patch(
            PROFILE_URL,
            {"gender": "M"},
            format="json",
        )
        user.profile.refresh_from_db()
        assert user.profile.gender == "M"

    def test_patch_is_partial_unset_fields_unchanged(
        self,
        auth_client,
        user,
    ):
        """
        Fields not included in the PATCH must not be cleared.

        Set phone first, then send a gender-only patch.
        Phone must remain unchanged 
"""