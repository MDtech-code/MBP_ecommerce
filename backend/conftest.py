# backend/conftest.py
"""
Global test configuration.

This file is loaded by pytest automatically before any test runs.
Fixtures defined here are available to EVERY test in the backend
without any import.

Rules for what belongs here:
    ✓ Fixtures every app needs (api_client, cache clearing)
    ✓ Global pytest configuration hooks
    ✗ App-specific fixtures (those go in apps/*/tests/conftest.py)
    ✗ Model imports (models may not be ready at global conftest load time)
"""
from __future__ import annotations

import django
import pytest
from django.core.cache import caches
from rest_framework.test import APIClient




# ─── Sentry — disable during tests ───────────────────────────────────────────

@pytest.fixture(autouse=True, scope="session")
def disable_sentry():
    """
    Disable Sentry event sending during the entire test session.

    Why:
        Tests deliberately raise exceptions (unhandled error views,
        permission denied tests etc). Without this, Sentry captures
        every deliberate test exception and sends it to your dashboard,
        polluting your real error monitoring with test noise.

        Also adds 2 second delay at end of test run while Sentry
        flushes its queue — multiplied across many test runs this wastes
        significant developer time.

    Why scope="session":
        Sentry is initialized once at Django startup.
        Re-disabling it per test is wasteful.
        Session scope disables it once for the entire pytest run.
    """
    import sentry_sdk
    sentry_sdk.init()  # reinitialize with empty DSN = effectively disabled

# ─── Cache Cleanup ────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_all_caches():
    """
    Clear both cache levels before and after EVERY test globally.

    Why autouse=True at global level:
        Cache pollution is a global concern, not an app concern.
        A throttle test in core could poison a login test in accounts
        if L1 LocMemCache is not reset between tests.

        L1 (LocMemCache) — cleared directly, no external dependency.
        L2 (Redis)        — cleared via Django cache API.
                            If Redis is down in CI, this fails silently
                            via the except block — tests still run.

    Why clear BEFORE yield AND after yield:
        Before → guarantees clean state even if previous test
                 crashed before its own cleanup ran.
        After  → leaves environment clean for next test.
    """
    try:
        caches["default"].clear()
    except Exception:
        # Redis may not be available in all CI environments.
        # Tests that need Redis will fail on their own terms.
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
    """
    Unauthenticated DRF test client.

    Why this lives at global level:
        Every app (accounts, products, cart, orders) needs an HTTP client.
        Defining it once here means zero duplication across app conftest files.

    Why a fresh instance per test (not session-scoped):
        APIClient holds state — cookies, auth headers, forced users.
        A session-scoped client would leak auth state between tests,
        causing intermittent failures that are very hard to debug.

    Usage:
        def test_something(self, api_client):
            response = api_client.get("/api/some-endpoint/")
    """
    return APIClient()