# backend/apps/accounts/tests/api/test_addresses.py
"""
Address endpoint tests.

Endpoints:
    GET    /api/accounts/addresses/              — list addresses
    POST   /api/accounts/addresses/              — create address
    PUT    /api/accounts/addresses/<pk>/         — update address
    DELETE /api/accounts/addresses/<pk>/         — delete address
    PATCH  /api/accounts/addresses/<pk>/set-default/ — set default

Views:
    AddressListCreateView
    AddressDetailView
    AddressSetDefaultView

Covers:
    - Authentication enforcement (all endpoints require IsAuthenticated)
    - List: empty list, populated list, ownership isolation
    - Create: happy path, auto-derived fields, validation failures
    - Update: partial update, ownership enforcement, not-found
    - Delete: success, ownership enforcement, not-found
    - Set-default: success, replaces previous default, not-found
    - Response envelope shape on every endpoint
"""
from __future__ import annotations

import pytest

from apps.accounts.models import UserAddress
from apps.accounts.tests.conftest import (
    ADDRESS_DETAIL_URL,
    ADDRESS_LIST_CREATE_URL,
    ADDRESS_SET_DEFAULT_URL,
    STRONG_PASSWORD,
    VALID_CITY_ISLAMABAD,
    VALID_CITY_KARACHI,
    VALID_CITY_LAHORE,
    valid_address_payload,
    user_address,
    default_address
)


# ─── URL helpers ──────────────────────────────────────────────────────────────
# ADDRESS_DETAIL_URL and ADDRESS_SET_DEFAULT_URL contain {pk} placeholder.
# These helpers resolve them so tests stay readable.

def detail_url(pk: int) -> str:
    """Resolve /api/accounts/addresses/{pk}/"""
    return ADDRESS_DETAIL_URL.format(pk=pk)


def set_default_url(pk: int) -> str:
    """Resolve /api/accounts/addresses/{pk}/set-default/"""
    return ADDRESS_SET_DEFAULT_URL.format(pk=pk)


# ─── Shared payload helper ────────────────────────────────────────────────────



# ─── Shared payload helper ────────────────────────────────────────────────────

