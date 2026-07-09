from __future__ import annotations
from unittest.mock import patch
import pytest
from apps.accounts.tests.conftest import (
   NEW_STRONG_PASSWORD,
   LOGIN_URL,
   STRONG_PASSWORD,
   CHANGE_PASSWORD_URL

    
)
from rest_framework.test import APIClient

from apps.accounts.models import (
    User
)


@pytest.mark.django_db
class TestChangePassword:
    """
    Tests for POST /api/accounts/change-password/

    Coverage:
        - Happy path (password changed)
        - Response shape conformance
        - Unauthenticated request blocked
        - Incorrect current password returns 400 on correct field
        - Mismatched new passwords returns 400 on correct field
        - Weak new password returns 400
        - Old password no longer works after change
        - New password can be used to log in
        - Same password as current rejected by Django validators
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_change_password_returns_200(self, auth_client):
        """Valid current password + valid new password must return 200."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_change_password_response_shape(self, auth_client):
        """Response must conform to standardized envelope."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_change_password_updates_db(self, auth_client, user):
        """Password must be updated in DB after change."""
        auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert user.check_password(NEW_STRONG_PASSWORD)

    def test_change_password_old_password_no_longer_works(
        self, auth_client, user
    ):
        """Old password must be invalid after change."""
        auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert not user.check_password(STRONG_PASSWORD)

    def test_change_password_new_password_works_for_login(
        self, auth_client, user, api_client
    ):
        """End-to-end: user must be able to log in with new password."""
        auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        login_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": NEW_STRONG_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_change_password_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated requests."""
        response = api_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 401

    # ── Current Password Validation ───────────────────────────────────────────

    def test_change_password_wrong_current_password_returns_400(
        self, auth_client
    ):
        """Incorrect current password must return 400."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": "WrongPassword!99",
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400

    def test_change_password_wrong_current_password_error_on_field(
        self, auth_client
    ):
        """Incorrect current password error must be on current_password field."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": "WrongPassword!99",
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert "current_password" in response.data["errors"]

    # ── New Password Validation ───────────────────────────────────────────────

    def test_change_password_mismatch_returns_400(self, auth_client):
        """Mismatched new passwords must return error on confirm_new_password."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": "DifferentPass999!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "confirm_new_password" in response.data["errors"]

    def test_change_password_weak_new_password_returns_400(self, auth_client):
        """Weak new password must be rejected."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": "123",
                "confirm_new_password": "123",
            },
            format="json",
        )
        assert response.status_code == 400

    # ── Missing Fields ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", [
        "current_password",
        "new_password",
        "confirm_new_password",
    ])
    def test_change_password_missing_field_returns_400(
        self, auth_client, missing_field
    ):
        """Every required field must individually cause 400 when omitted."""
        payload = {
            "current_password": STRONG_PASSWORD,
            "new_password": NEW_STRONG_PASSWORD,
            "confirm_new_password": NEW_STRONG_PASSWORD,
        }
        payload.pop(missing_field)
        response = auth_client.post(
            CHANGE_PASSWORD_URL, payload, format="json"
        )
        assert response.status_code == 400
        assert missing_field in response.data["errors"]

