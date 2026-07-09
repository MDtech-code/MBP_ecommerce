from __future__ import annotations
import pytest
from apps.accounts.tests.conftest import (
    STRONG_PASSWORD,
    REGISTER_URL, 

    
)
from apps.accounts.models import (
    EmailVerificationToken,
    User,
    UserProfile,
)


@pytest.fixture
def valid_register_payload() -> dict:
    return {
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }



@pytest.mark.django_db
class TestRegistration:

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_register_success(self, api_client, valid_register_payload):
        """201 returned and user exists in DB."""
        response = api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["success"] is True
        assert User.objects.filter(email="john@example.com").exists()

    def test_register_response_shape(self, api_client, valid_register_payload):
        """
        Response must conform to the standardized envelope.

        Keys: success, message, data, errors, meta.
        data.email must match the registered email.
        """
        response = api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data
        assert data["data"]["email"] == valid_register_payload["email"]

    def test_register_creates_unverified_user(self, api_client, valid_register_payload):
        """New users must not be verified until email confirmation."""
        api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert user.is_verified is False

    def test_register_user_is_active_on_creation(self, api_client, valid_register_payload):
        """Users are active by default — deactivation is done explicitly."""
        api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert user.is_active is True

    def test_register_creates_profile_automatically(self, api_client, valid_register_payload):
        """post_save signal must create UserProfile on user creation."""
        api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert UserProfile.objects.filter(user=user).exists()

    def test_register_creates_verification_token(self, api_client, valid_register_payload):
        """An EmailVerificationToken must exist after registration."""
        api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert EmailVerificationToken.objects.filter(user=user).exists()

    def test_register_password_is_hashed(self, api_client, valid_register_payload):
        """Raw password must never be stored — must survive check_password()."""
        api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert user.password != valid_register_payload["password"]
        assert user.check_password(valid_register_payload["password"])

    def test_register_email_stored_lowercase(self, api_client, valid_register_payload):
        """
        Email normalization must happen at the manager level.

        Even if the user submits mixed-case, DB must store lowercase.
        """
        payload = {**valid_register_payload, "email": "JOHN@EXAMPLE.COM"}
        api_client.post(REGISTER_URL, payload, format="json")
        assert User.objects.filter(email="john@example.com").exists()
        assert not User.objects.filter(email="JOHN@EXAMPLE.COM").exists()

    def test_register_dispatches_verification_task(
        self,
        api_client,
        valid_register_payload,
        mock_verification_task,
    ):
        """
        Celery task must be called once with correct user_id as first arg.

        mock_verification_task is the autouse fixture — requesting it
        explicitly here gives us access to assert on it.
        """
        api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        assert mock_verification_task.called
        assert mock_verification_task.call_count == 1
        user = User.objects.get(email=valid_register_payload["email"])
        call_args = mock_verification_task.call_args[0]
        assert call_args[0] == user.id

    # ── Duplicate Email ───────────────────────────────────────────────────────

    def test_register_duplicate_email_fails(
        self,
        api_client,
        user,
        valid_register_payload,
    ):
        """Existing email must return 400 with success=False."""
        valid_register_payload["email"] = user.email
        response = api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_register_duplicate_email_error_on_correct_field(
        self,
        api_client,
        user,
        valid_register_payload,
    ):
        """Duplicate email error must be on the 'email' field key."""
        valid_register_payload["email"] = user.email
        response = api_client.post(
            REGISTER_URL,
            valid_register_payload,
            format="json",
        )
        assert "email" in response.data["errors"]