def make_address_payload(
    city: str = VALID_CITY_LAHORE,
    label: str = "home",
    address_line1: str = "123 Main Street",
    address_line2: str = "Near Clock Tower",
) -> dict:
    """
    Build a valid address creation payload.

    province, postal_code, country are intentionally excluded —
    they are auto-derived from city on model save().
    """
    return {
        "label": label,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "city": city,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# LIST ADDRESSES  —  GET /api/accounts/addresses/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddressListAuthentication:
    """Authentication gate — all verifications before any data tests."""

    def test_unauthenticated_returns_401(self, api_client):
        """
        Unauthenticated request to list endpoint must return 401.

        IsAuthenticated permission is the first gate.
        No data should be visible without a valid token.
        """
        response = api_client.get(ADDRESS_LIST_CREATE_URL)
        assert response.status_code == 401

    def test_authenticated_returns_200(self, auth_client):
        """Authenticated request to list endpoint returns 200."""
        response = auth_client.get(ADDRESS_LIST_CREATE_URL)
        assert response.status_code == 200
        assert response.data["success"] is True


@pytest.mark.django_db
class TestAddressListData:
    """Data correctness tests for the list endpoint."""

    def test_empty_list_returns_empty_array(self, auth_client):
        """
        User with no addresses must receive an empty list — not 404.

        Why: empty state is valid, not an error. Frontend renders
        'no addresses yet' UI based on empty array, not error state.
        """
        response = auth_client.get(ADDRESS_LIST_CREATE_URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_returns_all_user_addresses(
        self,
        auth_client,
        user,
    ):
        """
        All addresses belonging to the user must be returned.
        Count must match exactly.
        """
        UserAddress.objects.create(
            user=user,
            label="home",
            address_line1="10 First Street",
            city=VALID_CITY_LAHORE,
        )
        UserAddress.objects.create(
            user=user,
            label="work",
            address_line1="20 Second Street",
            city=VALID_CITY_KARACHI,
        )

        response = auth_client.get(ADDRESS_LIST_CREATE_URL)
        assert response.status_code == 200
        assert len(response.data["data"]) == 2

    def test_does_not_return_other_users_addresses(
        self,
        auth_client,
        db,
    ):
        """
        Addresses belonging to other users must NEVER appear in response.

        Ownership isolation is critical — users must never see
        each other's shipping addresses.
        """
        from apps.accounts.models import User

        # Create a second user with their own address
        other_user = User.objects.create_user(
            email="other@test.com",
            full_name="Other User",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        UserAddress.objects.create(
            user=other_user,
            label="home",
            address_line1="99 Private Street",
            city=VALID_CITY_ISLAMABAD,
        )

        # auth_client is authenticated as `user` — must not see other_user's address
        response = auth_client.get(ADDRESS_LIST_CREATE_URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_list_response_envelope_shape(self, auth_client, user_address):
        """
        List response must conform to standard envelope.
        data must be a list.
        """
        response = auth_client.get(ADDRESS_LIST_CREATE_URL)
        data = response.data

        assert "success" in data
        assert "message" in data
        assert "data" in data
        assert "errors" in data
        assert "meta" in data
        assert isinstance(data["data"], list)

    def test_address_fields_in_response(self, auth_client, user_address):
        """
        Each address in the list must include all expected serializer fields.

        Catches field additions/removals in UserAddressSerializer.Meta.fields.
        """
        response = auth_client.get(ADDRESS_LIST_CREATE_URL)
        assert response.status_code == 200

        address_data = response.data["data"][0]

        expected_fields = [
            "id",
            "label",
            "label_display",
            "address_line1",
            "address_line2",
            "city",
            "province",
            "province_display",
            "postal_code",
            "country",
            "is_default",
            "full_address",
            "created_at",
            "updated_at",
        ]
        for field in expected_fields:
            assert field in address_data, (
                f"Expected field '{field}' missing from address response"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# CREATE ADDRESS  —  POST /api/accounts/addresses/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddressCreateAuthentication:

    def test_unauthenticated_cannot_create(
        self,
        api_client,
        valid_address_payload,
    ):
        """Unauthenticated POST to create endpoint must return 401."""
        response = api_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestAddressCreateHappyPath:

    def test_create_returns_201(self, auth_client, valid_address_payload):
        """Successful address creation must return 201."""
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["success"] is True

    def test_create_persists_address_in_db(
        self,
        auth_client,
        user,
        valid_address_payload,
    ):
        """Address must exist in DB after successful creation."""
        auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert UserAddress.objects.filter(
            user=user,
            address_line1=valid_address_payload["address_line1"],
        ).exists()

    def test_create_assigns_address_to_authenticated_user(
        self,
        auth_client,
        user,
        valid_address_payload,
    ):
        """
        Created address must belong to the authenticated user.

        The view calls serializer.save(user=request.user) —
        this test confirms user assignment is not bypassed.
        """
        auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        address = UserAddress.objects.get(
            address_line1=valid_address_payload["address_line1"]
        )
        assert address.user == user

    def test_create_auto_derives_province_from_city(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        Province must be auto-derived from city on model save().

        Lahore → Punjab (PB).
        Client never sends province — it is computed server-side.
        """
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert response.status_code == 201
        # Lahore → PB (Punjab)
        assert response.data["data"]["province"] == "PB"

    def test_create_auto_derives_postal_code_from_city(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        Postal code must be auto-derived from city on model save().

        Lahore → 54000.
        """
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["data"]["postal_code"] == "54000"

    def test_create_auto_derives_country(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        Country must be set to Pakistan automatically.
        Client never sends country — always Pakistan for this platform.
        """
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["data"]["country"] == "Pakistan"

    def test_create_returns_id_in_response(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        Response must include address ID.
        Frontend needs this for subsequent update/delete/set-default calls.
        """
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            valid_address_payload,
            format="json",
        )
        assert response.status_code == 201
        assert "id" in response.data["data"]
        assert response.data["data"]["id"] is not None

    def test_create_different_cities_derive_correctly(
        self,
        auth_client,
        user,
    ):
        """
        Auto-derivation must work for multiple cities — not just Lahore.

        Karachi → SD (Sindh), 75000.
        Islamabad → IC (Islamabad Capital Territory), 44000.
        """
        # Karachi
        response_karachi = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            make_address_payload(city=VALID_CITY_KARACHI, label="office"),
            format="json",
        )
        assert response_karachi.status_code == 201
        assert response_karachi.data["data"]["province"] == "SD"
        assert response_karachi.data["data"]["postal_code"] == "75000"

        # Islamabad
        response_islamabad = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            make_address_payload(city=VALID_CITY_ISLAMABAD, label="other"),
            format="json",
        )
        assert response_islamabad.status_code == 201
        assert response_islamabad.data["data"]["province"] == "IC"
        assert response_islamabad.data["data"]["postal_code"] == "44000"


@pytest.mark.django_db
class TestAddressCreateValidationFailures:

    def test_missing_city_returns_400(self, auth_client):
        """City is required — missing city must return 400."""
        payload = {
            "label": "home",
            "address_line1": "123 Main Street",
            # city intentionally omitted
        }
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            payload,
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_missing_address_line1_returns_400(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        address_line1 is required.
        validate_address_line1 raises if blank or missing.
        """
        payload = {**valid_address_payload}
        payload.pop("address_line1")

        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            payload,
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "address_line1" in response.data["errors"]["fields"]

    def test_blank_address_line1_returns_400(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        Whitespace-only address_line1 must be caught by validate_address_line1.
        The validator strips and checks — empty string after strip fails.
        """
        payload = {**valid_address_payload, "address_line1": "   "}

        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            payload,
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "address_line1" in response.data["errors"]["fields"]

    def test_invalid_city_returns_400(
        self,
        auth_client,
        valid_address_payload,
    ):
        """
        City must be a valid choice from City choices enum.
        An unrecognized city must be rejected.
        """
        payload = {**valid_address_payload, "city": "Atlantis"}

        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            payload,
            format="json",
        )
        assert response.status_code == 400

    def test_empty_payload_returns_400(self, auth_client):
        """Completely empty payload must be rejected with 400."""
        response = auth_client.post(
            ADDRESS_LIST_CREATE_URL,
            {},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# UPDATE ADDRESS  —  PUT /api/accounts/addresses/<pk>/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddressUpdateAuthentication:

    def test_unauthenticated_cannot_update(self, api_client, user_address):
        """Unauthenticated PUT must return 401."""
        response = api_client.put(
            detail_url(user_address.pk),
            {"address_line1": "New Street"},
            format="json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestAddressUpdateHappyPath:

    def test_update_returns_200(self, auth_client, user_address):
        """Successful update must return 200."""
        response = auth_client.put(
            detail_url(user_address.pk),
            {"address_line1": "Updated Street 99"},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_update_persists_changes_in_db(
        self,
        auth_client,
        user_address,
    ):
        """
        Updated fields must be persisted.
        Re-fetch from DB to confirm — do not trust the response alone.
        """
        auth_client.put(
            detail_url(user_address.pk),
            {"address_line1": "Verified Persistence Street"},
            format="json",
        )
        user_address.refresh_from_db()
        assert user_address.address_line1 == "Verified Persistence Street"

    def test_update_is_partial(self, auth_client, user_address):
        """
        PUT is implemented as partial=True in the view.
        Sending only one field must not clear other fields.

        Why partial update on PUT:
            All profile fields are optional on update.
            The view uses partial=True even for PUT requests.
        """
        original_city = user_address.city

        auth_client.put(
            detail_url(user_address.pk),
            {"address_line1": "New Line Only"},
            format="json",
        )
        user_address.refresh_from_db()

        # address_line1 updated
        assert user_address.address_line1 == "New Line Only"
        # city unchanged
        assert user_address.city == original_city

    def test_update_city_re_derives_province(
        self,
        auth_client,
        user_address,
    ):
        """
        Changing city on update must re-derive province, postal_code.

        user_address starts as Lahore (PB, 54000).
        After update to Karachi → SD, 75000.
        """
        response = auth_client.put(
            detail_url(user_address.pk),
            {"city": VALID_CITY_KARACHI},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["data"]["province"] == "SD"
        assert response.data["data"]["postal_code"] == "75000"

    def test_update_response_contains_updated_data(
        self,
        auth_client,
        user_address,
    ):
        """
        Response data must reflect the updated values, not stale data.
        """
        response = auth_client.put(
            detail_url(user_address.pk),
            {"address_line1": "Fresh Response Street"},
            format="json",
        )
        assert response.data["data"]["address_line1"] == "Fresh Response Street"


@pytest.mark.django_db
class TestAddressUpdateOwnership:

    def test_cannot_update_other_users_address(self, auth_client, db):
        """
        User must not be able to update addresses they do not own.
        Returns 404 — ownership check treats it as not-found.

        Why 404 not 403:
            Revealing that the address EXISTS but belongs to someone
            else is an information leak. 404 is the safe response.
        """
        from apps.accounts.models import User

        other_user = User.objects.create_user(
            email="other2@test.com",
            full_name="Other User Two",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        other_address = UserAddress.objects.create(
            user=other_user,
            label="home",
            address_line1="Someone Else Street",
            city=VALID_CITY_LAHORE,
        )

        response = auth_client.put(
            detail_url(other_address.pk),
            {"address_line1": "Hacked Street"},
            format="json",
        )
        assert response.status_code == 404

    def test_update_nonexistent_address_returns_404(
        self,
        auth_client,
    ):
        """Non-existent PK must return 404."""
        response = auth_client.put(
            detail_url(99999),
            {"address_line1": "Ghost Street"},
            format="json",
        )
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# DELETE ADDRESS  —  DELETE /api/accounts/addresses/<pk>/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddressDeleteAuthentication:

    def test_unauthenticated_cannot_delete(self, api_client, user_address):
        """Unauthenticated DELETE must return 401."""
        response = api_client.delete(detail_url(user_address.pk))
        assert response.status_code == 401


@pytest.mark.django_db
class TestAddressDeleteHappyPath:

    def test_delete_returns_200(self, auth_client, user_address):
        """Successful delete must return 200."""
        response = auth_client.delete(detail_url(user_address.pk))
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_delete_removes_address_from_db(
        self,
        auth_client,
        user_address,
    ):
        """
        Address must not exist in DB after deletion.
        Re-query DB to confirm — do not trust response alone.
        """
        pk = user_address.pk
        auth_client.delete(detail_url(pk))
        assert not UserAddress.objects.filter(pk=pk).exists()

    def test_delete_only_removes_target_address(
        self,
        auth_client,
        user,
        user_address,
    ):
        """
        Only the specified address must be deleted.
        Other addresses belonging to the same user must remain.
        """
        other_address = UserAddress.objects.create(
            user=user,
            label="work",
            address_line1="456 Work Street",
            city=VALID_CITY_KARACHI,
        )

        auth_client.delete(detail_url(user_address.pk))

        # Deleted address gone
        assert not UserAddress.objects.filter(pk=user_address.pk).exists()
        # Other address untouched
        assert UserAddress.objects.filter(pk=other_address.pk).exists()


@pytest.mark.django_db
class TestAddressDeleteOwnership:

    def test_cannot_delete_other_users_address(self, auth_client, db):
        """
        User must not be able to delete addresses they do not own.
        Returns 404 — same ownership-as-not-found pattern as update.
        """
        from apps.accounts.models import User

        other_user = User.objects.create_user(
            email="other3@test.com",
            full_name="Other User Three",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        other_address = UserAddress.objects.create(
            user=other_user,
            label="home",
            address_line1="Protected Street",
            city=VALID_CITY_LAHORE,
        )

        response = auth_client.delete(detail_url(other_address.pk))
        assert response.status_code == 404

        # Confirm address was NOT deleted
        assert UserAddress.objects.filter(pk=other_address.pk).exists()

    def test_delete_nonexistent_returns_404(self, auth_client):
        """Non-existent PK on delete must return 404."""
        response = auth_client.delete(detail_url(99999))
        assert response.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# SET DEFAULT  —  PATCH /api/accounts/addresses/<pk>/set-default/
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAddressSetDefaultAuthentication:

    def test_unauthenticated_cannot_set_default(
        self,
        api_client,
        user_address,
    ):
        """Unauthenticated PATCH to set-default must return 401."""
        response = api_client.patch(set_default_url(user_address.pk))
        assert response.status_code == 401


@pytest.mark.django_db
class TestAddressSetDefaultHappyPath:

    def test_set_default_returns_200(self, auth_client, user_address):
        """Successful set-default must return 200."""
        response = auth_client.patch(set_default_url(user_address.pk))
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_set_default_marks_address_as_default_in_db(
        self,
        auth_client,
        user_address,
    ):
        """
        is_default must be True in DB after set-default call.
        Re-fetch to confirm persistence.
        """
        auth_client.patch(set_default_url(user_address.pk))
        user_address.refresh_from_db()
        assert user_address.is_default is True

    def test_set_default_clears_previous_default(
        self,
        auth_client,
        user,
        default_address,
    ):
        """
        Setting a new default must unset the previous default.

        Only one address can be default at a time.
        This tests the set_as_default() model method's atomicity.

        default_address fixture creates an address with is_default=True.
        We create a second address and set IT as default.
        The original default_address must then have is_default=False.
        """
        # Create second address (not default yet)
        second_address = UserAddress.objects.create(
            user=user,
            label="work",
            address_line1="789 Work Avenue",
            city=VALID_CITY_KARACHI,
            is_default=False,
        )

        # Set second address as default
        response = auth_client.patch(set_default_url(second_address.pk))
        assert response.status_code == 200

        # Second address is now default
        second_address.refresh_from_db()
        assert second_address.is_default is True

        # Original default is no longer default
        default_address.refresh_from_db()
        assert default_address.is_default is False

    def test_only_one_default_exists_after_set_default(
        self,
        auth_client,
        user,
        default_address,
    ):
        """
        After set-default, exactly one address must have is_default=True.

        Guards against a race condition or broken set_as_default()
        that leaves multiple defaults active simultaneously.
        """
        second_address = UserAddress.objects.create(
            user=user,
            label="work",
            address_line1="100 New Default Road",
            city=VALID_CITY_ISLAMABAD,
            is_default=False,
        )

        auth_client.patch(set_default_url(second_address.pk))

        default_count = UserAddress.objects.filter(
            user=user,
            is_default=True,
        ).count()
        assert default_count == 1

    def test_set_default_response_contains_address_data(
        self,
        auth_client,
        user_address,
    ):
        """
        Response data must include the updated address.
        is_default must be True in the response.
        """
        response = auth_client.patch(set_default_url(user_address.pk))
        assert response.status_code == 200
        assert response.data["data"]["is_default"] is True
        assert response.data["data"]["id"] == user_address.pk

    def test_set_default_idempotent(
        self,
        auth_client,
        default_address,
    ):
        """
        Setting an already-default address as default again must succeed.
        is_default must remain True. No error should be raised.

        Why test idempotency:
            Frontend may call this on page refresh without checking
            current state. The endpoint must handle this gracefully.
        """
        response = auth_client.patch(set_default_url(default_address.pk))
        assert response.status_code == 200

        default_address.refresh_from_db()
        assert default_address.is_default is True


@pytest.mark.django_db
class TestAddressSetDefaultOwnership:

    def test_cannot_set_default_on_other_users_address(
        self,
        auth_client,
        db,
    ):
        """
        User must not be able to set-default on addresses they don't own.
        Must return 404.
        """
        from apps.accounts.models import User

        other_user = User.objects.create_user(
            email="other4@test.com",
            full_name="Other User Four",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        other_address = UserAddress.objects.create(
            user=other_user,
            label="home",
            address_line1="Private Default Street",
            city=VALID_CITY_LAHORE,
        )

        response = auth_client.patch(set_default_url(other_address.pk))
        assert response.status_code == 404

    def test_set_default_nonexistent_returns_404(self, auth_client):
        """Non-existent PK on set-default must return 404."""
        response = auth_client.patch(set_default_url(99999))
        assert response.status_code == 404

