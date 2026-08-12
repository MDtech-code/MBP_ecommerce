"""
apps/core/api/exceptions.py
────────────────────────────
Global DRF exception handler — HTTP transport layer only.

RESPONSIBILITY
──────────────
This module's sole job is mapping exceptions to HTTP responses.It contains no business logic.

PUBLIC INTERFACE
─────────────────
Only the following names are meant to be imported by other modules
(e.g. apps.core.api.views). Every other name in this file is prefixed
with an underscore and is private to this module — importing a private
name elsewhere defeats the point of having a public interface at all.

    custom_exception_handler        - DRF EXCEPTION_HANDLER entry point
    register_monitor                - monitoring backend injection point
    build_envelope_from_exception   - shared envelope builder for any
                                       BaseAppError, used by both this
                                       handler and BaseAPIView so the two
                                       can never produce different shapes
                                       for the same exception

DEPENDENCY DIRECTION
────────────────────
    apps.core.exceptions          (BaseAppError and its subclasses)
         ↑
    apps.core.api.exceptions      (this file — maps them to HTTP responses)

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
            "category": "domain" | "system" | "validation" | "unexpected",
            "message":  "...",
            "code":     "...",
            "extra":    {...} | null   ← only client_extra, never internal
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
from rest_framework.exceptions import ErrorDetail
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import BaseAppError

logger = logging.getLogger("apps.core")


# ─── Monitoring registry ──────────────────────────────────────────────────────

_monitors: list[Callable[[Exception], None]] = []


def register_monitor(fn: Callable[[Exception], None]) -> None:
    """
    Register a monitoring backend (e.g. Sentry, PagerDuty) to be called
    whenever an exception's notify flag is True, or whenever a genuinely
    unhandled exception reaches this handler.

    A callable registered here receives the raw exception instance and is
    responsible for whatever it does with it (send to Sentry, page
    on-call, etc.). 

    Args:
        fn: A callable accepting a single Exception argument. Return
            value is ignored.
    """
    _monitors.append(fn)


def _notify_monitors(exc: Exception) -> None:
    """
    Invoke every registered monitor with exc, isolating failures.

    Each monitor call is wrapped individually so that one broken
    integration (e.g. Sentry credentials expired) cannot prevent another
    monitor from running, and cannot mask the exception that triggered
    this call in the first place.
    """
    for monitor in _monitors:
        try:
            monitor(exc)
        except Exception as monitor_exc:
            logger.error("Monitor failed: %s", monitor_exc, exc_info=True)


# ─── Envelope builder for BaseAppError instances (public) ────────────────────

def build_envelope_from_exception(exc: BaseAppError) -> dict[str, Any]:
    """
    Build the full errors envelope ({code, fields, non_fields}) for any
    BaseAppError instance.

    Args:
        exc: Any BaseAppError instance (DomainError, InfrastructureError,
            or any future subclass).

    Returns:
        A dict shaped {"code": str, "fields": None, "non_fields": dict},
        ready to be passed as the errors argument to a response builder.
    """
    return {
        "code": _status_to_error_code(exc.status_code),
        "fields": None,
        "non_fields": exc.to_envelope(),
    }


# ─── Non-field block builders for DRF-native and unhandled cases (private) ───
#
# These handle cases that are not BaseAppError instances: DRF's own
# exceptions (ValidationError, AuthenticationFailed, ...) and genuinely
# unhandled exceptions.
def _non_fields_validation(detail: Any) -> dict[str, Any]:
    """
    Build a "validation" non_fields block from a single DRF error value.

    detail is either an ErrorDetail (DRF's str subclass that also carries
    a .code attribute, e.g. code="required") or a plain string/value with
    no .code to read. Both are normalized into the same shape so callers
    never need to know which one they received.

    Args:
        detail: A single DRF error value — typically one element from a
            list DRF returned under a key like "non_field_errors".

    Returns:
        A non_fields dict with category fixed to "validation".
    """
    if isinstance(detail, ErrorDetail):
        return {
            "category": "validation",
            "message": str(detail),
            "code": str(detail.code) if detail.code else "invalid",
            "extra": None,
        }
    return {
        "category": "validation",
        "message": str(detail),
        "code": "invalid",
        "extra": None,
    }


def _non_fields_unexpected(exc: Exception, *, status_code: int) -> dict[str, Any]:
    """
    Build an "unexpected" non_fields block for a genuinely unhandled
    exception (one DRF's own exception_handler did not recognize).

    In DEBUG mode the raw exception message is included, for local
    development convenience. In production the message is always the
    generic, safe default for the given status code — an unhandled
    exception's actual message may contain internals (a stack frame
    detail, a raw SQL error, a file path) that must never reach a client.

    Args:
        exc: The unhandled exception instance.
        status_code: The HTTP status being returned (500, in practice,
            since this path is only reached when DRF produced no
            response of its own).

    Returns:
        A non_fields dict with category fixed to "unexpected".
    """
    return {
        "category": "unexpected",
        "message": str(exc) if settings.DEBUG else _status_to_message(status_code),
        "code": ErrorCode.SERVER_ERROR,
        "extra": None,
    }


# ─── Field-error helpers (private) ─────────────────────────────────────────────

def _extract_error_detail(detail: Any) -> dict[str, str]:
    """
    Extract {message, code} from a single DRF ErrorDetail or plain value.

    Same normalization concern as _non_fields_validation, but shaped for
    a single field's error rather than the top-level non_fields block.
    """
    if isinstance(detail, ErrorDetail):
        return {
            "message": str(detail),
            "code": str(detail.code) if detail.code else "error",
        }
    return {"message": str(detail), "code": "error"}


def _resolve_single(value: Any) -> dict[str, str]:
    """
    Resolve a field's error list to a single {message, code} dict.

    DRF wraps field errors in a list even when there is exactly one
    error for that field. Only the first is surfaced — returning every
    error for a field at once is more detail than a client needs to
    correct one input, and adds noise for no benefit.

    Args:
        value: Either a list of DRF error values for one field, or a
            single error value directly.
    """
    if isinstance(value, list) and value:
        return _extract_error_detail(value[0])
    return _extract_error_detail(value)


# ─── DRF error normalizer (private) ────────────────────────────────────────────

def _format_drf_errors(data: Any, status_code: int) -> dict[str, Any]:
    """
    Normalize DRF-native error data into the standard errors envelope.

    Used only for exceptions DRF's own exception_handler already
    recognized and formatted (data is response.data from that call), or
    for a plain string/dict a view helper wants formatted the same way.
    BaseAppError instances never reach this function — they are handled
    by build_envelope_from_exception instead.

    DRF error shapes handled here:
        dict  → {"email": [ErrorDetail(...)], "non_field_errors": [...]}
        list  → [ErrorDetail("Authentication credentials not provided.")]
        str   → "Not found."

    Args:
        data: The raw error data, in one of the three shapes above.
        status_code: The HTTP status this data corresponds to, used to
            derive the top-level error code.

    Returns:
        The full errors sub-object: {code, fields, non_fields}.
    """
    top_level_code = _status_to_error_code(status_code)
    fields: dict[str, Any] = {}
    non_fields: dict[str, Any] | None = None

    if isinstance(data, dict):
        for field, value in data.items():
            # if field == "non_field_errors":
            if field in ("non_field_errors", "detail"):
                raw = value[0] if isinstance(value, list) and value else value
                non_fields = _non_fields_validation(raw)
            else:
                fields[field] = _resolve_single(value)

    elif isinstance(data, list) and data:
        non_fields = _non_fields_validation(data[0])

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


# ─── HTTP mapping helpers (private) ────────────────────────────────────────────

def _status_to_error_code(status_code: int) -> str:
    """
    Map an HTTP status to a top-level ErrorCode string.

    This is a fallback source of truth. For any BaseAppError subclass,
    the exception's own status_code still passes through this function
    to derive the top-level code — but the richer, per-exception detail
    (category, message, specific code) always comes from exc.to_envelope()
    directly, not from this dict. This function only decides the coarse
    top-level classification (e.g. "this is a 409, call it CONFLICT_ERROR"),
    which is genuinely a property of the status code alone, not of any
    particular exception type.

    409 maps to CONFLICT_ERROR rather than VALIDATION_ERROR deliberately:
    a 409 means the input was well-formed but the current state refuses
    the operation, which is a different failure class than malformed input.

    Args:
        status_code: An HTTP status code.

    Returns:
        The corresponding ErrorCode string, or SERVER_ERROR if the status
        code has no explicit mapping.
    """
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
    """
    Map an HTTP status to a safe, generic, human-readable default message.

    Used whenever no more specific message is available (unhandled
    exceptions in production, DRF-native errors with no better text) or
    as the top-level "message" field of the response envelope, which is
    always a generic per-status string regardless of what triggered it —
    the specific detail belongs in errors.non_fields.message, not here.

    Args:
        status_code: An HTTP status code.

    Returns:
        A generic message string for that status, or a generic fallback
        if the status code has no explicit entry.
    """
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


# ─── Response builder (private) ────────────────────────────────────────────────

def _build_response(
    *,
    status_code: int,
    errors: dict[str, Any],
    request_id: str | None,
    headers: dict[str, str] | None = None,
) -> Response:
    """
    Assemble the final standardized Response object.

    Every exit point of custom_exception_handler funnels through this
    function, which is what guarantees every error response — regardless
    of which branch produced it — has the identical top-level shape
    (success, message, data, errors, meta).

    Args:
        status_code: HTTP status to return.
        errors: The full errors sub-object, as produced by
            build_envelope_from_exception or _format_drf_errors.
        request_id: The current request's id, if available, included in
            meta for tracing a specific failure through logs.
    """
    response = Response(
        {
            "success": False,
            "message": _status_to_message(status_code),
            "data": None,
            "errors": errors,
            "meta": {"request_id": request_id},
        },
        status=status_code,
    )
    if headers:
        for key, value in headers.items():
            response[key] = value
    return response


# ─── Main handler ─────────────────────────────────────────────────────────────

def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    """
    Global DRF exception handler — standardizes every error response.

    Registered as DRF's EXCEPTION_HANDLER, this function is called
    automatically whenever a view raises an exception DRF does not
    handle internally before this point. All logging happens here and
    only here; every helper this function calls is a pure function with
    no side effects, which guarantees exactly one log entry and at most
    one monitor notification per exception.

    Decision tree
    ──────────────
    1. isinstance(exc, BaseAppError)
       → status from exc.status_code
       → notify from exc.notify: True triggers monitors + ERROR log with
         traceback; False logs at WARNING with no traceback
       → exc.internal, if present, is logged (never passed to a builder)
       → envelope built via build_envelope_from_exception(exc), which
         reads exc.category, exc.message, exc.code, exc.client_extra —
         this one branch covers every current and future BaseAppError
         subclass; no per-subclass branching is needed here

    2. DRF-recognized exception (ValidationError, AuthenticationFailed, ...)
       → DRF's own exception_handler produces the original status code
       → 4xx logged at WARNING, no traceback
       → 5xx logged at ERROR with traceback, monitors notified
       → response data normalized via _format_drf_errors

    3. Unhandled exception (DRF's exception_handler returns None)
       → always 500, always ERROR + traceback, monitors always notified
       → raw exception message shown only when settings.DEBUG is True

    Security invariant
    ────────────────────
    exc.internal is logged here and never passed to any builder function.
    build_envelope_from_exception calls exc.to_envelope(), and
    BaseAppError.to_envelope() does not include internal in its return
    value — so this invariant holds regardless of which BaseAppError
    subclass is involved, without this function needing to enforce it
    per branch.

    Args:
        exc: The raised exception.
        context: DRF's handler context, containing "request" and "view".

    Returns:
        A standardized Response object.
    """
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