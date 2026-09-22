"""Reusable domain/transport boundary, independent of any account workflow."""
from types import SimpleNamespace

import pytest
from rest_framework.exceptions import Throttled

from apps.core.api.exceptions import build_envelope_from_exception, custom_exception_handler, _format_drf_errors
from apps.core.api.views import BaseAPIView
from apps.core.exceptions import DomainError, InfrastructureError, ConflictError


@pytest.mark.unit
@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422])
def test_domain_statuses_preserve_safe_context_but_never_internal(status):
    error = DomainError("Safe", code="business_rule", status_code=status,
                        client_extra={"retry": True}, internal={"secret": "never-public"})
    envelope = build_envelope_from_exception(error)
    assert envelope["fields"] is None
    assert envelope["non_fields"] == {
        "category": "domain", "message": "Safe", "code": "business_rule",
        "extra": {"retry": True},
    }
    assert "never-public" not in str(envelope)


@pytest.mark.unit
@pytest.mark.parametrize("status", [200, 302, 429, 500, 503])
def test_domain_error_cannot_impersonate_transport_or_infrastructure(status):
    with pytest.raises(ValueError):
        DomainError("Wrong boundary", status_code=status)


@pytest.mark.unit
def test_direct_and_global_domain_responses_have_same_error_contract():
    request = SimpleNamespace(id="request-123")
    view = BaseAPIView()
    view.request = request
    error = ConflictError("Already exists", internal={"sql": "private"})
    direct = view.app_error_response(exc=error)
    handled = custom_exception_handler(error, {"request": request})
    assert direct.status_code == handled.status_code == 409
    assert direct.data["errors"] == handled.data["errors"]
    assert direct.data["meta"] == handled.data["meta"] == {"request_id": "request-123"}
    assert "private" not in str(handled.data)


@pytest.mark.unit
def test_infrastructure_error_notifies_without_exposing_internal(mocker):
    notify = mocker.patch("apps.core.api.exceptions._notify_monitors")
    error = InfrastructureError("Temporarily unavailable", internal={"password": "secret"})
    response = custom_exception_handler(error, {})
    assert response.status_code == 503
    assert response.data["errors"]["non_fields"]["category"] == "system"
    assert "secret" not in str(response.data)
    notify.assert_called_once_with(error)


@pytest.mark.unit
def test_unexpected_error_is_safe_outside_debug(settings):
    settings.DEBUG = False
    response = custom_exception_handler(RuntimeError("private connection string"), {})
    assert response.status_code == 500
    assert "private connection string" not in str(response.data)
    assert response.data["errors"]["non_fields"]["category"] == "unexpected"


@pytest.mark.unit
def test_throttle_headers_and_structured_metadata_survive_handler():
    request = SimpleNamespace(id="limited", _rate_limit_info={
        "limit": 2, "remaining": 0, "reset_at": 1704067260,
    })
    response = custom_exception_handler(Throttled(wait=60), {"request": request})
    assert response.status_code == 429
    assert response["Retry-After"] == "60"
    assert response.data["meta"] == {
        "request_id": "limited",
        "rateLimit": {"limit": 2, "remaining": 0, "resetAt": "2024-01-01T00:01:00+00:00"},
    }


@pytest.mark.unit
def test_response_metadata_keeps_caller_fields():
    view = BaseAPIView()
    view.request = SimpleNamespace(id="request-123", _rate_limit_info={
        "limit": 5, "remaining": 4, "reset_at": 1704067260,
    })
    response = view.created_response(meta={"custom": "kept"})
    assert response.status_code == 201
    assert response.data["data"] is None
    assert response.data["meta"]["custom"] == "kept"
    assert response.data["meta"]["request_id"] == "request-123"
    assert response.data["meta"]["rateLimit"]["remaining"] == 4


@pytest.mark.unit
def test_drf_detail_is_a_non_field_error_not_an_input_field():
    envelope = _format_drf_errors({"detail": "Not found."}, 404)
    assert envelope["fields"] is None
    assert envelope["non_fields"]["message"] == "Not found."
    assert envelope["non_fields"]["code"] == "invalid"
