# apps/accounts/tests/conftest.py
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.common.tests.factories import UserFactory

REGISTER_URL = "/api/accounts/register/"


@pytest.fixture
def register_url() -> str:
    return REGISTER_URL


@pytest.fixture
def valid_register_payload() -> dict:
    """
    Fresh valid registration payload.
    Email is unique per test run via Sequence in UserFactory.
    """
    return {
        "email": "newuser@example.com",
        "full_name": "John Doe",
        "password": "StrongPass123!",
        "confirm_password": "StrongPass123!",
    }