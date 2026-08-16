# common/tests/conftest.py
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from .factories import UserFactory





@pytest.fixture
def verified_user(db):
    """Committed, verified User instance."""
    return UserFactory(verified=True)


@pytest.fixture
def unverified_user(db):
    """Committed, unverified User instance."""
    return UserFactory()


@pytest.fixture
def auth_client(db):
    """
    Returns a factory function.
    Usage: auth_client(user) → authenticated APIClient
    """
    def _make(user):
        client = APIClient()
        client.force_authenticate(user=user)
        return client
    return _make