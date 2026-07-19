# apps/accounts/tests/test_tasks.py
from __future__ import annotations

from unittest.mock import patch

import pytest
from celery.exceptions import MaxRetriesExceededError

from apps.accounts.tasks import send_verification_email_task
from apps.common.tests.factories import UserFactory


MOCK_TOKEN    = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
MOCK_FRONTEND = "https://example.com"
MOCK_FROM     = "no-reply@example.com"


@pytest.mark.django_db
class TestSendVerificationEmailTask:

    # ── Happy path ─────────────────────────────────────────────────────────────

    @patch("apps.accounts.tasks.send_mail")
    @patch("apps.accounts.tasks.settings")
    def test_send_mail_called_with_correct_recipient(
        self, mock_settings, mock_send_mail
    ):
        mock_settings.FRONTEND_URL       = MOCK_FRONTEND
        mock_settings.DEFAULT_FROM_EMAIL = MOCK_FROM

        user = UserFactory()
        send_verification_email_task(user.id, MOCK_TOKEN)

        mock_send_mail.assert_called_once()
        kwargs = mock_send_mail.call_args.kwargs
        assert kwargs["recipient_list"] == [user.email]

    @patch("apps.accounts.tasks.send_mail")
    @patch("apps.accounts.tasks.settings")
    def test_send_mail_called_with_token_url_in_body(
        self, mock_settings, mock_send_mail
    ):
        mock_settings.FRONTEND_URL       = MOCK_FRONTEND
        mock_settings.DEFAULT_FROM_EMAIL = MOCK_FROM

        user = UserFactory()
        send_verification_email_task(user.id, MOCK_TOKEN)

        kwargs = mock_send_mail.call_args.kwargs
        assert MOCK_TOKEN in kwargs["message"]

    @patch("apps.accounts.tasks.send_mail")
    @patch("apps.accounts.tasks.settings")
    def test_send_mail_called_with_correct_subject(
        self, mock_settings, mock_send_mail
    ):
        mock_settings.FRONTEND_URL       = MOCK_FRONTEND
        mock_settings.DEFAULT_FROM_EMAIL = MOCK_FROM

        user = UserFactory()
        send_verification_email_task(user.id, MOCK_TOKEN)

        kwargs  = mock_send_mail.call_args.kwargs
        subject = kwargs["subject"].lower()
        assert "verify" in subject or "email" in subject

    # ── Edge case: user not found ──────────────────────────────────────────────

    @patch("apps.accounts.tasks.send_mail")
    def test_user_not_found_returns_early_no_send_mail(self, mock_send_mail):
        """
        Non-existent user_id → task returns silently.
        No retry. No send_mail call. No crash.
        """
        send_verification_email_task(999999, MOCK_TOKEN)
        mock_send_mail.assert_not_called()

    # ── Edge case: send_mail failure → retries → exhausted ────────────────────

    @patch("apps.accounts.tasks.send_mail")
    @patch("apps.accounts.tasks.settings")
    def test_send_mail_failure_exhausts_retries(
        self, mock_settings, mock_send_mail
    ):
        """
        What we are actually testing:
            send_mail always fails
            Celery retries 3 times (max_retries=3)
            After all retries exhausted → raises original Exception

        Why NOT testing for Retry exception:
            Retry is Celery internal re-execution signal
            Celery catches it and re-runs the task itself
            It never reaches the test caller
            What reaches the caller is the original exception
            after max retries are exhausted

        Why NOT testing for MaxRetriesExceededError:
            .apply() in ALWAYS_EAGER mode raises the original
            exception (SMTP failure) not MaxRetriesExceededError
            MaxRetriesExceededError only surfaces in non-eager mode
        """
        mock_settings.FRONTEND_URL       = MOCK_FRONTEND
        mock_settings.DEFAULT_FROM_EMAIL = MOCK_FROM
        mock_send_mail.side_effect       = Exception("SMTP failure")

        user = UserFactory()

        with pytest.raises(Exception, match="SMTP failure"):
            send_verification_email_task.apply(
                args=[user.id, MOCK_TOKEN]
            ).get()

    @patch("apps.accounts.tasks.send_mail")
    @patch("apps.accounts.tasks.settings")
    def test_send_mail_attempted_correct_number_of_times(
        self, mock_settings, mock_send_mail
    ):
        """
        max_retries=3 → send_mail called 4 times total.
        1 original attempt + 3 retries = 4 calls.
        This confirms retry logic is wired correctly.
        """
        mock_settings.FRONTEND_URL       = MOCK_FRONTEND
        mock_settings.DEFAULT_FROM_EMAIL = MOCK_FROM
        mock_send_mail.side_effect       = Exception("SMTP failure")

        user = UserFactory()

        with pytest.raises(Exception):
            send_verification_email_task.apply(
                args=[user.id, MOCK_TOKEN]
            ).get()

        # 1 original + 3 retries = 4 total attempts
        assert mock_send_mail.call_count == 4