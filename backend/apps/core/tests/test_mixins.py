# backend/apps/core/tests/test_mixins.py
"""
Tests for APIResponseMixin and BaseAPIView response infrastructure.

These two classes are the foundation of EVERY response in the backend.
Every endpoint in accounts, products, cart, orders inherits BaseAPIView.
If build_response() breaks, every single endpoint returns wrong data.

Test structure:

    Layer 1 — APIResponseMixin directly
        Tested via a minimal concrete subclass.
        Verifies the mixin works correctly in isolation
        before BaseAPIView adds its own behavior on top.

    Layer 2 — BaseAPIView response helpers
        Tests each helper method (success_response, created_response etc).
        Verifies correct status codes, default messages, envelope shape.

    Layer 3 — BaseAPIView.transform_payload() + request_id injection
        Verifies request_id flows into meta when request.id is present.
        Verifies graceful no-op when request.id is absent.

    Layer 4 — HTTP integration
        Full stack via test views — proves everything works
        end-to-end in a real request/response cycle.

Why we test both mixin and view separately:
    If a test fails, you know immediately whether the bug is in
    the mixin (build_response logic) or the view (helper methods).
    Without separation, debugging requires reading both files.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest
from django.test import override_settings
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.test import APIRequestFactory

from apps.core.api.mixins import APIResponseMixin
from apps.core.api.views import BaseAPIView
from  apps.core.tests.urls import test_urlpatterns
from apps.core.error_codes import ErrorCode

# ─── URL override for integration tests ───────────────────────────────────────

urlpatterns = test_urlpatterns


# ─── Minimal concrete classes for isolated testing ────────────────────────────

class ConcreteMixin(APIResponseMixin):
    """
    Minimal concrete subclass of APIResponseMixin.

    APIResponseMixin cannot be instantiated directly because
    transform_payload() references self which needs to exist.
    This subclass adds nothing — it just makes the mixin instantiable.

    Why not use BaseAPIView here:
        We want to test the MIXIN in isolation.
        BaseAPIView overrides transform_payload() — using it would
        mix mixin behavior with view behavior in the same test.
    """
    pass


class ConcreteView(BaseAPIView):
    """
    Minimal concrete BaseAPIView for testing all response helpers.

    GenericAPIView requires either queryset or get_queryset() for
    some operations — response helpers need neither, so bare subclass works.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return self.success_response(
            data={"key": "value"},
            message="Test success",
        )


# ─── Helper ───────────────────────────────────────────────────────────────────

def _make_view_with_request(view_class=ConcreteView, path: str = "/test/"):
    """
    Instantiate a view and attach a properly initialized DRF request.

    Why this setup is needed:
        BaseAPIView inherits GenericAPIView which stores the request
        on self.request after initialize_request().
        Without this, any helper that calls self.request raises AttributeError.
        transform_payload() calls getattr(self.request, 'id', None) —
        so self.request must exist even in unit tests.

    Returns:
        view instance with self.request properly set
    """
    factory = APIRequestFactory()
    raw_request = factory.get(path)
    view = view_class()
    view.request = view.initialize_request(raw_request)
    view.kwargs = {}
    view.format_kwarg = None
    return view


# ─── Layer 1: APIResponseMixin Unit Tests ─────────────────────────────────────

