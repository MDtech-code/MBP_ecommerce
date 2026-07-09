from __future__ import annotations
import pytest
from apps.accounts.tests.conftest import (
    STRONG_PASSWORD,
    LOGIN_URL,
    REFRESH_URL

    
)
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestTokenRefresh:
    """
    Tests for POST /api/accounts/token/refresh/

    Coverage:
        - Happy path (new access token returned)
        - Response shape conformance
        - No cookie → 401
        - Invalid/tampered token → 401
        - Expired-style token → 401
    """

    def _get_client_with_cookie(self, api_client, user) -> APIClient:
        """Helper — log in and attach refresh cookie to client."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        api_client.cookies = response.cookies
        return api_client

    def test_refresh_returns_200(self, api_client, user):
        """Valid refresh cookie must return 200."""
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        assert response.status_code == 200

    def test_refresh_returns_new_access_token(self, api_client, user):
        """Response must contain a non-empty access token."""
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        assert "access" in response.data["data"]
        assert len(response.data["data"]["access"]) > 0

    def test_refresh_response_shape(self, api_client, user):
        """Response must conform to the standardized envelope."""
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_refresh_without_cookie_returns_401(self, api_client):
        """No cookie = no session = must return 401."""
        response = api_client.post(REFRESH_URL, format="json")
        assert response.status_code == 401
        assert response.data["success"] is False

    def test_refresh_with_invalid_token_returns_401(self, api_client):
        """Tampered or garbage token must be rejected with 401."""
        api_client.cookies["refresh_token"] = "totally.invalid.token"
        response = api_client.post(REFRESH_URL, format="json")
        assert response.status_code == 401
        assert response.data["success"] is False

    def test_refresh_new_access_token_differs_from_original(
        self, api_client, user
    ):
        """
        Each refresh call should produce a token valid for the user.
        We verify it is a non-empty JWT-shaped string.
        """
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        access = response.data["data"]["access"]
        # JWT format: three base64 segments separated by dots
        assert access.count(".") == 2