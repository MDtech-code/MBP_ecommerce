# backend/apps/core/tests/test_exceptions.py
"""
Tests for apps.core.api.exceptions module.

This module is the most critical infrastructure component in the backend.
Every single error response — from every app, every endpoint — flows
through custom_exception_handler. If it breaks, ALL error responses break.

Four layers of tests:

    Layer 1 — _format_errors() unit tests
        Pure function. No DB. No HTTP. Tests normalization logic directly.
        Fastest possible — milliseconds.
        NEW: Tests assert the structured {code, fields, non_fields} envelope
             instead of the old flat shape.

    Layer 2 — _status_to_message() unit tests
        Pure function. Verifies correct human-readable messages per status code.
        UNCHANGED — function signature and output identical.

    Layer 3 — custom_exception_handler() integration tests
        Full HTTP stack via test views defined in conftest.py.
        Verifies the complete error envelope shape on real responses.
        NEW: assert_error_envelope() now validates errors sub-structure too.

    Layer 4 — Monitor registry tests
        Tests register_monitor() and _notify_monitors() behavior.
        UNCHANGED — no dependency on error shape.
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.exceptions import (
    AuthenticationFailed,
    ErrorDetail,
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
from apps.core.error_codes import ErrorCode
from apps.core.tests.urls import test_urlpatterns

# ─── URL override for integration tests ──────────────────────────────────────

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

    Validates two levels:

    Level 1 — outer envelope keys (unchanged from before):
        success  → always False on errors
        message  → human readable string, never None on errors
        data     → always None on errors
        errors   → structured error dict (see Level 2)
        meta     → dict containing at minimum request_id key

    Level 2 — errors sub-structure (NEW):
        When errors is not None it must always contain exactly
        three keys: code, fields, non_fields.
        This guarantees frontend can always access errors.code
        without defensive checks for different shapes.

    Why validate Level 2 here:
        Every integration test calls assert_error_envelope().
        Putting the sub-structure check here means every test
        automatically validates the new contract without repeating
        assertions in each individual test.
    """
    assert "success" in data, "Envelope missing 'success' key"
    assert "message" in data, "Envelope missing 'message' key"
    assert "data"    in data, "Envelope missing 'data' key"
    assert "errors"  in data, "Envelope missing 'errors' key"
    assert "meta"    in data, "Envelope missing 'meta' key"

    assert data["success"] is False, "success must be False on error responses"
    assert data["data"]    is None,  "data must be None on error responses"

    # ── Level 2: errors sub-structure ─────────────────────────────────────
    # 500 in production sends errors=None intentionally to avoid leaking
    # internals. Every other error must have the structured shape.
    if data["errors"] is not None:
        errors = data["errors"]
        assert "code"       in errors, "errors missing 'code' key"
        assert "fields"     in errors, "errors missing 'fields' key"
        assert "non_fields" in errors, "errors missing 'non_fields' key"

        # code must always be a non-empty string
        assert isinstance(errors["code"], str), (
            f"errors.code must be str, got {type(errors['code']).__name__}"
        )
        assert errors["code"] != "", "errors.code must not be empty string"

        # fields must be dict or None — never a list or string
        assert errors["fields"] is None or isinstance(errors["fields"], dict), (
            f"errors.fields must be dict or None, got {type(errors['fields']).__name__}"
        )

        # non_fields must be dict or None — never a list or string
        assert errors["non_fields"] is None or isinstance(errors["non_fields"], dict), (
            f"errors.non_fields must be dict or None, "
            f"got {type(errors['non_fields']).__name__}"
        )

        # When fields dict is present, each value must have message and code
        if errors["fields"] is not None:
            for field_name, field_error in errors["fields"].items():
                assert isinstance(field_error, dict), (
                    f"errors.fields.{field_name} must be dict, "
                    f"got {type(field_error).__name__}"
                )
                assert "message" in field_error, (
                    f"errors.fields.{field_name} missing 'message' key"
                )
                assert "code" in field_error, (
                    f"errors.fields.{field_name} missing 'code' key"
                )

        # When non_fields is present it must have message and code
        if errors["non_fields"] is not None:
            assert "message" in errors["non_fields"], (
                "errors.non_fields missing 'message' key"
            )
            assert "code" in errors["non_fields"], (
                "errors.non_fields missing 'code' key"
            )


