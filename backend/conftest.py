# backend/conftest.py

from __future__ import annotations


import pytest
from django.core.cache import caches
from rest_framework.test import APIClient




# ─── Sentry — disable during tests ───────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def disable_sentry():
    import sentry_sdk
    sentry_sdk.init()  

# ─── Cache Cleanup ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_all_caches():
    try:
        caches["default"].clear()
    except Exception:
        pass

    try:
        caches["local"].clear()
    except Exception:
        pass

    yield

    try:
        caches["default"].clear()
    except Exception:
        pass

    try:
        caches["local"].clear()
    except Exception:
        pass


# ─── HTTP Client ──────────────────────────────────────────────────────────────

@pytest.fixture
def api_client() -> APIClient:
    return APIClient()