@pytest.mark.unit
class TestAPIResponseMixin:
    """
    Unit tests for APIResponseMixin.build_response().

    Tested via ConcreteMixin which adds no behavior.
    This isolates the mixin completely from BaseAPIView.
    """

    def _mixin(self) -> ConcreteMixin:
        return ConcreteMixin()

    # ── Envelope structure ────────────────────────────────────────────────────

    def test_build_response_contains_all_five_keys(self):
        """
        Every response must contain exactly these five keys.

        Frontend contracts depend on this shape being consistent.
        Adding or removing keys here breaks every frontend consumer.

        Keys: success, message, data, errors, meta
        """
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)

        for key in ("success", "message", "data", "errors", "meta"):
            assert key in response.data, (
                f"Envelope missing required key: '{key}'"
            )

    def test_build_response_has_exactly_five_keys(self):
        """
        Response must have EXACTLY five keys — no more, no less.

        Extra undocumented keys break frontend clients that
        do strict schema validation on API responses.
        """
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)

        assert len(response.data) == 5, (
            f"Expected exactly 5 keys, got {len(response.data)}: "
            f"{list(response.data.keys())}"
        )

    # ── success field ─────────────────────────────────────────────────────────

    def test_success_true_for_200(self):
        """200 OK must produce success=True."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)
        assert response.data["success"] is True

    def test_success_true_for_201(self):
        """201 Created must produce success=True."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=201)
        assert response.data["success"] is True

    def test_success_true_for_204(self):
        """204 No Content must produce success=True."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=204)
        assert response.data["success"] is True

    def test_success_true_for_299(self):
        """Upper boundary of 2xx range must produce success=True."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=299)
        assert response.data["success"] is True

    def test_success_false_for_400(self):
        """400 must produce success=False."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=400)
        assert response.data["success"] is False

    def test_success_false_for_401(self):
        """401 must produce success=False."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=401)
        assert response.data["success"] is False

    def test_success_false_for_403(self):
        """403 must produce success=False."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=403)
        assert response.data["success"] is False

    def test_success_false_for_404(self):
        """404 must produce success=False."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=404)
        assert response.data["success"] is False

    def test_success_false_for_500(self):
        """500 must produce success=False."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=500)
        assert response.data["success"] is False

    def test_success_false_for_300(self):
        """
        300 (redirect) must produce success=False.

        Redirects are not successful API responses.
        3xx starts at 300 — boundary test.
        """
        mixin = self._mixin()
        response = mixin.build_response(status_code=300)
        assert response.data["success"] is False

    def test_success_is_bool_not_truthy(self):
        """
        success must be exactly True or False — not truthy/falsy int.

        Some serializers treat 1/0 and True/False differently.
        Frontend doing === True would fail if success is 1.
        """
        mixin = self._mixin()
        response_ok  = mixin.build_response(status_code=200)
        response_err = mixin.build_response(status_code=400)

        assert type(response_ok.data["success"])  is bool
        assert type(response_err.data["success"]) is bool

    # ── data field ────────────────────────────────────────────────────────────

    def test_data_field_carries_payload(self):
        """data field must contain the exact payload passed in."""
        mixin = self._mixin()
        payload = {"id": 42, "name": "test"}
        response = mixin.build_response(data=payload, status_code=200)
        assert response.data["data"] == payload

    def test_data_field_defaults_to_none(self):
        """data must default to None when not provided."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)
        assert response.data["data"] is None

    def test_data_field_accepts_list(self):
        """data must accept a list payload."""
        mixin = self._mixin()
        response = mixin.build_response(data=[1, 2, 3], status_code=200)
        assert response.data["data"] == [1, 2, 3]

    def test_data_field_accepts_empty_list(self):
        """data must accept empty list — not convert to None."""
        mixin = self._mixin()
        response = mixin.build_response(data=[], status_code=200)
        assert response.data["data"] == []

    def test_data_field_accepts_empty_dict(self):
        """data must accept empty dict — not convert to None."""
        mixin = self._mixin()
        response = mixin.build_response(data={}, status_code=200)
        assert response.data["data"] == {}

    def test_data_field_accepts_string(self):
        """data must accept string payload."""
        mixin = self._mixin()
        response = mixin.build_response(data="plain string", status_code=200)
        assert response.data["data"] == "plain string"

    def test_data_field_accepts_false(self):
        """
        data must accept False as a valid payload.

        Without the _encode pattern, False would be indistinguishable
        from None in some cache backends. Here in responses it is fine —
        we just verify False is not converted to None.
        """
        mixin = self._mixin()
        response = mixin.build_response(data=False, status_code=200)
        assert response.data["data"] is False

    # ── message field ─────────────────────────────────────────────────────────

    def test_message_field_carries_string(self):
        """message must contain the string passed in."""
        mixin = self._mixin()
        response = mixin.build_response(message="Operation complete", status_code=200)
        assert response.data["message"] == "Operation complete"

    def test_message_field_defaults_to_none(self):
        """message must default to None when not provided."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)
        assert response.data["message"] is None

    # ── errors field ──────────────────────────────────────────────────────────

    def test_errors_field_carries_error_detail(self):
        """errors must contain the error detail passed in."""
        mixin = self._mixin()
        errors = {"email": "Enter a valid email."}
        response = mixin.build_response(errors=errors, status_code=400)
        assert response.data["errors"] == errors

    def test_errors_field_defaults_to_none(self):
        """errors must default to None when not provided."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)
        assert response.data["errors"] is None

    # ── meta field ────────────────────────────────────────────────────────────

    def test_meta_field_carries_dict(self):
        """meta must contain the dict passed in."""
        mixin = self._mixin()
        meta = {"page": 1, "total": 100}
        response = mixin.build_response(meta=meta, status_code=200)
        assert response.data["meta"] == meta

    def test_meta_field_defaults_to_none(self):
        """meta must default to None when not provided."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=200)
        assert response.data["meta"] is None

    # ── HTTP status code ──────────────────────────────────────────────────────

    def test_response_status_code_matches_argument(self):
        """HTTP status code of Response must match status_code argument."""
        mixin = self._mixin()
        response = mixin.build_response(status_code=201)
        assert response.status_code == 201

    def test_response_status_code_defaults_to_200(self):
        """Default status code must be 200 when not specified."""
        mixin = self._mixin()
        response = mixin.build_response()
        assert response.status_code == 200

    # ── Custom headers ────────────────────────────────────────────────────────

    def test_custom_headers_set_on_response(self):
        """
        Custom headers passed via headers= must appear on the response.

        Used for: pagination links, rate limit headers, cache control.
        """
        mixin = self._mixin()
        response = mixin.build_response(
            status_code=200,
            headers={"X-Custom-Header": "custom-value"},
        )
        assert response["X-Custom-Header"] == "custom-value"

    def test_multiple_custom_headers_all_set(self):
        """All headers in the headers dict must be set on the response."""
        mixin = self._mixin()
        response = mixin.build_response(
            status_code=200,
            headers={
                "X-Header-One": "value-one",
                "X-Header-Two": "value-two",
            },
        )
        assert response["X-Header-One"] == "value-one"
        assert response["X-Header-Two"] == "value-two"

    def test_no_headers_argument_does_not_crash(self):
        """Omitting headers= must not raise — defaults to None."""
        mixin = self._mixin()
        # Must not raise
        response = mixin.build_response(status_code=200)
        assert response is not None

    # ── transform_payload hook ────────────────────────────────────────────────

    def test_mixin_transform_payload_returns_payload_unchanged(self):
        """
        APIResponseMixin.transform_payload() must return payload unchanged.

        The base mixin implementation is a passthrough.
        BaseAPIView overrides this to inject request_id.
        If the base implementation modifies payload, BaseAPIView's
        override would receive already-modified data — subtle bugs.
        """
        mixin = self._mixin()
        original = {
            "success": True,
            "message": "test",
            "data": {"id": 1},
            "errors": None,
            "meta": None,
        }
        result = mixin.transform_payload(original)

        assert result is original, (
            "transform_payload must return the same dict object — "
            "not a copy, not a modified version"
        )

    def test_mixin_transform_payload_called_by_build_response(self):
        """
        build_response() must call transform_payload() exactly once.

        This is the hook mechanism. If build_response() skips the call,
        BaseAPIView's request_id injection never runs — silent failure.
        """
        call_count = []

        class TrackingMixin(APIResponseMixin):
            def transform_payload(self, payload):
                call_count.append(1)
                return payload

        mixin = TrackingMixin()
        mixin.build_response(status_code=200)

        assert len(call_count) == 1, (
            f"transform_payload called {len(call_count)} times, expected 1"
        )

    def test_class_constants_used_as_keys(self):
        """
        Response keys must use the class constant values.

        If someone changes MESSAGE_KEY = "message" to MESSAGE_KEY = "msg",
        all responses silently change their key name.
        This test catches that regression.
        """
        mixin = self._mixin()
        response = mixin.build_response(
            data="test_data",
            message="test_message",
            errors="test_errors",
            meta={"k": "v"},
            status_code=200,
        )
        assert mixin.SUCCESS_KEY in response.data
        assert mixin.MESSAGE_KEY in response.data
        assert mixin.DATA_KEY    in response.data
        assert mixin.ERRORS_KEY  in response.data
        assert mixin.META_KEY    in response.data


# ─── Layer 2: BaseAPIView Response Helpers ────────────────────────────────────

@pytest.mark.unit
class TestBaseAPIViewHelpers:
    """
    Unit tests for BaseAPIView response helper methods.

    Each helper is a thin wrapper around build_response() with
    preset status codes and default messages.
    Tests verify: correct status, correct default message, correct envelope.
    """

    # ── success_response ──────────────────────────────────────────────────────

    def test_success_response_returns_200(self):
        """success_response() must return HTTP 200."""
        view = _make_view_with_request()
        response = view.success_response()
        assert response.status_code == 200

    def test_success_response_success_is_true(self):
        """success_response() must have success=True."""
        view = _make_view_with_request()
        response = view.success_response()
        assert response.data["success"] is True

    def test_success_response_default_message(self):
        """success_response() must use its default message."""
        view = _make_view_with_request()
        response = view.success_response()
        assert response.data["message"] == "Request successful"

    def test_success_response_custom_message(self):
        """Custom message must override the default."""
        view = _make_view_with_request()
        response = view.success_response(message="Custom success message")
        assert response.data["message"] == "Custom success message"

    def test_success_response_carries_data(self):
        """data payload must appear in response.data['data']."""
        view = _make_view_with_request()
        response = view.success_response(data={"id": 99})
        assert response.data["data"] == {"id": 99}

    def test_success_response_custom_status_code(self):
        """success_response() must accept custom 2xx status codes."""
        view = _make_view_with_request()
        response = view.success_response(status_code=202)
        assert response.status_code == 202
        assert response.data["success"] is True

    def test_success_response_accepts_meta(self):
        """meta parameter must be passed through to envelope."""
        view = _make_view_with_request()
        response = view.success_response(meta={"page": 1, "total": 50})
        assert response.data["meta"]["page"] == 1
        assert response.data["meta"]["total"] == 50

    def test_success_response_errors_is_none(self):
        """success_response() must never have errors set."""
        view = _make_view_with_request()
        response = view.success_response()
        assert response.data["errors"] is None

    # ── created_response ──────────────────────────────────────────────────────

    def test_created_response_returns_201(self):
        """created_response() must return HTTP 201."""
        view = _make_view_with_request()
        response = view.created_response()
        assert response.status_code == 201

    def test_created_response_success_is_true(self):
        """created_response() must have success=True."""
        view = _make_view_with_request()
        response = view.created_response()
        assert response.data["success"] is True

    def test_created_response_default_message(self):
        """created_response() must use its default message."""
        view = _make_view_with_request()
        response = view.created_response()
        assert response.data["message"] == "Resource created successfully"

    def test_created_response_custom_message(self):
        """Custom message must override the default."""
        view = _make_view_with_request()
        response = view.created_response(message="User created")
        assert response.data["message"] == "User created"

    def test_created_response_carries_data(self):
        """data payload must appear in response.data['data']."""
        view = _make_view_with_request()
        response = view.created_response(data={"id": 1, "email": "a@b.com"})
        assert response.data["data"] == {"id": 1, "email": "a@b.com"}

    def test_created_response_errors_is_none(self):
        """created_response() must never have errors set."""
        view = _make_view_with_request()
        response = view.created_response()
        assert response.data["errors"] is None

    # ── error_response ────────────────────────────────────────────────────────

    def test_error_response_returns_400(self):
        """error_response() must default to HTTP 400."""
        view = _make_view_with_request()
        response = view.error_response()
        assert response.status_code == 400

    def test_error_response_success_is_false(self):
        """error_response() must have success=False."""
        view = _make_view_with_request()
        response = view.error_response()
        assert response.data["success"] is False

    def test_error_response_default_message(self):
        """error_response() must use its default message."""
        view = _make_view_with_request()
        response = view.error_response()
        assert response.data["message"] == "Request failed"

    def test_error_response_custom_message(self):
        """Custom message must override the default."""
        view = _make_view_with_request()
        response = view.error_response(message="Email already in use")
        assert response.data["message"] == "Email already in use"

    def test_error_response_carries_errors(self):
        """
        errors payload must be formatted into {code, fields, non_fields}
        shape by error_response() automatically.

        OLD: assert response.data["errors"] == raw_dict
             This assumed errors passed through unchanged.

        NEW: error_response() calls _format_errors() automatically.
             Raw serializer.errors goes in → structured envelope comes out.
             Frontend always receives consistent shape regardless of
             what the view passes in.

        Why this is correct behavior:
            View passes serializer.errors which is a flat dict like
            {"email": [ErrorDetail("...", code="email_already_exists")]}.
            _format_errors() converts this to:
            {
                "code": "validation_error",
                "fields": {"email": {"message": "...", "code": "..."}},
                "non_fields": None
            }
            Frontend reads errors.fields.email.code — not errors.email.
        """
        view = _make_view_with_request()
        response = view.error_response(
            errors={"email": "This email is already registered."},
            status_code=400,
        )
        errors = response.data["errors"]

        # Must be the structured shape — not the raw dict
        assert isinstance(errors, dict)
        assert "code"       in errors
        assert "fields"     in errors
        assert "non_fields" in errors
        assert errors["code"] == ErrorCode.VALIDATION_ERROR

    def test_error_response_custom_status_code(self):
        """error_response() must accept custom 4xx/5xx status codes."""
        view = _make_view_with_request()
        response = view.error_response(status_code=422)
        assert response.status_code == 422
        assert response.data["success"] is False

    def test_error_response_data_is_none(self):
        """error_response() must never have data set."""
        view = _make_view_with_request()
        response = view.error_response()
        assert response.data["data"] is None

    # ── not_found_response ────────────────────────────────────────────────────

    def test_not_found_response_returns_404(self):
        """not_found_response() must return HTTP 404."""
        view = _make_view_with_request()
        response = view.not_found_response()
        assert response.status_code == 404

    def test_not_found_response_success_is_false(self):
        view = _make_view_with_request()
        response = view.not_found_response()
        assert response.data["success"] is False

    def test_not_found_response_default_message(self):
        """not_found_response() must use its default message."""
        view = _make_view_with_request()
        response = view.not_found_response()
        assert response.data["message"] == "Resource not found"

    def test_not_found_response_custom_message(self):
        """Custom message must override the default."""
        view = _make_view_with_request()
        response = view.not_found_response(message="Product not found")
        assert response.data["message"] == "Product not found"

    def test_not_found_response_data_is_none(self):
        view = _make_view_with_request()
        response = view.not_found_response()
        assert response.data["data"] is None

    # ── unauthorized_response ─────────────────────────────────────────────────

    def test_unauthorized_response_returns_401(self):
        """unauthorized_response() must return HTTP 401."""
        view = _make_view_with_request()
        response = view.unauthorized_response()
        assert response.status_code == 401

    def test_unauthorized_response_success_is_false(self):
        view = _make_view_with_request()
        response = view.unauthorized_response()
        assert response.data["success"] is False

    def test_unauthorized_response_default_message(self):
        """unauthorized_response() must use its default message."""
        view = _make_view_with_request()
        response = view.unauthorized_response()
        assert response.data["message"] == "Authentication required"

    def test_unauthorized_response_custom_message(self):
        view = _make_view_with_request()
        response = view.unauthorized_response(message="Token expired")
        assert response.data["message"] == "Token expired"

    def test_unauthorized_response_data_is_none(self):
        view = _make_view_with_request()
        response = view.unauthorized_response()
        assert response.data["data"] is None

    # ── forbidden_response ────────────────────────────────────────────────────

    def test_forbidden_response_returns_403(self):
        """forbidden_response() must return HTTP 403."""
        view = _make_view_with_request()
        response = view.forbidden_response()
        assert response.status_code == 403

    def test_forbidden_response_success_is_false(self):
        view = _make_view_with_request()
        response = view.forbidden_response()
        assert response.data["success"] is False

    def test_forbidden_response_default_message(self):
        """forbidden_response() must use its default message."""
        view = _make_view_with_request()
        response = view.forbidden_response()
        assert response.data["message"] == (
            "You do not have permission to perform this action"
        )

    def test_forbidden_response_custom_message(self):
        view = _make_view_with_request()
        response = view.forbidden_response(message="Admin only")
        assert response.data["message"] == "Admin only"

    def test_forbidden_response_data_is_none(self):
        view = _make_view_with_request()
        response = view.forbidden_response()
        assert response.data["data"] is None


# ─── Layer 3: transform_payload() + request_id injection ─────────────────────

@pytest.mark.unit
class TestTransformPayloadRequestID:
    """
    Tests for BaseAPIView.transform_payload() — request_id injection.

    This override is the bridge between RequestIDMiddleware and responses.
    RequestIDMiddleware sets request.id.
    transform_payload() reads it and puts it in meta.request_id.

    Without this, clients cannot correlate error responses with logs.
    """

    def test_request_id_injected_into_meta_when_present(self):
        """
        When request.id exists, meta.request_id must match it exactly.

        This is the happy path — middleware ran, ID was set,
        response must carry it in meta.
        """
        view = _make_view_with_request()
        view.request.id = "test-uuid-abc-123"

        response = view.success_response(data=None)

        assert "meta" in response.data
        assert "request_id" in response.data["meta"], (
            "request_id missing from meta — "
            "check BaseAPIView.transform_payload()"
        )
        assert response.data["meta"]["request_id"] == "test-uuid-abc-123"

    def test_no_request_id_does_not_crash(self):
        """
        When request has no id attribute, transform_payload must not raise.

        Happens in unit tests that bypass RequestIDMiddleware.
        getattr(self.request, 'id', None) must silently return None.
        """
        view = _make_view_with_request()
        # Deliberately do NOT set request.id

        # Must not raise AttributeError
        try:
            response = view.success_response(data=None)
        except AttributeError as e:
            pytest.fail(
                f"transform_payload raised AttributeError when request.id "
                f"is absent: {e}"
            )

        assert response is not None

    def test_no_request_id_leaves_meta_unchanged(self):
        """
        When request.id is absent, existing meta must not be modified.

        If caller passes meta={"page": 1}, and there is no request.id,
        the page key must still be there — not erased.
        """
        view = _make_view_with_request()
        # No request.id set

        response = view.success_response(meta={"page": 1, "total": 50})

        # meta values passed by caller must survive
        assert response.data["meta"]["page"] == 1
        assert response.data["meta"]["total"] == 50

    def test_request_id_added_to_existing_meta(self):
        """
        When both meta and request.id are present,
        request_id must be added to existing meta — not replace it.

        Pagination meta + request_id must coexist in the same dict.
        """
        view = _make_view_with_request()
        view.request.id = "inject-into-existing-meta"

        response = view.success_response(
            meta={"page": 2, "total": 100}
        )

        meta = response.data["meta"]
        assert meta["request_id"] == "inject-into-existing-meta"
        assert meta["page"]       == 2
        assert meta["total"]      == 100

    def test_request_id_injected_when_meta_is_none(self):
        """
        When meta=None and request.id is set,
        transform_payload must create meta dict with request_id.

        Most endpoints pass no explicit meta.
        request_id must still appear.
        """
        view = _make_view_with_request()
        view.request.id = "create-meta-from-none"

        response = view.success_response()  # no meta passed

        assert response.data["meta"] is not None
        assert response.data["meta"]["request_id"] == "create-meta-from-none"

    def test_transform_payload_called_on_every_helper(self):
        """
        transform_payload() must be called by every response helper.

        All helpers delegate to build_response() which calls transform_payload().
        If any helper bypasses build_response(), request_id injection breaks
        silently for that specific response type.
        """
        view = _make_view_with_request()
        view.request.id = "verify-all-helpers-inject"

        helpers_and_responses = [
            view.success_response(),
            view.created_response(),
            view.error_response(),
            view.not_found_response(),
            view.unauthorized_response(),
            view.forbidden_response(),
        ]

        for i, response in enumerate(helpers_and_responses):
            helper_names = [
                "success_response",
                "created_response",
                "error_response",
                "not_found_response",
                "unauthorized_response",
                "forbidden_response",
            ]
            meta = response.data.get("meta")
            assert meta is not None, (
                f"{helper_names[i]}() returned meta=None — "
                f"transform_payload() may not be called"
            )
            assert meta.get("request_id") == "verify-all-helpers-inject", (
                f"{helper_names[i]}() did not inject request_id into meta"
            )


# ─── Layer 4: HTTP Integration Tests ─────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestBaseAPIViewHTTPIntegration:
    """
    Integration tests — verify response envelope via full HTTP stack.

    Uses test views from conftest.py.
    Proves that the complete chain works:
        Request → Middleware → View → build_response → transform_payload → Response
    """

    @override_settings(ROOT_URLCONF=__name__)
    def test_public_endpoint_returns_standard_envelope(self, api_client):
        """
        GET /test/public/ must return the full standard envelope.

        This is the most basic integration test — if this fails,
        the entire response infrastructure is broken.
        """
        response = api_client.get("/test/public/")

        assert response.status_code == 200
        for key in ("success", "message", "data", "errors", "meta"):
            assert key in response.data, f"Missing key: {key}"

    @override_settings(ROOT_URLCONF=__name__)
    def test_success_response_shape_via_http(self, api_client):
        """Success response via HTTP must have correct field values."""
        response = api_client.get("/test/public/")

        assert response.data["success"] is True
        assert response.data["errors"] is None
        assert response.data["data"] is not None

    @override_settings(ROOT_URLCONF=__name__)
    def test_request_id_in_meta_via_http(self, api_client):
        """
        meta.request_id must be present in HTTP responses.

        Full chain: RequestIDMiddleware → transform_payload → meta.request_id
        """
        response = api_client.get("/test/public/")

        assert "meta" in response.data
        assert "request_id" in response.data["meta"]
        assert response.data["meta"]["request_id"] is not None

    @override_settings(ROOT_URLCONF=__name__)
    def test_x_request_id_header_present_via_http(self, api_client):
        """
        X-Request-ID response header must be present on all responses.

        Set by RequestIDMiddleware — independent of response body.
        """
        response = api_client.get("/test/public/")
        assert response.get("X-Request-ID") is not None

    @override_settings(ROOT_URLCONF=__name__)
    def test_envelope_consistent_across_multiple_requests(self, api_client):
        """
        Envelope shape must be identical across multiple requests.

        Verifies no per-request state corruption in the response building chain.
        """
        for _ in range(5):
            response = api_client.get("/test/public/")
            assert response.status_code == 200
            for key in ("success", "message", "data", "errors", "meta"):
                assert key in response.data

    def test_error_response_formats_serializer_errors_with_field_codes(self):
        """
        When errors contains ErrorDetail objects with custom codes,
        those codes must survive into errors.fields.field_name.code.

        This is the end-to-end test for the registration email_already_exists
        case — serializer raises with ErrorCode.EMAIL_ALREADY_EXISTS,
        error_response() must preserve it all the way to the response.
        """
        from rest_framework.exceptions import ErrorDetail

        view = _make_view_with_request()
        response = view.error_response(
            errors={
                "email": [
                    ErrorDetail(
                        "An account with this email already exists.",
                        code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    )
                ]
            },
            status_code=400,
        )

        errors = response.data["errors"]
        assert errors["fields"]["email"]["code"]    == ErrorCode.EMAIL_ALREADY_EXISTS
        assert errors["fields"]["email"]["message"] == (
            "An account with this email already exists."
        )

    def test_error_response_none_errors_stays_none(self):
        """
        When errors=None is passed, errors in response must be None.

        _format_errors() must NOT be called on None — it would return
        a structured dict with no useful content, which is misleading.
        None means 'no error detail available' — preserve that signal.
        """
        view = _make_view_with_request()
        response = view.error_response(
            message="Something went wrong.",
            errors=None,
            status_code=500,
        )
        assert response.data["errors"] is None

    def test_error_response_non_field_error_goes_to_non_fields(self):
        """
        non_field_errors in serializer.errors must map to errors.non_fields.

        The key separation between field and non-field errors is what
        enables the frontend to show a banner (non_fields) vs field
        highlight (fields) correctly.
        """
        from rest_framework.exceptions import ErrorDetail

        view = _make_view_with_request()
        response = view.error_response(
            errors={
                "non_field_errors": [
                    ErrorDetail(
                        "Please verify your email address.",
                        code=ErrorCode.EMAIL_NOT_VERIFIED,
                    )
                ]
            },
            status_code=400,
        )

        errors = response.data["errors"]
        assert errors["fields"]             is None
        assert errors["non_fields"]         is not None
        assert errors["non_fields"]["code"] == ErrorCode.EMAIL_NOT_VERIFIED
