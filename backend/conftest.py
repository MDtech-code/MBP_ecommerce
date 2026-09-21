"""Small, shared fixtures. Feature-specific behavior belongs in its own suite."""
import pytest
from django.conf import settings
from django.core.cache import caches
from rest_framework.test import APIClient


@pytest.fixture(autouse=True)
def isolated_caches():
    # Fail closed: the old fixture could flush a developer's configured Redis.
    if not getattr(settings, "TESTING", False):
        pytest.fail("Use config.test_settings; application caches must not be cleared")
    for alias in ("default", "local"):
        if settings.CACHES[alias]["BACKEND"] != "django.core.cache.backends.locmem.LocMemCache":
            pytest.fail("Default suite requires isolated local-memory caches")
        caches[alias].clear()
    yield
    for alias in ("default", "local"):
        caches[alias].clear()


@pytest.fixture
def api_client():
    return APIClient()
