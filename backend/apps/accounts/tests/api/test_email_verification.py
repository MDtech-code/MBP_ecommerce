from __future__ import annotations
from unittest.mock import patch
import pytest
from apps.accounts.tests.conftest import (
    VERIFY_EMAIL_URL,
    LOGIN_URL,
    STRONG_PASSWORD

    
)
from rest_framework.test import APIClient

from apps.accounts.models import (
    EmailVerificationToken,
)


@pytest.mark.django_db
@patch("apps.accounts.views.send_welcome_email_task.delay")
class TestEmailVerification:
    """
    Tests for POST /api/accounts/verify-email/

    Coverage:
        - Happy path (user verified, token deleted, welcome email dispatched)
        - Response shape conformance
        - Invalid token format
        - Token not found in DB
        - Expired token
        - Already verified user (idempotent 200)
        - Token is deleted after use (one-time use)
    """

    def _make_token(self, user) -> EmailVerificationToken:
        """Helper — create a fresh verification token for a user."""
        return EmailVerificationToken.create_for_user(user)

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_verify_email_success_returns_200(
        self, mock_welcome, api_client, unverified_user
    ):
        """Valid token must return 200 and mark user as verified."""
        token_obj = self._make_token(unverified_user)
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_verify_email_response_shape(
        self, mock_welcome, api_client, unverified_user
    ):
        """Response must conform to standardized envelope."""
        token_obj = self._make_token(unverified_user)
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_verify_email_marks_user_as_verified(
        self, mock_welcome, api_client, unverified_user
    ):
        """User.is_verified must be True after successful verification."""
        token_obj = self._make_token(unverified_user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        unverified_user.refresh_from_db()
        assert unverified_user.is_verified is True

    def test_verify_email_deletes_token_after_use(
        self, mock_welcome, api_client, unverified_user
    ):
        """Token must be deleted after successful verification — one-time use."""
        token_obj = self._make_token(unverified_user)
        token_id = token_obj.token
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_id)},
            format="json",
        )
        assert not EmailVerificationToken.objects.filter(token=token_id).exists()

    def test_verify_email_dispatches_welcome_email(
        self, mock_welcome, api_client, unverified_user
    ):
        """Welcome email task must be dispatched exactly once."""
        token_obj = self._make_token(unverified_user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert mock_welcome.called
        assert mock_welcome.call_count == 1
        assert mock_welcome.call_args[0][0] == unverified_user.id

    def test_verified_user_can_now_login(
        self, mock_welcome, api_client, unverified_user
    ):
        """
        After verification, user must be able to log in.
        End-to-end confirmation that is_verified gate works.
        """
        token_obj = self._make_token(unverified_user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        login_response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    # ── Token Not Found ───────────────────────────────────────────────────────

    def test_verify_email_invalid_token_returns_400(
        self, mock_welcome, api_client
    ):
        """Non-existent token UUID must return 400."""
        import uuid
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_verify_email_invalid_format_returns_400(
        self, mock_welcome, api_client
    ):
        """Non-UUID string must fail serializer validation with 400."""
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": "not-a-uuid"},
            format="json",
        )
        assert response.status_code == 400
        assert "token" in response.data["errors"]

    def test_verify_email_missing_token_returns_400(
        self, mock_welcome, api_client
    ):
        """Missing token field must return 400."""
        response = api_client.post(VERIFY_EMAIL_URL, {}, format="json")
        assert response.status_code == 400
        assert "token" in response.data["errors"]

    # ── Expired Token ─────────────────────────────────────────────────────────

    def test_verify_email_expired_token_returns_400(
        self, mock_welcome, api_client, unverified_user
    ):
        """
        Expired token must return 400 with descriptive message.
        We backdate the token's created_at to simulate expiry.
        """
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(unverified_user)
        # Backdate beyond expiry window (assume 24h expiry)
        EmailVerificationToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_verify_email_expired_token_does_not_verify_user(
        self, mock_welcome, api_client, unverified_user
    ):
        """Expired token must not change user's verified state."""
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(unverified_user)
        EmailVerificationToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        unverified_user.refresh_from_db()
        assert unverified_user.is_verified is False

    # ── Already Verified ──────────────────────────────────────────────────────

    def test_verify_email_already_verified_returns_200(
        self, mock_welcome, api_client, user
    ):
        """
        Already-verified user must get 200 — idempotent endpoint.
        ``user`` fixture is verified by default.
        """
        import uuid
        # Create a token manually even though user is verified
        # to bypass the DoesNotExist check
        token_obj = EmailVerificationToken.objects.create(
            user=user,
        )
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert response.status_code == 200

    def test_verify_email_already_verified_does_not_dispatch_welcome(
        self, mock_welcome, api_client, user
    ):
        """Welcome email must NOT be sent if user was already verified."""
        token_obj = EmailVerificationToken.objects.create(user=user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert not mock_welcome.called