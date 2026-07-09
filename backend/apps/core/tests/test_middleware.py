# backend/apps/core/tests/test_middleware.py
"""
Tests for RequestIDMiddleware.

What this middleware does:
    1. Attaches a unique string ID to every request  → request.id
    2. Injects that ID into every response header    → X-Request-ID
    3. BaseAPIView.transform_payload() then puts it  → response.data["meta"]["request_id"]

Why this matters in production:
    When a user reports a bug, they give you their request ID.
    You search logs for that ID and find the exact request/error.
    Without this, debugging production issues is guesswork.

Test strategy:
    Unit tests  → test middleware class directly via RequestFactory
                  no DB, no full Django stack, very fast
    Integration → test that ID flows all the way into response body
                  via our test views defined in conftest.py
"""
from __future__ import annotations

import uuid

import pytest
from django.test import RequestFactory, override_settings
from rest_framework.test import APIClient

from apps.core.middleware import RequestIDMiddleware
from .conftest import test_urlpatterns



# ─── URL override for integration tests ───────────────────────────────────────
# Loaded via override_settings(ROOT_URLCONF=__name__) on each test method.
# Production urls.py is never touched.

urlpatterns = test_urlpatterns


# ─── Unit Tests ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestRequestIDMiddlewareUnit:
    """
    Unit tests for RequestIDMiddleware.

    No database. No Django test client.
    Uses RequestFactory to build raw request objects.
    Fast — runs in milliseconds.
    """

    def _make_middleware(self) -> RequestIDMiddleware:
        """
        Build middleware with a minimal get_response callable.

        get_response is normally the next middleware or the view.
        Here we use a lambda that returns a minimal HttpResponse
        so we can test the middleware in complete isolation.
        """
        from django.http import HttpResponse
        return RequestIDMiddleware(get_response=lambda req: HttpResponse("ok"))

    # ── request.id tests ──────────────────────────────────────────────────────

    def test_request_id_is_attached_to_request(self):
        """
        Middleware must attach an id attribute to the request object.

        Views and BaseAPIView.transform_payload() both read request.id.
        If this attribute is missing, meta.request_id will always be None
        and log correlation will silently fail.
        """
        factory = RequestFactory()
        middleware = self._make_middleware()
        request = factory.get("/test/")

        middleware(request)

        assert hasattr(request, "id"), (
            "request.id not set — middleware did not run or attribute name changed"
        )

    def test_request_id_is_a_string(self):
        """
        request.id must be a string, not a UUID object.

        BaseAPIView puts request.id directly into JSON response.
        UUID objects are not JSON serializable — string is required.
        """
        factory = RequestFactory()
        middleware = self._make_middleware()
        request = factory.get("/test/")

        middleware(request)

        assert isinstance(request.id, str), (
            f"Expected str, got {type(request.id).__name__}"
        )

    def test_request_id_is_valid_uuid_format(self):
        """
        request.id must be a valid UUID string.

        Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        uuid.UUID() raises ValueError if format is wrong.
        """
        factory = RequestFactory()
        middleware = self._make_middleware()
        request = factory.get("/test/")

        middleware(request)

        try:
            uuid.UUID(request.id)
        except ValueError:
            pytest.fail(
                f"request.id is not a valid UUID string: {request.id!r}"
            )

    def test_each_request_gets_unique_id(self):
        """
        Two different requests must never share the same ID.

        If IDs collide, log correlation breaks — you cannot distinguish
        which log lines belong to which request in production.

        We run 50 requests to make accidental collision statistically
        impossible while keeping the test fast.
        """
        factory = RequestFactory()
        middleware = self._make_middleware()

        ids = set()
        for _ in range(50):
            request = factory.get("/test/")
            middleware(request)
            ids.add(request.id)

        assert len(ids) == 50, (
            f"Expected 50 unique IDs, got {len(ids)} — possible UUID collision"
        )

    # ── response header tests ─────────────────────────────────────────────────

    def test_response_contains_x_request_id_header(self):
        """
        Every response must carry X-Request-ID header.

        Clients and API gateways read this header to include
        in bug reports without needing to parse the response body.
        """
        factory = RequestFactory()
        middleware = self._make_middleware()
        request = factory.get("/test/")

        response = middleware(request)

        assert "X-Request-ID" in response, (
            "X-Request-ID header missing from response"
        )

    def test_response_header_matches_request_id(self):
        """
        X-Request-ID header value must match request.id exactly.

        If they differ, client-side correlation and server-side log
        correlation will point to different IDs — useless for debugging.
        """
        factory = RequestFactory()
        middleware = self._make_middleware()
        request = factory.get("/test/")

        response = middleware(request)

        assert response["X-Request-ID"] == request.id

    def test_response_header_is_valid_uuid(self):
        """Header value must itself be a valid UUID string."""
        factory = RequestFactory()
        middleware = self._make_middleware()
        request = factory.get("/test/")

        response = middleware(request)

        try:
            uuid.UUID(response["X-Request-ID"])
        except ValueError:
            pytest.fail(
                f"X-Request-ID header is not valid UUID: "
                f"{response['X-Request-ID']!r}"
            )

    def test_middleware_does_not_modify_response_body(self):
        """
        Middleware must only add a header — never touch response body.

        Modifying response body here would corrupt every API response.
        """
        from django.http import HttpResponse
        original_content = b"original body content"

        middleware = RequestIDMiddleware(
            get_response=lambda req: HttpResponse(original_content)
        )
        factory = RequestFactory()
        request = factory.get("/test/")

        response = middleware(request)

        assert response.content == original_content