# ─── Layer 1: _format_errors() Unit Tests ─────────────────────────────────────

@pytest.mark.unit
class TestFormatErrors:
    """
    Unit tests for _format_errors().

    NEW CONTRACT:
        _format_errors() now always returns a structured dict:
        {
            "code":       str,           # top-level category from status code
            "fields":     dict | None,   # field-level errors
            "non_fields": dict | None    # non-field / cross-field errors
        }

        Every field error is:
            {"message": str, "code": str}

        Every non_fields error is:
            {"message": str, "code": str}

    KEY CHANGE from old implementation:
        Old: returned raw strings/lists/dicts — three different shapes.
        New: always returns exactly one shape regardless of input type.
        This is what makes frontend logic possible instead of just display.

    DRF attaches ErrorDetail objects to every error it produces.
    ErrorDetail is a str subclass with an extra .code attribute.
    Old _format_errors threw that .code away silently.
    New _format_errors extracts it so frontend receives machine-readable codes.
    """

    # ── Dict input — field-level errors ──────────────────────────────────────

    def test_dict_field_error_produces_fields_dict(self):
        """
        Dict input with field errors must produce structured fields dict.

        DRF ValidationError with field dict is the most common error shape.
        Each field must map to {message, code} — not a plain string.

        Why this matters:
            Old: errors.email = "Enter a valid email."
                 Frontend can only display it.
            New: errors.fields.email = {message: "...", code: "email_invalid_format"}
                 Frontend can display it AND branch on the code.
        """
        data = {"email": [ErrorDetail("Enter a valid email address.", code="invalid")]}

        result = _format_errors(data, status_code=400)

        assert result["code"]   == ErrorCode.VALIDATION_ERROR
        assert result["non_fields"] is None
        assert result["fields"]["email"]["message"] == "Enter a valid email address."
        assert result["fields"]["email"]["code"]    == "invalid"

    def test_dict_custom_error_code_preserved(self):
        """
        Custom error codes on ErrorDetail must be preserved in output.

        This is the entire point of the new system.
        When a serializer raises with code=ErrorCode.EMAIL_ALREADY_EXISTS,
        that code must survive all the way to the frontend unchanged.

        Old system: code was silently discarded.
        New system: code flows through to errors.fields.email.code
        """
        data = {
            "email": [
                ErrorDetail(
                    "An account with this email already exists.",
                    code=ErrorCode.EMAIL_ALREADY_EXISTS,
                )
            ]
        }

        result = _format_errors(data, status_code=400)

        assert result["fields"]["email"]["code"] == ErrorCode.EMAIL_ALREADY_EXISTS

    def test_dict_multiple_fields_each_structured_independently(self):
        """
        Multiple fields must each produce independent {message, code} dicts.

        Each field is processed independently — errors on one field
        must not affect the structure of another field's output.
        """
        data = {
            "email":    [ErrorDetail("Email invalid.", code="email_invalid_format")],
            "password": [ErrorDetail("Too short.", code="password_too_weak")],
        }

        result = _format_errors(data, status_code=400)

        assert result["fields"]["email"]["code"]    == "email_invalid_format"
        assert result["fields"]["password"]["code"] == "password_too_weak"
        assert result["non_fields"] is None

    def test_dict_first_error_taken_when_multiple_on_same_field(self):
        """
        When a field has multiple ErrorDetail objects, only first is surfaced.

        DRF can produce multiple errors per field but surfacing all of them
        simultaneously is poor UX — fixing the first error usually resolves
        subsequent ones. Production standard is first-error-wins per field.
        """
        data = {
            "password": [
                ErrorDetail("Too short.", code="min_length"),
                ErrorDetail("Too common.", code="password_too_common"),
            ]
        }

        result = _format_errors(data, status_code=400)

        # First error wins
        assert result["fields"]["password"]["message"] == "Too short."
        assert result["fields"]["password"]["code"]    == "min_length"

    def test_dict_non_field_errors_go_to_non_fields_key(self):
        """
        non_field_errors from DRF must map to non_fields — not fields.

        DRF uses the key 'non_field_errors' for cross-field and
        authentication errors. Frontend needs these separated from
        field errors because they display differently (banner vs field highlight).

        Old: errors.non_field_errors = ["Please verify your email."]
             Frontend just showed it as text. No action possible.
        New: errors.non_fields = {message: "...", code: "email_not_verified"}
             Frontend sees code → renders message + "Resend email" button.
        """
        data = {
            "non_field_errors": [
                ErrorDetail(
                    "Please verify your email address before logging in.",
                    code=ErrorCode.EMAIL_NOT_VERIFIED,
                )
            ]
        }

        result = _format_errors(data, status_code=401)

        assert result["fields"]     is None
        assert result["non_fields"]["message"] == (
            "Please verify your email address before logging in."
        )
        assert result["non_fields"]["code"] == ErrorCode.EMAIL_NOT_VERIFIED

    def test_dict_mixed_field_and_non_field_errors(self):
        """
        Dict with both field errors and non_field_errors must split correctly.

        field errors    → result["fields"]
        non_field_errors → result["non_fields"]

        Both populated simultaneously, neither drops the other.
        """
        data = {
            "email": [ErrorDetail("Email required.", code="required")],
            "non_field_errors": [ErrorDetail("Account disabled.", code="account_disabled")],
        }

        result = _format_errors(data, status_code=400)

        assert result["fields"]["email"]["code"] == "required"
        assert result["non_fields"]["code"]      == "account_disabled"

    def test_dict_empty_produces_none_fields_and_none_non_fields(self):
        """
        Empty dict input must produce fields=None and non_fields=None.

        An empty dict means no errors of either type.
        Both must be None — not empty dicts — so frontend can do
        simple falsy checks: if (errors.fields) { ... }
        """
        result = _format_errors({}, status_code=400)

        assert result["code"]       == ErrorCode.VALIDATION_ERROR
        assert result["fields"]     is None
        assert result["non_fields"] is None

    def test_dict_plain_string_value_gets_error_fallback_code(self):
        """
        Plain string field values (no ErrorDetail) get fallback code 'error'.

        Some DRF exceptions produce plain strings instead of ErrorDetail.
        _format_errors must handle these gracefully with a fallback code
        rather than crashing or silently dropping the error.
        """
        data = {"detail": "Not found."}

        result = _format_errors(data, status_code=404)

        assert result["fields"]["detail"]["message"] == "Not found."
        assert result["fields"]["detail"]["code"]    == "error"

    # ── List input — top-level non-field errors ───────────────────────────────

    def test_list_single_error_goes_to_non_fields(self):
        """
        List input must produce non_fields with first item's message and code.

        DRF AuthenticationFailed and PermissionDenied produce list-wrapped
        error detail at the top level — not inside a dict keyed by field name.
        These are always non-field errors.
        """
        data = [
            ErrorDetail("Authentication credentials were not provided.", code="not_authenticated")
        ]

        result = _format_errors(data, status_code=401)

        assert result["fields"] is None
        assert result["non_fields"]["message"] == (
            "Authentication credentials were not provided."
        )
        assert result["non_fields"]["code"] == "not_authenticated"

    def test_list_custom_code_preserved(self):
        """Custom code on list ErrorDetail must survive to non_fields.code."""
        data = [ErrorDetail("Account suspended.", code=ErrorCode.ACCOUNT_DISABLED)]

        result = _format_errors(data, status_code=401)

        assert result["non_fields"]["code"] == ErrorCode.ACCOUNT_DISABLED

    def test_empty_list_produces_none_fields_and_none_non_fields(self):
        """Empty list produces fields=None and non_fields=None."""
        result = _format_errors([], status_code=400)

        assert result["fields"]     is None
        assert result["non_fields"] is None

    # ── String input ──────────────────────────────────────────────────────────

    def test_string_input_goes_to_non_fields(self):
        """
        Plain string input must produce non_fields with top-level code.

        DRF NotFound and similar exceptions can produce plain strings.
        These are non-field errors with the top-level category as code
        since there is no ErrorDetail to extract a specific code from.
        """
        result = _format_errors("Not found.", status_code=404)

        assert result["fields"]            is None
        assert result["non_fields"]["message"] == "Not found."
        assert result["non_fields"]["code"]    == ErrorCode.NOT_FOUND

    def test_empty_string_input_goes_to_non_fields(self):
        """Empty string input must go to non_fields without crashing."""
        result = _format_errors("", status_code=400)

        assert result["fields"]                is None
        assert result["non_fields"]["message"] == ""

    # ── Status code → top-level code mapping ─────────────────────────────────

    def test_status_400_produces_validation_error_code(self):
        """400 status must produce errors.code = 'validation_error'."""
        result = _format_errors({}, status_code=400)
        assert result["code"] == ErrorCode.VALIDATION_ERROR

    def test_status_401_produces_authentication_error_code(self):
        """401 status must produce errors.code = 'authentication_error'."""
        result = _format_errors([], status_code=401)
        assert result["code"] == ErrorCode.AUTHENTICATION_ERROR

    def test_status_403_produces_permission_error_code(self):
        """403 status must produce errors.code = 'permission_error'."""
        result = _format_errors([], status_code=403)
        assert result["code"] == ErrorCode.PERMISSION_ERROR

    def test_status_404_produces_not_found_code(self):
        """404 status must produce errors.code = 'not_found'."""
        result = _format_errors("Not found.", status_code=404)
        assert result["code"] == ErrorCode.NOT_FOUND

    def test_status_429_produces_rate_limit_code(self):
        """429 status must produce errors.code = 'rate_limit_exceeded'."""
        result = _format_errors([], status_code=429)
        assert result["code"] == ErrorCode.RATE_LIMIT_EXCEEDED

    def test_status_500_produces_server_error_code(self):
        """500 status must produce errors.code = 'server_error'."""
        result = _format_errors("Unexpected error.", status_code=500)
        assert result["code"] == ErrorCode.SERVER_ERROR

    # ── Output shape guarantee ────────────────────────────────────────────────

    def test_output_always_has_three_keys_regardless_of_input(self):
        """
        Output must always have exactly code, fields, non_fields keys.

        This is the core guarantee of the new system.
        Frontend never needs to check 'does errors have a fields key?'
        or 'is errors a string or dict?' — it always has the same shape.

        Old system: frontend had to handle str / list / dict differently.
        New system: always exactly one shape. Frontend logic is trivial.
        """
        inputs = [
            ({"email": [ErrorDetail("e.", code="invalid")]}, 400),
            ([ErrorDetail("e.", code="invalid")],            401),
            ("Not found.",                                   404),
            ({},                                             400),
            ([],                                             400),
        ]
        for data, status_code in inputs:
            result = _format_errors(data, status_code)
            assert "code"       in result, f"'code' missing for input {data!r}"
            assert "fields"     in result, f"'fields' missing for input {data!r}"
            assert "non_fields" in result, f"'non_fields' missing for input {data!r}"


