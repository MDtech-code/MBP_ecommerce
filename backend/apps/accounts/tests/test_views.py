# apps/accounts/tests/test_views.py
from __future__ import annotations

from unittest.mock import patch

import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.core.error_codes import ErrorCode
from apps.common.tests.factories import UserFactory


REGISTER_URL = "/api/accounts/register/"

BASE_PAYLOAD = {
    "email": "newuser@example.com",
    "full_name": "John Doe",
    "password": "StrongPass123!",
    "confirm_password": "StrongPass123!",
}


def _post(client: APIClient, payload: dict):
    return client.post(REGISTER_URL, payload, format="json")


@pytest.mark.django_db
class TestRegisterViewHappyPath:

    def setup_method(self):
        self.client = APIClient()
        self.task_patcher = patch(
            "apps.accounts.services.registration.send_verification_email_task"
        )
        self.task_patcher.start()

    def teardown_method(self):
        self.task_patcher.stop()

    def test_returns_201_on_success(self):
        response = _post(self.client, BASE_PAYLOAD)
        assert response.status_code == status.HTTP_201_CREATED

    def test_response_contains_email(self):
        response = _post(self.client, BASE_PAYLOAD)
        assert response.data["data"]["email"] == "newuser@example.com"

    def test_response_success_true(self):
        response = _post(self.client, BASE_PAYLOAD)
        assert response.data["success"] is True

    def test_response_contains_success_message(self):
        response = _post(self.client, BASE_PAYLOAD)
        assert "verify" in response.data["message"].lower()


@pytest.mark.django_db
class TestRegisterViewValidationErrors:

    def setup_method(self):
        self.client = APIClient()

    def _assert_400(self, payload: dict):
        response = _post(self.client, payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["success"] is False
        return response

    def test_missing_email_returns_400(self):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "email"}
        self._assert_400(payload)

    def test_invalid_email_format_returns_400(self):
        self._assert_400({**BASE_PAYLOAD, "email": "not-an-email"})

    def test_missing_password_returns_400(self):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "password"}
        self._assert_400(payload)

    def test_password_too_short_returns_400(self):
        self._assert_400({
            **BASE_PAYLOAD,
            "password": "Ab1!",
            "confirm_password": "Ab1!",
        })

    def test_passwords_mismatch_returns_400(self):
        self._assert_400({
            **BASE_PAYLOAD,
            "confirm_password": "DifferentPass999!",
        })

    def test_missing_full_name_returns_400(self):
        payload = {k: v for k, v in BASE_PAYLOAD.items() if k != "full_name"}
        self._assert_400(payload)


@pytest.mark.django_db
class TestRegisterViewBusinessErrors:

    def setup_method(self):
        self.client = APIClient()
        self.task_patcher = patch(
            "apps.accounts.services.registration.send_verification_email_task"
        )
        self.task_patcher.start()

    def teardown_method(self):
        self.task_patcher.stop()

    def test_duplicate_email_returns_409(self):
        UserFactory(email="newuser@example.com")
        response = _post(self.client, BASE_PAYLOAD)
        assert response.status_code == status.HTTP_409_CONFLICT

    def test_duplicate_email_returns_correct_error_code(self):
        UserFactory(email="newuser@example.com")
        response = _post(self.client, BASE_PAYLOAD)
        assert (
            response.data["errors"]["non_fields"]["code"]
            == ErrorCode.EMAIL_ALREADY_EXISTS
        )

    def test_duplicate_email_success_false(self):
        UserFactory(email="newuser@example.com")
        response = _post(self.client, BASE_PAYLOAD)
        assert response.data["success"] is False


@pytest.mark.django_db
class TestRegisterViewThrottle:

    def test_throttle_class_configured(self):
        from apps.accounts.views import RegisterView
        from rest_framework.throttling import AnonRateThrottle
        assert AnonRateThrottle in RegisterView.throttle_classes