# ─── Integration Tests ────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestRequestIDMiddlewareIntegration:
    """
    Integration tests — verify request ID flows through the full stack.

    Why override_settings is on each method, not the class:
        Django's override_settings as a class decorator only works with
        Django's own TestCase subclasses (SimpleTestCase, TestCase).
        Pytest classes are plain Python classes — Django does not recognize
        them, so class-level decoration raises ValueError.
        Method-level override_settings works correctly with pytest classes.

    What we verify that unit tests cannot:
        - Middleware runs inside the full Django request/response cycle
        - request.id reaches BaseAPIView.transform_payload()
        - meta.request_id appears in the actual JSON response body
        - The ID in meta matches the ID in the response header
    """

    @override_settings(ROOT_URLCONF=__name__)
    def test_request_id_appears_in_response_meta(self, api_client):
        """
        meta.request_id must be present in response body.

        Full chain being tested:
            RequestIDMiddleware sets request.id
            → BaseAPIView.transform_payload() reads request.id
            → puts it in payload["meta"]["request_id"]
            → client receives it in response body
        """
        response = api_client.get("/test/public/")

        assert response.status_code == 200
        assert "meta" in response.data
        assert "request_id" in response.data["meta"], (
            "request_id missing from meta — "
            "check BaseAPIView.transform_payload()"
        )

    @override_settings(ROOT_URLCONF=__name__)
    def test_request_id_in_meta_is_valid_uuid(self, api_client):
        """meta.request_id must be a valid UUID string."""
        response = api_client.get("/test/public/")

        request_id = response.data["meta"]["request_id"]
        assert request_id is not None

        try:
            uuid.UUID(str(request_id))
        except ValueError:
            pytest.fail(
                f"meta.request_id is not a valid UUID: {request_id!r}"
            )

    @override_settings(ROOT_URLCONF=__name__)
    def test_meta_request_id_matches_response_header(self, api_client):
        """
        meta.request_id in body must equal X-Request-ID in header.

        If they differ, client has two different IDs and cannot
        know which one to report. Must always be identical.
        """
        response = api_client.get("/test/public/")

        header_id = response.get("X-Request-ID")
        meta_id = response.data["meta"]["request_id"]

        assert header_id is not None, "X-Request-ID header missing"
        assert meta_id is not None, "meta.request_id missing"
        assert header_id == meta_id, (
            f"Header ID {header_id!r} != meta ID {meta_id!r}"
        )

    @override_settings(ROOT_URLCONF=__name__)
    def test_different_requests_get_different_ids(self, api_client):
        """
        Two sequential requests must have different IDs.

        Tests that UUID is generated per-request, not once at startup.
        """
        response1 = api_client.get("/test/public/")
        response2 = api_client.get("/test/public/")

        id1 = response1.data["meta"]["request_id"]
        id2 = response2.data["meta"]["request_id"]

        assert id1 != id2, (
            "Both requests got same ID — "
            "UUID is not being regenerated per request"
        )

    @override_settings(ROOT_URLCONF=__name__)
    def test_request_id_present_on_error_responses(self, api_client):
        """
        request_id must appear in meta even on error responses.

        This is critical — errors are exactly when you need
        log correlation most. If ID is missing on errors,
        debugging production failures becomes very hard.

        Our custom_exception_handler also injects request_id into meta.
        """
        response = api_client.get("/test/unhandled-error/")

        assert response.status_code == 500
        assert "meta" in response.data
        assert response.data["meta"].get("request_id") is not None