# ─── Layer 2: _status_to_message() Unit Tests ─────────────────────────────────

@pytest.mark.unit
class TestStatusToMessage:
    """
    Unit tests for _status_to_message().

    UNCHANGED from previous implementation.
    Function signature and output are identical.
    Every test here passes without modification.
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
        result = _status_to_message(status_code)
        assert result == expected_fragment, (
            f"Status {status_code}: expected {expected_fragment!r}, got {result!r}"
        )

    def test_unknown_status_code_returns_fallback(self):
        result = _status_to_message(418)
        assert result == "Request failed."

    def test_returns_string_for_all_known_codes(self):
        known_codes = [400, 401, 403, 404, 405, 429, 500]
        for code in known_codes:
            result = _status_to_message(code)
            assert isinstance(result, str), (
                f"Expected str for status {code}, got {type(result).__name__}"
            )

    def test_fallback_is_string(self):
        result = _status_to_message(999)
        assert isinstance(result, str)


# ─── Layer 3: custom_exception_handler() Integration Tests ────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestCustomExceptionHandlerDirect:
    """
    Tests for custom_exception_handler() called directly.

    Most tests pass unchanged because assert_error_envelope() is now
    stricter and validates the new errors sub-structure automatically.

    Only tests that inspected the OLD flat errors shape needed updating.
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

    # ── Error field content — UPDATED for new shape ───────────────────────────

    def test_validation_error_field_in_errors_fields(self):
        """
        Field-level validation errors must appear in errors.fields.

        OLD: assert "email" in response.data["errors"]
        NEW: assert "email" in response.data["errors"]["fields"]

        Why changed:
            errors is no longer a flat dict of field names.
            errors is now {code, fields, non_fields}.
            Field errors live inside errors.fields.
        """
        request = _make_request()
        exc = ValidationError({"email": ["Enter a valid email address."]})

        response = custom_exception_handler(exc, {"request": request})

        assert response.data["errors"]["fields"] is not None
        assert "email" in response.data["errors"]["fields"]

    def test_validation_field_error_has_message_and_code(self):
        """
        Each field error must be a dict with message and code keys.

        OLD: assert isinstance(response.data["errors"]["email"], str)
        NEW: assert isinstance(response.data["errors"]["fields"]["email"], dict)
             and it has 'message' and 'code' keys.

        Why changed:
            Field errors are no longer plain strings.
            They are structured {message, code} dicts so frontend
            can branch on code while displaying message.
        """
        request = _make_request()
        exc = ValidationError({"email": ["Enter a valid email address."]})

        response = custom_exception_handler(exc, {"request": request})

        field_error = response.data["errors"]["fields"]["email"]
        assert isinstance(field_error, dict)
        assert "message" in field_error
        assert "code"    in field_error
        assert isinstance(field_error["message"], str)
        assert isinstance(field_error["code"],    str)

    def test_validation_multiple_field_errors_first_wins(self):
        """
        Multiple errors on same field — first error surfaced in message/code.

        OLD: assert isinstance(response.data["errors"]["password"], list)
             assert len(response.data["errors"]["password"]) == 2
        NEW: first error wins — result is always a single {message, code} dict.

        Why changed:
            Production UX standard is first-error-wins per field.
            Showing multiple errors simultaneously overwhelms users.
            Fix the first, resubmit, next error surfaces if still present.
        """
        request = _make_request()
        exc = ValidationError({"password": ["Too short.", "Too common."]})

        response = custom_exception_handler(exc, {"request": request})

        field_error = response.data["errors"]["fields"]["password"]
        assert isinstance(field_error, dict)
        assert field_error["message"] == "Too short."

    def test_non_field_error_goes_to_non_fields_key(self):
        """
        non_field_errors from DRF must appear in errors.non_fields.

        This is the key change that enables the login email_not_verified
        use case — frontend reads errors.non_fields.code and renders
        the appropriate UI (message + resend button, not just message).
        """
        request = _make_request()
        exc = ValidationError(
            {"non_field_errors": ["Please verify your email address."]}
        )

        response = custom_exception_handler(exc, {"request": request})

        assert response.data["errors"]["fields"]     is None
        assert response.data["errors"]["non_fields"] is not None
        assert "message" in response.data["errors"]["non_fields"]
        assert "code"    in response.data["errors"]["non_fields"]

    def test_errors_top_level_code_matches_status(self):
        """
        errors.code must reflect the HTTP status category.

        Frontend can switch on errors.code for top-level handling
        before even inspecting fields or non_fields.
        """
        request = _make_request()

        cases = [
            (ValidationError({"f": ["e"]}), 400, ErrorCode.VALIDATION_ERROR),
            (NotFound(),                    404, ErrorCode.NOT_FOUND),
            (PermissionDenied(),            403, ErrorCode.PERMISSION_ERROR),
            (NotAuthenticated(),            401, ErrorCode.AUTHENTICATION_ERROR),
        ]

        for exc, expected_status, expected_code in cases:
            response = custom_exception_handler(exc, {"request": request})
            assert response.status_code == expected_status
            assert response.data["errors"]["code"] == expected_code, (
                f"Expected {expected_code!r} for status {expected_status}, "
                f"got {response.data['errors']['code']!r}"
            )

    # ── Message content — UNCHANGED ───────────────────────────────────────────

    def test_400_message_is_correct(self):
        request = _make_request()
        exc = ValidationError({"field": ["error"]})
        response = custom_exception_handler(exc, {"request": request})
        assert response.data["message"] == "Invalid request data."

    def test_404_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(NotFound(), {"request": request})
        assert response.data["message"] == "The requested resource was not found."

    def test_401_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(NotAuthenticated(), {"request": request})
        assert response.data["message"] == "Authentication required."

    def test_403_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(PermissionDenied(), {"request": request})
        assert response.data["message"] == (
            "You do not have permission to perform this action."
        )

    def test_500_message_is_correct(self):
        request = _make_request()
        response = custom_exception_handler(RuntimeError("boom"), {"request": request})
        assert response.data["message"] == (
            "An unexpected error occurred. Please try again later."
        )

    # ── Production safety — UPDATED for new shape ────────────────────────────

    @override_settings(DEBUG=False)
    def test_unhandled_exception_errors_never_none_in_production(self):
        """
        In production (DEBUG=False), errors is a structured dict with
        server_error code and non_fields=None to avoid leaking internals.

        OLD: assert response.data["errors"] is None
        NEW: errors is always a structured dict.
             non_fields is None in production to avoid leaking exception detail.
             errors.code tells frontend it is a server error.

        Why changed:
            errors=None in old system was blunt — frontend could not even
            read a category code. New system: errors.code="server_error"
            always present, but non_fields.message is None in production
            so no internal details leak.
        """
        request = _make_request()
        exc = RuntimeError("SELECT * FROM secret_table WHERE password=...")

        response = custom_exception_handler(exc, {"request": request})

        errors = response.data["errors"]
        assert errors is not None,                      "errors must never be None — use structured shape"
        assert errors["code"]       == ErrorCode.SERVER_ERROR
        assert errors["fields"]     is None
        assert errors["non_fields"] is None, (
            "Production 500 must not expose exception detail in non_fields"
        )

    @override_settings(DEBUG=True)
    def test_unhandled_exception_non_fields_exposed_in_debug(self):
        """
        In DEBUG mode, exception detail appears in errors.non_fields.message.

        OLD: assert response.data["errors"] == "Detailed debug error message"
        NEW: assert response.data["errors"]["non_fields"]["message"] == "..."

        Why changed:
            Even in DEBUG the shape is consistent.
            Frontend reads errors.non_fields.message — same path always.
            Only the content differs between DEBUG and production.
        """
        request = _make_request()
        exc = RuntimeError("Detailed debug error message")

        response = custom_exception_handler(exc, {"request": request})

        errors = response.data["errors"]
        assert errors["code"] == ErrorCode.SERVER_ERROR
        assert errors["non_fields"]["message"] == "Detailed debug error message"
        assert errors["non_fields"]["code"]    == ErrorCode.SERVER_ERROR

    def test_no_request_in_context_handled_gracefully(self):
        """Missing request in context must not crash the handler."""
        exc = NotFound()
        response = custom_exception_handler(exc, {})

        assert response is not None
        assert response.status_code == 404

    # ── request_id in meta — UNCHANGED ────────────────────────────────────────

    def test_request_id_injected_into_meta_when_present(self):
        request = _make_request()
        request.id = "test-correlation-id-abc123"

        response = custom_exception_handler(NotFound(), {"request": request})

        assert response.data["meta"]["request_id"] == "test-correlation-id-abc123"

    def test_request_id_is_none_when_not_on_request(self):
        request = _make_request()

        response = custom_exception_handler(NotFound(), {"request": request})

        assert "meta"       in response.data
        assert "request_id" in response.data["meta"]
        assert response.data["meta"]["request_id"] is None

    def test_meta_present_on_all_error_types(self):
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


