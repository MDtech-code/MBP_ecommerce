
from __future__ import annotations
import pytest
from apps.accounts.tests.conftest import (
    STRONG_PASSWORD,
    LOGIN_URL, 

    
)







@pytest.mark.django_db
class TestLogin:
    """
    Tests for POST /api/accounts/login/

    Coverage:
        - Happy path (tokens issued, cookie set)
        - Response shape conformance
        - Refresh token NOT in response body
        - Email case insensitivity
        - Invalid credentials (wrong password, nonexistent email)
        - User enumeration prevention
        - Inactive account blocked
        - Unverified email blocked
        - Already-authenticated user blocked
        - Missing required fields
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_login_success_returns_200(self, api_client, user):
        """Valid credentials must return 200 with success=True."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_login_response_shape(self, api_client, user):
        """Response envelope must contain access token and user data."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data
        assert "access" in data["data"]
        assert "user" in data["data"]

    def test_login_sets_httponly_refresh_cookie(self, api_client, user):
        """
        Refresh token must be delivered via HttpOnly cookie.
        HttpOnly prevents JavaScript access — critical security requirement.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"]["httponly"]

    def test_login_does_not_expose_refresh_token_in_body(self, api_client, user):
        """
        Refresh token must NEVER appear in the response body.
        Body is accessible to JS — only access token goes there.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh" not in response.data["data"]

    def test_login_email_is_case_insensitive(self, api_client, user):
        """Login must succeed regardless of email casing."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email.upper(), "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 200

    # ── Credential Failures ───────────────────────────────────────────────────

    def test_login_wrong_password_returns_400(self, api_client, user):
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_login_nonexistent_email_returns_400(self, api_client):
        response = api_client.post(
            LOGIN_URL,
            {"email": "ghost@example.com", "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_login_invalid_credentials_do_not_reveal_email_existence(
        self, api_client, user
    ):
        """
        Error message must be identical whether email exists or not.
        Different messages would allow user enumeration attacks.
        """
        real_user_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        fake_user_response = api_client.post(
            LOGIN_URL,
            {"email": "ghost@example.com", "password": "WrongPassword!99"},
            format="json",
        )
        assert str(real_user_response.data["errors"]) == str(
            fake_user_response.data["errors"]
        )

    # ── Account State Checks ──────────────────────────────────────────────────

    def test_login_inactive_user_returns_400(self, api_client, user):
        """Deactivated accounts must not receive tokens."""
        user.is_active = False
        user.save()
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_login_unverified_user_returns_400(self, api_client, unverified_user):
        """
        Unverified users must not receive tokens.
        Forces completion of the registration email verification flow.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_login_unverified_user_error_is_non_field(
        self, api_client, unverified_user
    ):
        """Unverified email error must be on non_field_errors key."""
        response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "non_field_errors" in response.data["errors"]

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_authenticated_user_cannot_login(self, auth_client, user):
        """IsNotAuthenticated must block already-authenticated users."""
        response = auth_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 403

    # ── Missing Fields ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", ["email", "password"])
    def test_login_missing_required_field_returns_400(
        self, api_client, user, missing_field
    ):
        """Each required field must individually cause 400 when omitted."""
        payload = {"email": user.email, "password": STRONG_PASSWORD}
        payload.pop(missing_field)
        response = api_client.post(LOGIN_URL, payload, format="json")
        assert response.status_code == 400
        assert missing_field in response.data["errors"]
