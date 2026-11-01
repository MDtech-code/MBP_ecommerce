"""Foundation canaries — the invariants that must hold no matter what else changes.

These are deliberately NOT behaviour tests of a feature. Each one asserts a
property that the whole project depends on, so it only fails if something is
genuinely broken:

    * all 17 apps still load and every AppConfig.ready() still runs
    * the root URLconf still imports and still exposes its documented routes
    * the error-code registry is still a valid public contract
    * the shared error envelope still has the shape the frontend parses
    * error codes are still derived from HTTP status the same way

They need no database, no network, no fixtures and no ordering, so they stay
stable while the application grows. Real feature tests belong next to the app
they cover (e.g. apps/orders/tests/), not here.

Marked `unit`: see pytest.ini.
"""

import json
import re

import pytest
from django.apps import apps
from django.conf import settings
from django.urls import get_resolver, reverse

from apps.core.api.exceptions import _status_to_error_code, custom_exception_handler
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

pytestmark = pytest.mark.unit


# ─── Apps ─────────────────────────────────────────────────────────────────────

def _project_apps() -> list[str]:
    return list(settings.PROJECT_APPS)


@pytest.mark.parametrize("app_name", _project_apps())
def test_every_project_app_is_loaded(app_name):
    """settings.PROJECT_APPS is the project's own list of installed apps.

    A failure here means an app cannot be imported — a broken models.py,
    a broken AppConfig.ready(), or a missing package.
    """
    assert apps.is_installed(app_name), f"{app_name} is in PROJECT_APPS but not loaded"


def test_project_app_list_is_not_empty():
    """Guards against the parametrized test above silently collecting nothing."""
    assert len(_project_apps()) >= 10


# ─── URL wiring ───────────────────────────────────────────────────────────────

def test_root_urlconf_exposes_every_documented_namespace():
    """Each app that is mounted in config/urls.py must publish its namespace."""
    mounted = {
        "accounts", "products", "cart", "orders", "logistics",
        "reviews", "returns", "payments", "wishlist", "contact",
    }
    resolver = get_resolver()
    assert mounted.issubset(set(resolver.namespace_dict))


@pytest.mark.parametrize("route_name", ["csrf", "schema", "swagger-ui", "redoc"])
def test_documented_top_level_routes_reverse(route_name):
    """Proves the URLconf imported and these views are wired, without HTTP."""
    assert reverse(route_name).startswith("/api/")


# ─── Error-code registry ──────────────────────────────────────────────────────

# Values that violate the registry's own "snake_case" rule today. Kept as an
# explicit, visible allowlist so the rule is still enforced for the other 79
# codes. Fixing the value lets the entry be deleted — that is the whole point.
KNOWN_NON_SNAKE_CASE_CODES = {"SOCIAL_AUTH_FAILED"}


def _error_codes() -> dict[str, str]:
    return {
        name: value
        for name, value in vars(ErrorCode).items()
        if not name.startswith("_") and isinstance(value, str)
    }


def test_error_code_values_are_unique():
    """Two codes sharing a value would make the frontend unable to branch."""
    codes = _error_codes()
    seen: dict[str, str] = {}
    duplicates: dict[str, list[str]] = {}
    for name, value in codes.items():
        if value in seen:
            duplicates.setdefault(value, [seen[value]]).append(name)
        else:
            seen[value] = name
    assert not duplicates, f"duplicate ErrorCode values: {duplicates}"


SNAKE_CASE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


def test_error_code_values_are_snake_case():
    """The registry documents its values as snake_case 'public API' strings."""
    offenders = {
        name: value
        for name, value in _error_codes().items()
        if name not in KNOWN_NON_SNAKE_CASE_CODES and not SNAKE_CASE.fullmatch(value)
    }
    assert not offenders, f"ErrorCode values must be snake_case: {offenders}"


def test_known_deviations_still_exist():
    """Stops the allowlist from rotting into a list of dead names."""
    missing = KNOWN_NON_SNAKE_CASE_CODES - set(_error_codes())
    assert not missing, f"allowlisted codes no longer exist: {missing}"


# ─── HTTP status → error code mapping ─────────────────────────────────────────

@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (400, ErrorCode.VALIDATION_ERROR),
        (401, ErrorCode.AUTHENTICATION_ERROR),
        (403, ErrorCode.PERMISSION_ERROR),
        (404, ErrorCode.NOT_FOUND),
        (405, ErrorCode.METHOD_NOT_ALLOWED),
        (409, ErrorCode.CONFLICT_ERROR),
        (422, ErrorCode.VALIDATION_ERROR),
        (429, ErrorCode.RATE_LIMIT_EXCEEDED),
        (500, ErrorCode.SERVER_ERROR),
        (503, ErrorCode.SERVER_ERROR),
        (418, ErrorCode.SERVER_ERROR),
    ],
)
def test_http_status_maps_to_a_stable_error_code(status_code, expected_code):
    assert _status_to_error_code(status_code) == expected_code


# ─── The response envelope the frontend parses ────────────────────────────────

def test_domain_error_response_uses_the_shared_envelope():
    """Locks the contract shared/api/transformers.js depends on."""
    exc = DomainError(
        "This order cannot be cancelled.",
        code=ErrorCode.CONFLICT_ERROR,
        status_code=409,
    )

    response = custom_exception_handler(exc, {})

    assert response.status_code == 409
    body = response.data
    assert set(body) == {"success", "message", "data", "errors", "meta"}
    assert body["success"] is False
    assert body["data"] is None
    assert body["errors"]["code"] == ErrorCode.CONFLICT_ERROR
    assert body["errors"]["fields"] is None
    assert body["errors"]["non_fields"] == {
        "category": "domain",
        "message": "This order cannot be cancelled.",
        "code": ErrorCode.CONFLICT_ERROR,
        "extra": None,
    }
    assert body["meta"] == {"request_id": None}


def test_internal_context_is_never_serialized_into_a_response():
    """The module documents this as a security invariant, not a convention."""
    exc = DomainError(
        "Something went wrong.",
        code=ErrorCode.VALIDATION_ERROR,
        status_code=400,
        internal={"sql": "SELECT secret FROM accounts_user", "password_hash": "pbkdf2_sha256$..."},
    )

    response = custom_exception_handler(exc, {})
    payload = json.dumps(response.data, default=str)

    assert "SELECT secret" not in payload
    assert "pbkdf2_sha256" not in payload


def test_domain_error_rejects_an_out_of_range_status_code():
    """DomainError is restricted to 4xx codes; 500 must be InfrastructureError."""
    with pytest.raises(ValueError):
        DomainError("Server exploded.", status_code=500)