# ─── Layer 3b: HTTP Stack Integration Tests ───────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestCustomExceptionHandlerHTTP:
    """
    Tests custom_exception_handler through the full HTTP stack.

    Most tests pass unchanged.
    Only the field-inspection test needed updating for the new shape.
    """

    @override_settings(ROOT_URLCONF=__name__)
    def test_unhandled_exception_returns_500_envelope_via_http(self, api_client):
        """Full stack: unhandled RuntimeError → 500 standard envelope."""
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
    def test_validation_error_field_in_errors_fields_via_http(self, api_client):
        """
        Full stack: field errors must be in errors.fields.email via HTTP.

        OLD: assert "email" in response.data["errors"]
        NEW: assert "email" in response.data["errors"]["fields"]
        """
        response = api_client.get("/test/validation-error/")

        assert response.data["errors"]["fields"] is not None
        assert "email" in response.data["errors"]["fields"]

    @override_settings(ROOT_URLCONF=__name__)
    def test_request_id_in_meta_on_error_via_http(self, api_client):
        """Full stack: meta.request_id must be present on error responses."""
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

    @override_settings(ROOT_URLCONF=__name__)
    def test_errors_code_present_on_all_error_responses_via_http(self, api_client):
        """
        Full stack: errors.code must be present on every error response.

        NEW TEST — validates the new contract end-to-end through HTTP.
        If errors.code is missing, frontend cannot do category-level switching.
        """
        error_urls = [
            "/test/unhandled-error/",
            "/test/validation-error/",
        ]
        for url in error_urls:
            response = api_client.get(url)
            errors = response.data.get("errors")
            if errors is not None:
                assert "code" in errors, (
                    f"errors.code missing on response from {url}"
                )


