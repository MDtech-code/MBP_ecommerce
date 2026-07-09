# backend/apps/core/tests/test_exceptions.py
"""
Tests for apps.core.api.exceptions module.

This module is the most critical infrastructure component in the backend.
Every single error response — from every app, every endpoint — flows
through custom_exception_handler. If it breaks, ALL error responses break.

Three layers of tests:

    Layer 1 — _format_errors() unit tests
        Pure function. No DB. No HTTP. Tests normalization logic directly.
        Fastest possible — milliseconds.

    Layer 2 — _status_to_message() unit tests
        Pure function. Verifies correct human-readable messages per status code.

    Layer 3 — custom_exception_handler() integration tests
        Full HTTP stack via test views defined in conftest.py.
        Verifies the complete error envelope shape on real responses.

    Layer 4 — Monitor registry tests
        Tests register_monitor() and _notify_monitors() behavior.
        Verifies broken monitors cannot suppress responses.
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    PermissionDenied,
    Throttled,
    ValidationError,
)
from rest_framework.test import APIRequestFactory

from apps.core.api.exceptions import (
    _format_errors,
    _monitors,
    _notify_monitors,
    _status_to_message,
    custom_exception_handler,
    register_monitor,
)
from .conftest import test_urlpatterns

# ─── URL override for integration tests ───────────────────────────────────────

urlpatterns = test_urlpatterns


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_request(path: str = "/test/"):
    """
    Build a minimal DRF-compatible request for direct handler testing.

    Why APIRequestFactory not RequestFactory:
        custom_exception_handler receives a DRF Request object.
        APIRequestFactory produces DRF-wrapped requests.
        Django's RequestFactory produces raw Django HttpRequest objects
        which lack DRF request attributes — causing AttributeError inside
        the handler when it calls getattr(request, "id", None).
    """
    factory = APIRequestFactory()
    return factory.get(path)


def assert_error_envelope(data: dict) -> None:
    """
    Assert response conforms to the standard error envelope.

    Extracted as a shared helper because EVERY error test needs
    exactly these same five assertions. DRY principle.

    Standard error envelope:
        success  → always False on errors
        message  → human readable string, never None on errors
        data     → always None on errors
        errors   → error detail (may be None for 500 in production)
        meta     → dict containing at minimum request_id key
    """
    assert "success" in data,  "Envelope missing 'success' key"
    assert "message" in data,  "Envelope missing 'message' key"
    assert "data"    in data,  "Envelope missing 'data' key"
    assert "errors"  in data,  "Envelope missing 'errors' key"
    assert "meta"    in data,  "Envelope missing 'meta' key"
    assert data["success"] is False, "success must be False on error responses"
    assert data["data"] is None,     "data must be None on error responses"


# ─── Layer 1: _format_errors() Unit Tests ─────────────────────────────────────

@pytest.mark.unit
class TestFormatErrors:
    """
    Unit tests for _format_errors().

    DRF produces errors in three formats depending on exception type.
    _format_errors() normalizes all three into a consistent shape
    so the frontend always receives predictable error structures.

    Formats DRF produces:
        str  → "Not found."
        list → ["This field is required.", "Another error."]
        dict → {"email": ["Enter a valid email address."]}
    """

    # ── dict input ────────────────────────────────────────────────────────────

    def test_dict_single_item_list_unwrapped_to_string(self):
        """
        Single-item list values in dict must be unwrapped to plain string.

        DRF always wraps field errors in lists even when there is only one.
        Frontend showing ["Enter a valid email."] looks worse than
        "Enter a valid email." — unwrapping improves UX.

        Before: {"email": ["Enter a valid email address."]}
        After:  {"email": "Enter a valid email address."}
        """
        result = _format_errors({"email": ["Enter a valid email address."]})
        assert result == {"email": "Enter a valid email address."}

    def test_dict_multi_item_list_kept_as_list(self):
        """
        Multi-item list values in dict must stay as list.

        When a field has multiple errors, all must be preserved.
        Unwrapping would silently discard all but the first error.

        Before: {"password": ["Too short.", "Too common."]}
        After:  {"password": ["Too short.", "Too common."]}
        """
        result = _format_errors({"password": ["Too short.", "Too common."]})
        assert result == {"password": ["Too short.", "Too common."]}

    def test_dict_string_value_kept_as_string(self):
        """
        Dict values that are already strings must not be modified.

        Some DRF exceptions produce string values directly in dicts.
        _format_errors must not wrap or alter them.
        """
        result = _format_errors({"detail": "Not found."})
        assert result == {"detail": "Not found."}

    def test_dict_multiple_fields_each_processed_independently(self):
        """
        Each field in a dict must be processed independently.

        A mix of single-item lists (unwrapped) and multi-item lists (kept)
        must each be handled correctly without affecting each other.
        """
        result = _format_errors({
            "email":    ["Enter a valid email address."],
            "password": ["Too short.", "Too common."],
            "name":     "This field is required.",
        })
        assert result["email"]    == "Enter a valid email address."
        assert result["password"] == ["Too short.", "Too common."]
        assert result["name"]     == "This field is required."

    def test_dict_empty_dict_returned_unchanged(self):
        """Empty dict must be returned as empty dict."""
        result = _format_errors({})
        assert result == {}

    def test_dict_empty_list_value_kept_as_empty_list(self):
        """
        Empty list value must be kept as empty list.

        An empty list is not a single-item list — must not be unwrapped
        to None or any other value.
        """
        result = _format_errors({"field": []})
        assert result == {"field": []}

    # ── list input ────────────────────────────────────────────────────────────

    def test_single_item_list_unwrapped_to_string(self):
        """
        Single-item top-level list must be unwrapped to its element.

        DRF non_field_errors produces ["Error message."] for single errors.
        Unwrapping gives frontend a plain string instead of a list.

        Before: ["Authentication credentials were not provided."]
        After:  "Authentication credentials were not provided."
        """
        result = _format_errors(["Authentication credentials were not provided."])
        assert result == "Authentication credentials were not provided."

    def test_multi_item_list_kept_as_list(self):
        """
        Multi-item top-level list must stay as list.

        Multiple non-field errors must all be preserved.
        """
        result = _format_errors(["Error one.", "Error two."])
        assert result == ["Error one.", "Error two."]

    def test_empty_list_returned_unchanged(self):
        """Empty list must be returned as empty list."""
        result = _format_errors([])
        assert result == []

    # ── string input ──────────────────────────────────────────────────────────

    def test_string_returned_unchanged(self):
        """
        Plain string input must be returned unchanged.

        Some DRF exceptions (e.g. NotFound) produce a plain string.
        _format_errors must pass it through without modification.
        """
        result = _format_errors("Not found.")
        assert result == "Not found."

    def test_empty_string_returned_unchanged(self):
        """Empty string must be returned as empty string."""
        result = _format_errors("")
        assert result == ""

    # ── edge cases ────────────────────────────────────────────────────────────

    def test_none_returned_unchanged(self):
        """
        None input must be returned as None.

        500 errors in production pass errors=None to avoid leaking internals.
        _format_errors must not crash on None input.
        """
        result = _format_errors(None)
        assert result is None

    def test_integer_returned_unchanged(self):
        """Unexpected types must be returned unchanged — no crash."""
        result = _format_errors(42)
        assert result == 42


# ─── Layer 2: _status_to_message() Unit Tests ─────────────────────────────────

@pytest.mark.unit
class TestStatusToMessage:
    """
    Unit tests for _status_to_message().

    Every error response uses this to build its human-readable message.
    Frontend displays these messages directly to users.
    They must be informative but never leak implementation details.
    """

    @pytest.mark.parametrize("status_code,expected_fragment", [
        (400, "Invalid request data."),
        (401, "Authentication required."),
        (403, "You do not have permission to perform this action."),
        (404, "The requested resource was not found."),
        (405, "Method not allowed."),
        (429, "Too many requests. Please slow down."),
        (500, "An unexpected error occurred. Please try again later."),
    ])
    def test_known_status_codes_return_correct_message(
        self, status_code, expected_fragment
    ):
        """
        Each known status code must return its designated message.

        Parametrized so adding a new status code mapping only requires
        adding one line to the parametrize list above.
        """
        result = _status_to_message(status_code)
        assert result == expected_fragment, (
            f"Status {status_code}: expected {expected_fragment!r}, got {result!r}"
        )

    def test_unknown_status_code_returns_fallback(self):
        """
        Unknown status codes must return the generic fallback message.

        We cannot anticipate every possible status code.
        Fallback prevents KeyError and keeps response envelope intact.
        """
        result = _status_to_message(418)  # I'm a teapot
        assert result == "Request failed."

    def test_returns_string_for_all_known_codes(self):
        """Return type must always be str — never None, never int."""
        known_codes = [400, 401, 403, 404, 405, 429, 500]
        for code in known_codes:
            result = _status_to_message(code)
            assert isinstance(result, str), (
                f"Expected str for status {code}, got {type(result).__name__}"
            )

    def test_fallback_is_string(self):
        """Fallback for unknown codes must also be a string."""
        result = _status_to_message(999)
        assert isinstance(result, str)


# ─── Layer 3: custom_exception_handler() Integration Tests ────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestCustomExceptionHandlerDirect:
    """
    Tests for custom_exception_handler() called directly.

    We call the handler directly with a mock request and context
    rather than going through the full HTTP stack.

    Why both direct tests AND HTTP tests:
        Direct → faster, pinpoints exactly which exception type fails
        HTTP   → proves the handler is correctly wired in settings.py
                 and runs in the real Django request/response cycle
    """

    # ── Envelope shape on all exception types ─────────────────────────────────

    def test_validation_error_returns_400_with_envelope(self):
        """ValidationError must produce 400 with standard error envelope."""
        request = _make_request()
        exc = ValidationError({"email": ["Enter a valid email address."]})

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 400
        assert_error_envelope(response.data)

    def test_not_found_returns_404_with_envelope(self):
        """NotFound must produce 404 with standard error envelope."""
        request = _make_request()
        exc = NotFound()

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 404
        assert_error_envelope(response.data)

    def test_permission_denied_returns_403_with_envelope(self):
        """PermissionDenied must produce 403 with standard error envelope."""
        request = _make_request()
        exc = PermissionDenied()

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 403
        assert_error_envelope(response.data)

    def test_not_authenticated_returns_401_with_envelope(self):
        """NotAuthenticated must produce 401 with standard error envelope."""
        request = _make_request()
        exc = NotAuthenticated()

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 401
        assert_error_envelope(response.data)

    def test_method_not_allowed_returns_405_with_envelope(self):
        """MethodNotAllowed must produce 405 with standard error envelope."""
        request = _make_request()
        exc = MethodNotAllowed("DELETE")

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 405
        assert_error_envelope(response.data)

    def test_throttled_returns_429_with_envelope(self):
        """Throttled must produce 429 with standard error envelope."""
        request = _make_request()
        exc = Throttled()

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 429
        assert_error_envelope(response.data)

    def test_unhandled_exception_returns_500_with_envelope(self):
        """
        Unhandled Python exceptions must produce 500 with standard envelope.

        RuntimeError has no DRF handler — response from exception_handler
        will be None. Our handler must catch this and return 500.
        """
        request = _make_request()
        exc = RuntimeError("Something broke unexpectedly")

        response = custom_exception_handler(exc, {"request": request})

        assert response.status_code == 500
        assert_error_envelope(response.data)

    # ── Error field content ───────────────────────────────────────────────────

    def test_validation_error_field_errors_in_errors_key(self):
        """
        Field-level validation errors must appear in response.data['errors'].

        Frontend reads errors.email, errors.password etc to show
        field-specific error messages next to the correct input.
        """
        request = _make_request()
        exc = ValidationError({"email": ["Enter a valid email address."]})

        response = custom_exception_handler(exc, {"request": request})

        assert "email" in response.data["errors"]

    def test_validation_single_error_unwrapped(self):
        """
        Single validation error must be unwrapped from list to string.

        _format_errors must be applied — ["error"] becomes "error".
        """
        request = _make_request()
        exc = ValidationError({"email": ["Enter a valid email address."]})

        response = custom_exception_handler(exc, {"request": request})

        assert isinstance(response.data["errors"]["email"], str)

    def test_validation_multiple_errors_kept_as_list(self):
        """Multiple field errors must all be preserved as list."""
        request = _make_request()
        exc = ValidationError({"password": ["Too short.", "Too common."]})

        response = custom_exception_handler(exc, {"request": request})

        assert isinstance(response.data["errors"]["password"], list)
        assert len(response.data["errors"]["password"]) == 2

    # ── Message content ───────────────────────────────────────────────────────

    def test_400_message_is_correct(self):
        """400 response must use the designated message string."""
        request = _make_request()
        exc = ValidationError({"field": ["error"]})

        response = custom_exception_handler(exc, {"request": request})

        assert response.data["message"] == "Invalid request data."

    def test_404_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(
            NotFound(), {"request": request}
        )
        assert response.data["message"] == "The requested resource was not found."

    def test_401_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(
            NotAuthenticated(), {"request": request}
        )
        assert response.data["message"] == "Authentication required."

    def test_403_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(
            PermissionDenied(), {"request": request}
        )
        assert response.data["message"] == (
            "You do not have permission to perform this action."
        )

    def test_500_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(
            RuntimeError("boom"), {"request": request}
        )
        assert response.data["message"] == (
            "An unexpected error occurred. Please try again later."
        )

    # ── request_id in meta ────────────────────────────────────────────────────

    def test_request_id_injected_into_meta_when_present(self):
        """
        When request has an id attribute, meta.request_id must match it.

        This is how frontend correlates an error response with backend logs.
        """
        request = _make_request()
        request.id = "test-correlation-id-abc123"

        response = custom_exception_handler(
            NotFound(), {"request": request}
        )

        assert response.data["meta"]["request_id"] == "test-correlation-id-abc123"

    def test_request_id_is_none_when_not_on_request(self):
        """
        When request has no id attribute, meta.request_id must be None.

        Must not raise AttributeError — graceful degradation.
        Happens in tests that bypass RequestIDMiddleware.
        """
        request = _make_request()
        # Deliberately do NOT set request.id

        response = custom_exception_handler(
            NotFound(), {"request": request}
        )

        # meta must exist and request_id key must be present
        assert "meta" in response.data
        assert "request_id" in response.data["meta"]
        assert response.data["meta"]["request_id"] is None

    def test_meta_present_on_all_error_types(self):
        """
        meta dict must be present on every error response type.

        Checked across all major exception types to ensure
        no code path returns a response without meta.
        """
        request = _make_request()
        exceptions = [
            ValidationError({"f": ["e"]}),
            NotFound(),
            PermissionDenied(),
            NotAuthenticated(),
            RuntimeError("boom"),
        ]
        for exc in exceptions:
            response = custom_exception_handler(exc, {"request": request})
            assert "meta" in response.data, (
                f"meta missing for {type(exc).__name__}"
            )

    # ── Production safety — no internals leaked ───────────────────────────────

    @override_settings(DEBUG=False)
    def test_unhandled_exception_errors_is_none_in_production(self):
        """
        In production (DEBUG=False), errors must be None for 500 responses.

        Raw exception messages often contain:
            - Database table names
            - File system paths
            - Internal variable values
        Exposing these helps attackers. errors=None in production is required.
        """
        request = _make_request()
        exc = RuntimeError("SELECT * FROM secret_table WHERE password=...")

        response = custom_exception_handler(exc, {"request": request})

        assert response.data["errors"] is None, (
            "Production 500 must never expose exception details in errors field"
        )

    @override_settings(DEBUG=True)
    def test_unhandled_exception_errors_exposed_in_debug(self):
        """
        In DEBUG mode, exception detail appears in errors for dev convenience.

        Developers need to see the actual error without hunting through logs.
        This ONLY applies when DEBUG=True — never in production.
        """
        request = _make_request()
        exc = RuntimeError("Detailed debug error message")

        response = custom_exception_handler(exc, {"request": request})

        assert response.data["errors"] == "Detailed debug error message"

    def test_no_request_in_context_handled_gracefully(self):
        """
        Missing request in context must not crash the handler.

        context.get("request") returns None — handler must handle this
        without AttributeError on getattr(None, "id", None).
        """
        exc = NotFound()

        # Must not raise
        response = custom_exception_handler(exc, {})

        assert response is not None
        assert response.status_code == 404


# ─── Layer 3b: HTTP Stack Integration Tests ───────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestCustomExceptionHandlerHTTP:
    """
    Tests custom_exception_handler through the full HTTP stack.

    Uses test views from conftest.py via override_settings.
    Proves the handler is correctly wired in REST_FRAMEWORK settings
    and produces correct envelopes in real request/response cycles.
    """

    @override_settings(ROOT_URLCONF=__name__)
    def test_unhandled_exception_returns_500_envelope_via_http(
        self, api_client
    ):
        """
        Full stack: unhandled RuntimeError → 500 standard envelope.

        Proves exception handler is wired in settings.py correctly.
        If EXCEPTION_HANDLER setting is wrong, Django returns its own
        HTML error page instead of our JSON envelope.
        """
        response = api_client.get("/test/unhandled-error/")

        assert response.status_code == 500
        assert_error_envelope(response.data)

    @override_settings(ROOT_URLCONF=__name__)
    def test_validation_error_returns_400_envelope_via_http(self, api_client):
        """Full stack: ValidationError → 400 standard envelope."""
        response = api_client.get("/test/validation-error/")

        assert response.status_code == 400
        assert_error_envelope(response.data)

    @override_settings(ROOT_URLCONF=__name__)
    def test_validation_error_field_present_via_http(self, api_client):
        """
        Full stack: field errors must be in errors.email via HTTP.

        RaiseValidationErrorView raises ValidationError on email field.
        """
        response = api_client.get("/test/validation-error/")

        assert "email" in response.data["errors"]

    @override_settings(ROOT_URLCONF=__name__)
    def test_request_id_in_meta_on_error_via_http(self, api_client):
        """
        Full stack: meta.request_id must be present on error responses.

        RequestIDMiddleware → custom_exception_handler → meta.request_id.
        This is the most important end-to-end test for error correlation.
        """
        response = api_client.get("/test/unhandled-error/")

        assert response.data["meta"].get("request_id") is not None

    @override_settings(ROOT_URLCONF=__name__)
    def test_success_false_on_all_error_responses_via_http(self, api_client):
        """success must be False on all error responses from real views."""
        error_urls = [
            "/test/unhandled-error/",
            "/test/validation-error/",
        ]
        for url in error_urls:
            response = api_client.get(url)
            assert response.data["success"] is False, (
                f"success was not False for {url}"
            )


# ─── Layer 4: Monitor Registry Tests ──────────────────────────────────────────

@pytest.mark.unit
class TestMonitorRegistry:
    """
    Tests for register_monitor() and _notify_monitors().

    Monitors are callbacks that get called when unexpected exceptions occur.
    In production, Sentry is registered as a monitor.
    These tests verify the registry mechanics work correctly
    and that a broken monitor cannot suppress other monitors or responses.
    """

    def setup_method(self):
        """
        Snapshot the monitors list before each test.
        Restored in teardown_method so tests do not pollute each other.
        """
        self._original_monitors = list(_monitors)

    def teardown_method(self):
        """Restore monitors list to pre-test state."""
        _monitors.clear()
        _monitors.extend(self._original_monitors)

    def test_register_monitor_adds_callable(self):
        """register_monitor must add the callable to _monitors list."""
        initial_count = len(_monitors)

        def my_monitor(exc):
            pass

        register_monitor(my_monitor)
        assert len(_monitors) == initial_count + 1
        assert my_monitor in _monitors

    def test_monitor_is_called_on_notify(self):
        """_notify_monitors must call each registered monitor."""
        called_with = []

        def capturing_monitor(exc):
            called_with.append(exc)

        register_monitor(capturing_monitor)

        test_exc = RuntimeError("test error")
        _notify_monitors(test_exc)

        assert len(called_with) == 1
        assert called_with[0] is test_exc

    def test_monitor_receives_correct_exception(self):
        """Monitor must receive the exact exception object, not a copy."""
        received = []

        def capture(exc):
            received.append(exc)

        register_monitor(capture)
        exc = ValueError("specific error")
        _notify_monitors(exc)

        assert received[0] is exc

    def test_multiple_monitors_all_called(self):
        """
        All registered monitors must be called — not just the first.

        In production you may have both Sentry and PagerDuty registered.
        If first monitor failure stops iteration, PagerDuty never fires.
        """
        call_counts = {"first": 0, "second": 0, "third": 0}

        register_monitor(lambda exc: call_counts.__setitem__("first",  call_counts["first"]  + 1))
        register_monitor(lambda exc: call_counts.__setitem__("second", call_counts["second"] + 1))
        register_monitor(lambda exc: call_counts.__setitem__("third",  call_counts["third"]  + 1))

        _notify_monitors(RuntimeError("boom"))

        assert call_counts["first"]  == 1
        assert call_counts["second"] == 1
        assert call_counts["third"]  == 1

    def test_broken_monitor_does_not_prevent_other_monitors_from_running(self):
        """
        A monitor that raises must not stop subsequent monitors from running.

        Critical production requirement:
            If Sentry raises NetworkError, PagerDuty must still fire.
            Broken monitoring must never cascade into silent monitoring failure.
        """
        second_called = []

        def broken_monitor(exc):
            raise RuntimeError("Monitor itself is broken")

        def working_monitor(exc):
            second_called.append(exc)

        register_monitor(broken_monitor)
        register_monitor(working_monitor)

        # Must not raise despite broken_monitor
        _notify_monitors(RuntimeError("original error"))

        assert len(second_called) == 1

    def test_broken_monitor_does_not_raise_to_caller(self):
        """
        _notify_monitors must never propagate monitor exceptions.

        If monitor exceptions propagated, a broken Sentry integration
        would crash the exception handler itself — turning a handled
        error into an unhandled crash. Unacceptable in production.
        """
        def always_crashes(exc):
            raise RuntimeError("I always crash")

        register_monitor(always_crashes)

        # Must not raise
        try:
            _notify_monitors(RuntimeError("original"))
        except Exception as e:
            pytest.fail(
                f"_notify_monitors raised an exception to caller: {e}"
            )

    def test_monitors_not_called_for_4xx_exceptions(self):
        """
        Monitors must NOT be called for client errors (4xx).

        Monitors are for unexpected server errors only.
        Calling monitors for every 400/404 would:
            - Flood Sentry with noise
            - Trigger false PagerDuty alerts
            - Make real errors impossible to find
        """
        monitor_called = []

        def monitor(exc):
            monitor_called.append(exc)

        register_monitor(monitor)

        request = _make_request()
        custom_exception_handler(
            NotFound(), {"request": request}
        )
        custom_exception_handler(
            ValidationError({"f": ["e"]}), {"request": request}
        )
        custom_exception_handler(
            PermissionDenied(), {"request": request}
        )

        assert len(monitor_called) == 0, (
            f"Monitor was called {len(monitor_called)} times for 4xx exceptions "
            f"— monitors must only fire for unhandled/5xx exceptions"
        )

    def test_monitors_called_for_unhandled_exception(self):
        """
        Monitors MUST be called for unhandled exceptions (response=None).

        RuntimeError has no DRF handler — this is the category of exceptions
        that represents real bugs and infrastructure failures.
        """
        monitor_called = []

        def monitor(exc):
            monitor_called.append(exc)

        register_monitor(monitor)

        request = _make_request()
        custom_exception_handler(
            RuntimeError("real unexpected error"), {"request": request}
        )

        assert len(monitor_called) == 1