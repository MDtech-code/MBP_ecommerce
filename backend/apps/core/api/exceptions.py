"""
apps/core/api/exceptions.py
───────────────────────────
Global DRF exception handler — HTTP transport layer only.

RESPONSIBILITY
──────────────
This module's sole job is mapping exceptions → HTTP responses.
It contains NO business logic. All custom exception types live in
apps.core.exceptions and are imported here — never the reverse.

DEPENDENCY DIRECTION
────────────────────
    apps.core.exceptions          (DomainError, InfrastructureError)
         ↑
    apps.core.api.exceptions      (this file — maps them to HTTP responses)

Services import from apps.core.exceptions.
This file imports from apps.core.exceptions.
Nothing imports api.exceptions except Django settings (EXCEPTION_HANDLER)
and BaseAPIView (for _format_drf_errors, _non_fields_domain,
_status_to_error_code).

ERROR ENVELOPE (always)
───────────────────────
{
    "success":  false,
    "message":  "<safe human string>",
    "data":     null,
    "errors": {
        "code":       "<top-level ErrorCode>",
        "fields":     { "<field>": {"message": "...", "code": "..."} } | null,
        "non_fields": {
            "category": "validation" | "domain" | "system" | "unexpected",
            "message":  "...",
            "code":     "...",
            "extra":    {...} | null   ← ONLY client_extra, never internal
        } | null
    },
    "meta": { "request_id": "..." }
}

NON-FIELD CATEGORIES
────────────────────
  validation  – DRF non_field_errors / auth / permission / not-found.
  domain      – Business-rule violation (DomainError).
  system      – Infrastructure failure (InfrastructureError).
  unexpected  – Unhandled exception; always triggers monitor + ERROR log.

SECURITY INVARIANT
──────────────────
exc.internal is NEVER serialized into any response in any branch.
It is only passed to the logger in custom_exception_handler.

LOGGING POLICY
──────────────
All logging lives in custom_exception_handler — not in builders.
Builders are pure functions: input → dict, zero side effects.
This means one log entry per exception, one Sentry issue per event.

  DomainError                        → WARNING, no exc_info
  InfrastructureError notify=True    → ERROR + exc_info  (unexpected)
  InfrastructureError notify=False   → WARNING, no exc_info  (expected)
  DRF 4xx                            → WARNING, no exc_info
  DRF 5xx                            → ERROR + exc_info
  Unhandled                          → ERROR + exc_info
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from django.conf import settings
from rest_framework.exceptions import ErrorDetail
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError, InfrastructureError

logger = logging.getLogger("apps.core")


# ─── Monitoring registry ──────────────────────────────────────────────────────

_monitors: list[Callable[[Exception], None]] = []


def register_monitor(fn: Callable[[Exception], None]) -> None:
    """
    Register a monitoring backend (e.g. Sentry, PagerDuty).

    Called on:
        - InfrastructureError where notify=True
        - DRF 5xx responses
        - Unhandled exceptions

    NOT called on:
        - DomainError                            (expected business logic)
        - DRF 4xx                                (client errors, not our defects)
        - InfrastructureError where notify=False (expected, handled outage)
    """
    _monitors.append(fn)


def _notify_monitors(exc: Exception) -> None:
    """Invoke all registered monitors, isolating individual failures."""
    for monitor in _monitors:
        try:
            monitor(exc)
        except Exception as monitor_exc:
            logger.error("Monitor failed: %s", monitor_exc, exc_info=True)


# ─── Non-field block builders (pure — zero side effects) ─────────────────────
#
# These functions produce the non_fields sub-object only.
# They do NOT log. All logging is in custom_exception_handler.
# This guarantees one log entry per exception regardless of code path.
#
# Security contract: client_extra is forwarded to the response.
#                    internal is NOT touched here — handler logs it.

def _non_fields_validation(detail: Any) -> dict[str, Any]:
    """
    Build a 'validation' non_fields block from a DRF ErrorDetail or plain value.

    Used for: DRF non_field_errors, list-shaped errors, plain strings.
    """
    if isinstance(detail, ErrorDetail):
        return {
            "category": "validation",
            "message":  str(detail),
            "code":     str(detail.code) if detail.code else "invalid",
            "extra":    None,
        }
    return {
        "category": "validation",
        "message":  str(detail),
        "code":     "invalid",
        "extra":    None,
    }


def _non_fields_domain(exc: DomainError) -> dict[str, Any]:
    """
    Build a 'domain' non_fields block from a DomainError.

    Pure — no logging. Handler logs internal data before calling this.
    client_extra forwarded to response; internal excluded entirely.
    """
    return {
        "category": "domain",
        "message":  exc.message,
        "code":     exc.code,
        "extra":    exc.client_extra,   # client_extra only; internal excluded
    }


def _non_fields_infrastructure(exc: InfrastructureError) -> dict[str, Any]:
    """
    Build a 'system' non_fields block from an InfrastructureError.

    Pure — no logging. Handler logs internal data before calling this.
    client_extra forwarded to response; internal excluded entirely.
    """
    return {
        "category": "system",
        "message":  exc.message,
        "code":     exc.code,
        "extra":    exc.client_extra,   # client_extra only; internal excluded
    }


def _non_fields_unexpected(exc: Exception, *, status_code: int) -> dict[str, Any]:
    """
    Build an 'unexpected' non_fields block for unhandled exceptions.

    Pure — no logging. Handler logs before calling this.

    DEBUG:      raw exception message included (local dev convenience).
    Production: always the safe generic message — never leak internals.
    """
    return {
        "category": "unexpected",
        "message": (
            str(exc) if settings.DEBUG
            else _status_to_message(status_code)
        ),
        "code":  ErrorCode.SERVER_ERROR,
        "extra": None,
    }


# ─── Field-error helpers ──────────────────────────────────────────────────────

def _extract_error_detail(detail: Any) -> dict[str, str]:
    """Extract {message, code} from a single DRF ErrorDetail or plain value."""
    if isinstance(detail, ErrorDetail):
        return {
            "message": str(detail),
            "code":    str(detail.code) if detail.code else "error",
        }
    return {"message": str(detail), "code": "error"}


def _resolve_single(value: Any) -> dict[str, str]:
    """
    Resolve a field's error list to a single {message, code} dict.

    DRF wraps field errors in lists even when there is only one.
    We surface only the first — showing multiple errors per field
    simultaneously is poor UX.
    """
    if isinstance(value, list) and value:
        return _extract_error_detail(value[0])
    return _extract_error_detail(value)


# ─── DRF error normalizer ─────────────────────────────────────────────────────

def _format_drf_errors(data: Any, status_code: int) -> dict[str, Any]:
    """
    Normalize DRF error data into the standard errors envelope.

    Called by:
        - custom_exception_handler for DRF-recognised exceptions
        - BaseAPIView.error_response() for manually constructed responses
        - BaseAPIView.not_found_response() / unauthorized_response() /
          forbidden_response() to ensure a consistent errors envelope

    DRF error shapes handled:
        dict  → {"email": [ErrorDetail], "non_field_errors": [...]}
        list  → [ErrorDetail("Authentication credentials not provided.")]
        str   → "Not found."

    Returns the full ``errors`` sub-object (code + fields + non_fields).
    """
    top_level_code = _status_to_error_code(status_code)
    fields: dict[str, Any] = {}
    non_fields: dict[str, Any] | None = None

    if isinstance(data, dict):
        for field, value in data.items():
            if field == "non_field_errors":
                raw = value[0] if isinstance(value, list) and value else value
                non_fields = _non_fields_validation(raw)
            else:
                fields[field] = _resolve_single(value)

    elif isinstance(data, list) and data:
        non_fields = _non_fields_validation(data[0])

    elif isinstance(data, str):
        non_fields = {
            "category": "validation",
            "message":  data,
            "code":     top_level_code,
            "extra":    None,
        }

    return {
        "code":       top_level_code,
        "fields":     fields if fields else None,
        "non_fields": non_fields,
    }


# ─── HTTP mapping helpers ─────────────────────────────────────────────────────

def _status_to_error_code(status_code: int) -> str:
    """
    Map HTTP status to top-level ErrorCode string.

    409 → CONFLICT_ERROR, not VALIDATION_ERROR.
    Rationale: validation_error implies "you sent malformed data."
    A 409 means "data was valid but current state refuses the operation."
    Conflating them forces the frontend to inspect category to correct
    the top-level code, which defeats having a top-level code at all.
    """
    return {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTHENTICATION_ERROR,
        403: ErrorCode.PERMISSION_ERROR,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        409: ErrorCode.CONFLICT_ERROR,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.SERVER_ERROR,
        503: ErrorCode.SERVER_ERROR,
    }.get(status_code, ErrorCode.SERVER_ERROR)


def _status_to_message(status_code: int) -> str:
    """Map HTTP status to safe, human-readable default message."""
    return {
        400: "Invalid request data.",
        401: "Authentication required.",
        403: "You do not have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        409: "This action conflicts with the current state of the resource.",
        429: "Too many requests. Please slow down.",
        500: "An unexpected error occurred. Please try again later.",
        503: "The service is temporarily unavailable. Please try again shortly.",
    }.get(status_code, "Request failed.")


# ─── Response builder ─────────────────────────────────────────────────────────

def _build_response(
    *,
    status_code: int,
    errors: dict[str, Any],
    request_id: str | None,
) -> Response:
    """Assemble the final standardized Response object."""
    return Response(
        {
            "success": False,
            "message": _status_to_message(status_code),
            "data":    None,
            "errors":  errors,
            "meta":    {"request_id": request_id},
        },
        status=status_code,
    )


# ─── Main handler ─────────────────────────────────────────────────────────────

def custom_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response:
    """
    Global DRF exception handler — standardizes all error responses.

    All logging happens here and only here. Builders are pure functions.
    This guarantees exactly one log entry and one Sentry issue per exception.

    Decision tree
    ─────────────
    1.  DomainError
        → status from exc.status_code (400 or 409)
        → non_fields.category = "domain"
        → NO monitor alert
        → logged at WARNING, no traceback
        → exc.internal logged at DEBUG before builder is called
        → exc.client_extra forwarded to client via builder

    2.  InfrastructureError
        → 503 Service Unavailable
        → non_fields.category = "system"
        → notify=True  → monitor alert + ERROR log with traceback
        → notify=False → WARNING log, no traceback, no monitor
        → exc.internal logged at appropriate level before builder is called
        → exc.client_extra forwarded to client via builder

    3.  DRF-recognised exception (ValidationError, AuthenticationFailed, …)
        → original DRF status code preserved
        → non_fields.category = "validation" (or null for pure field errors)
        → 4xx → WARNING, no traceback
        → 5xx → ERROR + traceback + monitor alert

    4.  Unhandled exception (DRF produces no response)
        → 500 Internal Server Error
        → non_fields.category = "unexpected"
        → always ERROR + traceback + monitor alert
        → raw message shown in DEBUG only, hidden in production

    Security invariant
    ──────────────────
    exc.internal is logged here and never passed to any builder.
    Builders only receive the exception object to read client_extra.

    Args:
        exc:     The raised exception.
        context: DRF handler context (contains ``request``, ``view``).

    Returns:
        Standardized Response object.
    """
    request: Request | None = context.get("request")
    request_id: str | None = getattr(request, "id", None)

    # ── 1. DomainError ────────────────────────────────────────────────────────
    if isinstance(exc, DomainError):
        # Log internal diagnostic data at DEBUG — not a defect, no traceback.
        if exc.internal:
            logger.debug(
                "DomainError internal context [%s]: %s",
                exc.code,
                exc.internal,
                extra={"request_id": request_id},
            )
        logger.warning(
            "Domain error: %s [code=%s, status=%s]",
            exc.message,
            exc.code,
            exc.status_code,
            extra={"request_id": request_id},
        )
        return _build_response(
            status_code=exc.status_code,
            errors={
                "code":       _status_to_error_code(exc.status_code),
                "fields":     None,
                "non_fields": _non_fields_domain(exc),
            },
            request_id=request_id,
        )

    # ── 2. InfrastructureError ────────────────────────────────────────────────
    if isinstance(exc, InfrastructureError):
        if exc.notify:
            # Unexpected infrastructure failure — alert on-call, full traceback.
            _notify_monitors(exc)
            if exc.internal:
                logger.error(
                    "InfrastructureError internal context [%s]: %s",
                    exc.code,
                    exc.internal,
                    exc_info=True,
                    extra={"request_id": request_id},
                )
            logger.error(
                "Infrastructure error: %s [code=%s]",
                exc.message,
                exc.code,
                exc_info=True,
                extra={"request_id": request_id},
            )
        else:
            # Expected, handled outage — no monitor, no traceback.
            if exc.internal:
                logger.warning(
                    "InfrastructureError (handled) internal context [%s]: %s",
                    exc.code,
                    exc.internal,
                    extra={"request_id": request_id},
                )
            logger.warning(
                "Infrastructure error (expected/handled): %s [code=%s]",
                exc.message,
                exc.code,
                extra={"request_id": request_id},
            )
        return _build_response(
            status_code=503,
            errors={
                "code":       ErrorCode.SERVER_ERROR,
                "fields":     None,
                "non_fields": _non_fields_infrastructure(exc),
            },
            request_id=request_id,
        )

    # ── 3. DRF-recognised exception ───────────────────────────────────────────
    response = exception_handler(exc, context)

    if response is not None:
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
            errors=_format_drf_errors(response.data, response.status_code),
            request_id=request_id,
        )

    # ── 4. Unhandled exception ────────────────────────────────────────────────
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
            "code":       ErrorCode.SERVER_ERROR,
            "fields":     None,
            "non_fields": _non_fields_unexpected(exc, status_code=500),
        },
        request_id=request_id,
    )
