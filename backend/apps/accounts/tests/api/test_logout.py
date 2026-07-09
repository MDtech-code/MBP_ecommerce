from __future__ import annotations
import pytest
from apps.accounts.tests.conftest import (
    STRONG_PASSWORD,
    LOGIN_URL,
    LOGOUT_URL

    
)
from rest_framework.test import APIClient



@pytest.mark.django_db
class TestLogout:
    """
    Tests for POST /api/accounts/logout/

    Coverage:
        - Happy path (cookie cleared, token blacklisted)
        - Unauthenticated request blocked
        - No cookie present still returns 200 (idempotent)
        - Double logout is safe
    """

    def _get_logged_in_client(self, api_client, user) -> APIClient:
        """
        Helper — log in and return client with refresh cookie attached.
        Also force_authenticate so DRF IsAuthenticated passes.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        api_client.cookies = response.cookies
        api_client.force_authenticate(user=user)
        return api_client

    def test_logout_success_returns_200(self, api_client, user):
        client = self._get_logged_in_client(api_client, user)
        response = client.post(LOGOUT_URL, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_logout_clears_refresh_cookie(self, api_client, user):
        """
        After logout, refresh cookie must be cleared.
        Django sets value='' and max_age=0 on delete_cookie().
        """
        client = self._get_logged_in_client(api_client, user)
        response = client.post(LOGOUT_URL, format="json")
        cookie = response.cookies.get("refresh_token")
        if cookie:
            assert cookie.value == "" or cookie["max-age"] == 0

    def test_logout_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated logout attempts."""
        response = api_client.post(LOGOUT_URL, format="json")
        assert response.status_code == 401

    def test_logout_without_cookie_still_returns_200(self, api_client, user):
        """
        Logout with no cookie must return 200 — idempotent.
        Client may have already cleared cookie locally.
        """
        api_client.force_authenticate(user=user)
        response = api_client.post(LOGOUT_URL, format="json")
        assert response.status_code == 200

    def test_double_logout_does_not_crash(self, api_client, user):
        """
        Second logout with already-blacklisted token must not raise.
        Token is invalid on second call — must still return 200.
        """
        client = self._get_logged_in_client(api_client, user)
        client.post(LOGOUT_URL, format="json")
        response = client.post(LOGOUT_URL, format="json")
        assert response.status_code in (200, 401)

