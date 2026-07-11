from __future__ import annotations
from unittest.mock import patch
import pytest
from apps.accounts.tests.conftest import (
   PASSWORD_RESET_URL,
   PASSWORD_RESET_CONFIRM_URL,
   NEW_STRONG_PASSWORD,
   LOGIN_URL,
   STRONG_PASSWORD

    
)
from rest_framework.test import APIClient

from apps.accounts.models import (
    PasswordResetToken
)



@pytest.mark.django_db
@patch("apps.accounts.views.send_password_reset_email_task.delay")
class TestPasswordResetRequest:
    """
    Tests for POST /api/accounts/password-reset/

    Coverage:
        - Happy path (token created, task dispatched)
        - Response shape conformance
        - Unregistered email returns same 200 (enumeration prevention)
        - Inactive user returns same 200
        - Task called with correct args
        - Invalid email format returns 400
        - Missing email returns 400
        - Unregistered and registered return identical message
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_reset_request_returns_200(self, mock_task, api_client, user):
        """Valid registered email must return 200."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_reset_request_response_shape(self, mock_task, api_client, user):
        """Response must conform to standardized envelope."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_reset_request_creates_token(self, mock_task, api_client, user):
        """A PasswordResetToken must exist after a valid request."""
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert PasswordResetToken.objects.filter(user=user).exists()

    def test_reset_request_dispatches_task(self, mock_task, api_client, user):
        """Task must be dispatched exactly once with correct args."""
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert mock_task.called
        assert mock_task.call_count == 1
        assert mock_task.call_args[0][0] == user.id

    def test_reset_request_email_case_insensitive(
        self, mock_task, api_client, user
    ):
        """Email lookup must be case-insensitive."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email.upper()},
            format="json",
        )
        assert response.status_code == 200
        assert mock_task.called

    # ── Enumeration Prevention ────────────────────────────────────────────────

    def test_reset_request_unregistered_email_returns_200(
        self, mock_task, api_client
    ):
        """
        Unregistered email must return same 200 as registered email.
        Different responses would allow email enumeration.
        """
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert response.status_code == 200

    def test_reset_request_unregistered_email_does_not_dispatch_task(
        self, mock_task, api_client
    ):
        """No task must be dispatched for an unregistered email."""
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert not mock_task.called

    def test_reset_request_inactive_user_returns_200(
        self, mock_task, api_client, user
    ):
        """Inactive user must return same 200 — cannot reveal account state."""
        user.is_active = False
        user.save()
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert response.status_code == 200

    def test_reset_request_inactive_user_does_not_dispatch_task(
        self, mock_task, api_client, user
    ):
        """No task must be dispatched for inactive user."""
        user.is_active = False
        user.save()
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert not mock_task.called

    def test_reset_request_all_responses_have_identical_message(
        self, mock_task, api_client, user
    ):
        """
        Registered, unregistered, and inactive responses must be identical.
        Message divergence would enable enumeration.
        """
        registered = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        unregistered = api_client.post(
            PASSWORD_RESET_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert registered.data["message"] == unregistered.data["message"]

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_reset_request_invalid_email_returns_400(
        self, mock_task, api_client
    ):
        """Malformed email must be rejected with 400."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": "not-an-email"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "email" in response.data["errors"]["fields"]

    def test_reset_request_missing_email_returns_400(
        self, mock_task, api_client
    ):
        """Missing email field must return 400."""
        response = api_client.post(PASSWORD_RESET_URL, {}, format="json")
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "email" in response.data["errors"]["fields"]


# ─── Password Reset Confirm Tests ─────────────────────────────────────────────

@pytest.mark.django_db
class TestPasswordResetConfirm:
    """
    Tests for POST /api/accounts/password-reset/confirm/

    Coverage:
        - Happy path (password changed, token marked used)
        - Response shape conformance
        - Token not found returns 400
        - Expired token returns 400
        - Already used token returns 400
        - Mismatched passwords returns 400 on correct field
        - Weak password returns 400
        - Old password no longer works after reset
        - User can login with new password after reset
        - Token is single-use
    """

    def _make_token(self, user) -> PasswordResetToken:
        """Create a fresh password reset token for a user."""
        return PasswordResetToken.create_for_user(user)

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_reset_confirm_returns_200(self, api_client, user):
        """Valid token + valid password must return 200."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_reset_confirm_response_shape(self, api_client, user):
        """Response must conform to standardized envelope."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_reset_confirm_changes_password(self, api_client, user):
        """User password must be updated in DB after reset."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert user.check_password(NEW_STRONG_PASSWORD)

    def test_reset_confirm_old_password_no_longer_works(self, api_client, user):
        """Old password must be invalid after reset."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert not user.check_password(STRONG_PASSWORD)

    def test_reset_confirm_marks_token_as_used(self, api_client, user):
        """Token must be marked as used after successful reset."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        token_obj.refresh_from_db()
        assert token_obj.is_used is True

    def test_reset_confirm_user_can_login_with_new_password(
        self, api_client, user
    ):
        """End-to-end: user must be able to log in with new password."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        login_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": NEW_STRONG_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    # ── Token Not Found ───────────────────────────────────────────────────────

    def test_reset_confirm_invalid_token_returns_400(self, api_client):
        """Non-existent token UUID must return 400."""
        import uuid
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(uuid.uuid4()),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_reset_confirm_invalid_token_format_returns_400(self, api_client):
        """Non-UUID token string must fail serializer validation."""
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": "not-a-uuid",
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "token" in response.data["errors"]["fields"]

    # ── Expired Token ─────────────────────────────────────────────────────────

    def test_reset_confirm_expired_token_returns_400(self, api_client, user):
        """Expired token must return 400 — backdating expires_at field."""
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(user)
        PasswordResetToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=2)
        )
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400

    def test_reset_confirm_expired_token_does_not_change_password(
        self, api_client, user
    ):
        """Expired token must not change the user's password."""
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(user)
        PasswordResetToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=2)
        )
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert not user.check_password(NEW_STRONG_PASSWORD)

    # ── Single Use ────────────────────────────────────────────────────────────

    def test_reset_confirm_token_is_single_use(self, api_client, user):
        """
        Second use of same token must return 400.
        Prevents replay attacks.
        """
        token_obj = self._make_token(user)
        payload = {
            "token": str(token_obj.token),
            "password": NEW_STRONG_PASSWORD,
            "confirm_password": NEW_STRONG_PASSWORD,
        }
        api_client.post(PASSWORD_RESET_CONFIRM_URL, payload, format="json")
        second_response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL, payload, format="json"
        )
        assert second_response.status_code == 400

    # ── Password Validation ───────────────────────────────────────────────────

    def test_reset_confirm_password_mismatch_returns_400(self, api_client, user):
        """Mismatched passwords must return error on confirm_password field."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": "DifferentPass999!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "confirm_password" in response.data["errors"]["fields"]

    def test_reset_confirm_weak_password_returns_400(self, api_client, user):
        """Weak password must be rejected."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": "123",
                "confirm_password": "123",
            },
            format="json",
        )
        assert response.status_code == 400
