from __future__ import annotations
from unittest.mock import patch
import pytest
from apps.accounts.tests.conftest import (
    RESEND_VERIFICATION_URL,
    

    
)
from rest_framework.test import APIClient

from apps.accounts.models import (
    EmailVerificationToken,
)



@pytest.mark.django_db
@patch("apps.accounts.views.send_verification_email_task.delay")
class TestResendVerification:
    """
    Tests for POST /api/accounts/resend-verification/

    Coverage:
        - Happy path (task dispatched for unverified user)
        - Response shape conformance
        - Unregistered email returns same 200 (enumeration prevention)
        - Already verified user returns same 200 (enumeration prevention)
        - Task called with correct args
        - Invalid email format returns 400
        - Missing email returns 400
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_resend_verification_success_returns_200(
        self, mock_task, api_client, unverified_user
    ):
        """Valid unverified email must return 200."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_resend_verification_response_shape(
        self, mock_task, api_client, unverified_user
    ):
        """Response must conform to standardized envelope."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_resend_verification_dispatches_task(
        self, mock_task, api_client, unverified_user
    ):
        """Task must be dispatched exactly once with correct user_id."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        assert mock_task.called
        assert mock_task.call_count == 1
        assert mock_task.call_args[0][0] == unverified_user.id

    def test_resend_verification_creates_new_token(
        self, mock_task, api_client, unverified_user
    ):
        """A new EmailVerificationToken must exist after resend."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        assert EmailVerificationToken.objects.filter(
            user=unverified_user
        ).exists()

    # ── Enumeration Prevention ────────────────────────────────────────────────

    def test_resend_unregistered_email_returns_200(
        self, mock_task, api_client
    ):
        """
        Unregistered email must return the same 200 as a valid request.
        Different responses would allow email enumeration.
        """
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert response.status_code == 200

    def test_resend_unregistered_email_does_not_dispatch_task(
        self, mock_task, api_client
    ):
        """No task must be dispatched for an unregistered email."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert not mock_task.called

    def test_resend_already_verified_user_returns_200(
        self, mock_task, api_client, user
    ):
        """
        Already verified user must return same 200.
        Cannot reveal verification state to caller.
        """
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": user.email},
            format="json",
        )
        assert response.status_code == 200

    def test_resend_already_verified_user_does_not_dispatch_task(
        self, mock_task, api_client, user
    ):
        """Task must not be dispatched if user is already verified."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": user.email},
            format="json",
        )
        assert not mock_task.called

    def test_resend_unregistered_and_verified_return_same_message(
        self, mock_task, api_client, user
    ):
        """
        All non-error responses must have identical message text.
        Message divergence would enable enumeration.
        """
        unregistered = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        already_verified = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": user.email},
            format="json",
        )
        assert unregistered.data["message"] == already_verified.data["message"]

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_resend_invalid_email_format_returns_400(
        self, mock_task, api_client
    ):
        """Malformed email must be rejected with 400."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "not-an-email"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "email" in response.data["errors"]["fields"]

    def test_resend_missing_email_returns_400(self, mock_task, api_client):
        """Missing email field must return 400."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert "email" in response.data["errors"]["fields"]