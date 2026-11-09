"""
apps/core/api/exceptions.py
────────────────────────────
Global DRF exception handler — HTTP transport layer only.

RESPONSIBILITY
──────────────
This module's sole job is mapping exceptions to HTTP responses.It contains no business logic.



DEPENDENCY DIRECTION
────────────────────
    apps.core.exceptions          (BaseAppError and its subclasses)
         ↑
    apps.core.api.exceptions      (this file — maps them to HTTP responses)

ERROR ENVELOPE 
───────────────────────
{
    "success":  false,
    "message":  "<safe human string>",
    "data":     null,
    "errors": {
        "code":       "<top-level ErrorCode>",
        "fields":     { "<field>": {"message": "...", "code": "..."} } | null,
        "non_fields": {
            "category": "domain" | "system" | "validation" | "request" | "unexpected",
            "message":  "...",
            "code":     "...",
            "extra":    {...} | null   ← public DRF details or client_extra, never internal
        } | null
    },
    "meta": { "request_id": "..." }
}

SECURITY INVARIANT
──────────────────
exc.internal is never serialized into any response, in any branch.
It is only ever passed to the logger, inside custom_exception_handler.
build_envelope_from_exception() calls exc.to_envelope(), and
BaseAppError.to_envelope() does not expose internal — so this invariant
is enforced by the exception class itself, not repeated at each call site.

LOGGING POLICY
──────────────
All logging lives in custom_exception_handler, not in builders. Builders
are pure functions: input in, dict out, no side effects. This guarantees
one log entry per exception and one monitor call per exception.

  BaseAppError, notify=False   → WARNING, no traceback
  BaseAppError, notify=True    → ERROR + traceback, monitors notified
  DRF-native 4xx               → WARNING, no traceback
  DRF-native 5xx                → ERROR + traceback, monitors notified
  Unhandled exception           → ERROR + traceback, monitors notified
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from django.conf import settings
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import exception_handler

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import BaseAppError
from datetime import datetime, timezone as dt_timezone

logger = logging.getLogger(__name__)


# ─── Monitoring registry ──────────────────────────────────────────────────────

_monitors: list[Callable[[Exception], None]] = []


def register_monitor(fn: Callable[[Exception], None]) -> None:
    """
    Register a monitoring backend (e.g. Sentry, PagerDuty) to be called
    whenever an exception's notify flag is True, or whenever a genuinely
    unhandled exception reaches this handler.
    """
    _monitors.append(fn)


def _notify_monitors(exc: Exception) -> None:
    for monitor in _monitors:
        try:
            monitor(exc)
        except Exception as monitor_exc:
            logger.error("Monitor failed: %s", monitor_exc, exc_info=True)




def build_envelope_from_exception(exc: BaseAppError) -> dict[str, Any]:

    """Build the full errors envelope ({code, fields, non_fields}) for any BaseAppError instance."""
    return {
        "code": _status_to_error_code(exc.status_code),
        "fields": None,
        "non_fields": exc.to_envelope(),
    }


#! ─── non Field-error helpers  ─────────────────────────────────────────────

def _non_fields_error(detail: Any, *, category: str) -> dict[str, Any]:

    if isinstance(detail, ErrorDetail):
        return {
            "category": category,
            "message": str(detail),
            "code": str(detail.code) if detail.code else "invalid",
            "extra": None,
        }
    return {
        "category": category,
        "message": str(detail),
        "code": "invalid",
        "extra": None,
    }


def _non_fields_unexpected(exc: Exception, *, status_code: int) -> dict[str, Any]:
    
    return {
        "category": "unexpected",
        "message": str(exc) if settings.DEBUG else _status_to_message(status_code),
        "code": ErrorCode.SERVER_ERROR,
        "extra": None,
    }


#! ─── error detail  helpers  ─────────────────────────────────────────────

def _extract_error_detail(detail: Any) -> dict[str, str]:
    
    if isinstance(detail, ErrorDetail):
        return {
            "message": str(detail),
            "code": str(detail.code) if detail.code else "error",
        }
    return {"message": str(detail), "code": "error"}



def _resolve_single(value: Any) -> dict[str, Any]:
    """Resolve one field's error value without discarding extra messages.

    The first message stays in message/code so existing clients keep working.
    When DRF supplies more than one message for the same field, every message
    is also exposed under details instead of being silently dropped.
    """
    if isinstance(value, list) and value:
        resolved = _extract_error_detail(value[0])
        if len(value) > 1:
            resolved["details"] = [_extract_error_detail(item) for item in value]
        return resolved
    return _extract_error_detail(value)


def _resolve_non_field(value: Any, *, category: str) -> dict[str, Any]:
    """Resolve non-field errors, preserving every message DRF supplied.

    extra stays None for a single message. Multiple messages mirror the
    general formatter's contract by listing them under extra.messages.
    """
    if isinstance(value, list) and value:
        resolved = _non_fields_error(value[0], category=category)
        if len(value) > 1:
            resolved["extra"] = {
                "messages": [_extract_error_detail(item) for item in value]
            }
        return resolved
    return _non_fields_error(value, category=category)


#! ─── DRF error normalizer  ────────────────────────────────────────────

def _format_drf_errors(
    data: Any,
    status_code: int,
    *,
    category: str = "validation",
) -> dict[str, Any]:
    """Choose the interpretation using the category selected by the caller.

    The default preserves serializer-error handling in BaseAPIView.error_response().
    Other DRF errors must not interpret public response metadata as input fields.
    """
    if category == "validation":
        return _format_validation_errors(data, status_code)
    return _format_general_error(data, status_code, category=category)


def _format_validation_errors(data: Any, status_code: int) -> dict[str, Any]:
    """Preserve the first-message policy while keeping every reported message."""
    top_level_code = _status_to_error_code(status_code)
    fields: dict[str, Any] = {}
    non_fields: dict[str, Any] | None = None

    if isinstance(data, dict):
        for field, value in data.items():
            if field == api_settings.NON_FIELD_ERRORS_KEY:
                non_fields = _resolve_non_field(value, category="validation")
            else:
                fields[field] = _resolve_single(value)

    elif isinstance(data, list) and data:
        non_fields = _resolve_non_field(data, category="validation")

    elif isinstance(data, str):
        non_fields = {
            "category": "validation",
            "message": data,
            "code": top_level_code,
            "extra": None,
        }

    return {
        "code": top_level_code,
        "fields": fields if fields else None,
        "non_fields": non_fields,
    }


def _format_general_error(
    data: Any,
    status_code: int,
    *,
    category: str,
) -> dict[str, Any]:
    """Format DRF's public error body without applying serializer-field rules.

    Additional public keys retain their structure under extra. A structured detail
    value is retained under extra.detail with a status-based message. No exception
    attributes are inspected, and the input body is not mutated.
    """
    top_level_code = _status_to_error_code(status_code)
    extra: dict[str, Any] = {}

    if isinstance(data, dict):
        detail = data.get("detail")
        explicit_code = data.get("code")
        extra = {
            key: value
            for key, value in data.items()
            if key not in ("detail", "code")
        }
    else:
        detail = data
        explicit_code = None

    if isinstance(detail, str):
        non_fields = _non_fields_error(detail, category=category)
    else:
        non_fields = {
            "category": category,
            "message": _status_to_message(status_code),
            "code": top_level_code,
            "extra": None,
        }
        if detail is not None:
            extra["detail"] = detail

    if isinstance(explicit_code, str) and explicit_code:
        non_fields["code"] = str(explicit_code)
    elif isinstance(data, dict) and "code" in data:
        # A non-string code is public data, not a machine-readable reason code.
        extra["code"] = explicit_code

    non_fields["extra"] = extra if extra else None
    return {
        "code": top_level_code,
        "fields": None,
        "non_fields": non_fields,
    }


# ─── HTTP mapping helpers  ────────────────────────────────────────────

def _status_to_error_code(status_code: int) -> str:
    return {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTHENTICATION_ERROR,
        403: ErrorCode.PERMISSION_ERROR,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        409: ErrorCode.CONFLICT_ERROR,
        422: ErrorCode.VALIDATION_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.SERVER_ERROR,
        503: ErrorCode.SERVER_ERROR,
    }.get(status_code, ErrorCode.SERVER_ERROR)


def _status_to_message(status_code: int) -> str:
    
    return {
        400: "Invalid request data.",
        401: "Authentication required.",
        403: "You do not have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        409: "This action conflicts with the current state of the resource.",
        422: "Invalid request data.",
        429: "Too many requests. Please slow down.",
        500: "An unexpected error occurred. Please try again later.",
        503: "The service is temporarily unavailable. Please try again shortly.",
    }.get(status_code, "Request failed.")


# ─── Response builder  ────────────────────────────────────────────────
def _build_response(
    *,
    status_code: int,
    errors: dict[str, Any],
    request_id: str | None,
    request: Request | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    meta: dict[str, Any] = {"request_id": request_id}

    rate_info = getattr(request, "_rate_limit_info", None) if request else None
    if rate_info:
        meta["rateLimit"] = {
            "limit": rate_info["limit"],
            "remaining": rate_info["remaining"],
            "resetAt": datetime.fromtimestamp(rate_info["reset_at"], tz=dt_timezone.utc).isoformat(),
        }

    response = Response(
        {"success": False, "message": _status_to_message(status_code), "data": None, "errors": errors, "meta": meta},
        status=status_code,
    )
    if headers:
        for key, value in headers.items():
            response[key] = value
    return response


# ─── Main handler ─────────────────────────────────────────────────────────────

def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    
    request: Request | None = context.get("request")
    request_id: str | None = getattr(request, "id", None)

    # ── 1. Any BaseAppError subclass ────────────────────────────────────────
    if isinstance(exc, BaseAppError):
        if exc.internal:
            logger.log(
                logging.ERROR if exc.notify else logging.DEBUG,
                "%s internal context [%s]: %s",
                type(exc).__name__,
                exc.code,
                exc.internal,
                exc_info=exc.notify,
                extra={"request_id": request_id},
            )

        if exc.notify:
            _notify_monitors(exc)
            logger.error(
                "%s: %s [code=%s, status=%s]",
                type(exc).__name__,
                exc.message,
                exc.code,
                exc.status_code,
                exc_info=True,
                extra={"request_id": request_id},
            )
        else:
            logger.warning(
                "%s: %s [code=%s, status=%s]",
                type(exc).__name__,
                exc.message,
                exc.code,
                exc.status_code,
                extra={"request_id": request_id},
            )

        return _build_response(
            status_code=exc.status_code,
            errors=build_envelope_from_exception(exc),
            request_id=request_id,
        )

    # ── 2. DRF-recognized exception ─────────────────────────────────────────
    response = exception_handler(exc, context)

    if response is not None:
        # HTTP 400 alone cannot distinguish validation from malformed requests.
        if isinstance(exc, ValidationError):
            category = "validation"
        elif response.status_code >= 500:
            category = "system"
        else:
            category = "request"

        if response.status_code >= 500:
            _notify_monitors(exc)
            logger.error(
                "Server error via DRF handler [%s] %s",
                response.status_code,
                type(exc).__name__,
                exc_info=True,
                extra={"request_id": request_id},
            )
        else:
            logger.warning(
                "Client error handled [%s] %s",
                response.status_code,
                type(exc).__name__,
                extra={"request_id": request_id},
            )
        
        return _build_response(
            status_code=response.status_code,
            errors=_format_drf_errors(
                response.data, response.status_code, category=category
            ),
            request_id=request_id,
            request=request,
            headers=dict(response.items()),
        )

    # ── 3. Unhandled exception ──────────────────────────────────────────────
    _notify_monitors(exc)
    logger.error(
        "Unhandled exception [%s]",
        type(exc).__name__,
        exc_info=True,
        extra={"request_id": request_id},
    )
    return _build_response(
        status_code=500,
        errors={
            "code": ErrorCode.SERVER_ERROR,
            "fields": None,
            "non_fields": _non_fields_unexpected(exc, status_code=500),
        },
        request_id=request_id,
    )