# ─── Layer 4: Monitor Registry Tests — UNCHANGED ──────────────────────────────

@pytest.mark.unit
class TestMonitorRegistry:
    """
    Monitor registry tests.
    COMPLETELY UNCHANGED — no dependency on error shape whatsoever.
    """

    def setup_method(self):
        self._original_monitors = list(_monitors)

    def teardown_method(self):
        _monitors.clear()
        _monitors.extend(self._original_monitors)

    def test_register_monitor_adds_callable(self):
        initial_count = len(_monitors)

        def my_monitor(exc): pass

        register_monitor(my_monitor)
        assert len(_monitors) == initial_count + 1
        assert my_monitor in _monitors

    def test_monitor_is_called_on_notify(self):
        called_with = []

        def capturing_monitor(exc):
            called_with.append(exc)

        register_monitor(capturing_monitor)
        test_exc = RuntimeError("test error")
        _notify_monitors(test_exc)

        assert len(called_with) == 1
        assert called_with[0] is test_exc

    def test_monitor_receives_correct_exception(self):
        received = []

        def capture(exc):
            received.append(exc)

        register_monitor(capture)
        exc = ValueError("specific error")
        _notify_monitors(exc)

        assert received[0] is exc

    def test_multiple_monitors_all_called(self):
        call_counts = {"first": 0, "second": 0, "third": 0}

        register_monitor(lambda exc: call_counts.__setitem__("first",  call_counts["first"]  + 1))
        register_monitor(lambda exc: call_counts.__setitem__("second", call_counts["second"] + 1))
        register_monitor(lambda exc: call_counts.__setitem__("third",  call_counts["third"]  + 1))

        _notify_monitors(RuntimeError("boom"))

        assert call_counts["first"]  == 1
        assert call_counts["second"] == 1
        assert call_counts["third"]  == 1

    def test_broken_monitor_does_not_prevent_other_monitors_from_running(self):
        second_called = []

        def broken_monitor(exc): raise RuntimeError("Monitor itself is broken")
        def working_monitor(exc): second_called.append(exc)

        register_monitor(broken_monitor)
        register_monitor(working_monitor)

        _notify_monitors(RuntimeError("original error"))

        assert len(second_called) == 1

    def test_broken_monitor_does_not_raise_to_caller(self):
        def always_crashes(exc): raise RuntimeError("I always crash")

        register_monitor(always_crashes)

        try:
            _notify_monitors(RuntimeError("original"))
        except Exception as e:
            pytest.fail(f"_notify_monitors raised an exception to caller: {e}")

    def test_monitors_not_called_for_4xx_exceptions(self):
        monitor_called = []

        def monitor(exc): monitor_called.append(exc)

        register_monitor(monitor)
        request = _make_request()

        custom_exception_handler(NotFound(),                    {"request": request})
        custom_exception_handler(ValidationError({"f": ["e"]}), {"request": request})
        custom_exception_handler(PermissionDenied(),            {"request": request})

        assert len(monitor_called) == 0

    def test_monitors_called_for_unhandled_exception(self):
        monitor_called = []

        def monitor(exc): monitor_called.append(exc)

        register_monitor(monitor)
        request = _make_request()

        custom_exception_handler(RuntimeError("real unexpected error"), {"request": request})

        assert len(monitor_called) == 1