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
from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions as drf_exceptions
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




def _app_error_family(exc: BaseAppError) -> str:
    """Name an application error from its class, not from its status.

    A concrete subclass declares its own family and that always wins. The base
    DomainError declares only the generic 'domain_error', yet it is also raised
    directly with 409/422 for conflicts and unprocessable requests; those keep
    the status-derived family so they are not renamed to domain_error.
    """
    declared = getattr(type(exc), "default_code", None)
    if declared and declared != ErrorCode.DOMAIN_ERROR:
        return declared
    mapped = _status_to_error_code(exc.status_code)
    return ErrorCode.DOMAIN_ERROR if mapped == ErrorCode.BAD_REQUEST else mapped


def build_envelope_from_exception(exc: BaseAppError) -> dict[str, Any]:

    """Build the full errors envelope ({code, fields, non_fields}) for any BaseAppError instance."""
    return {
        "code": _app_error_family(exc),
        "fields": None,
        "non_fields": exc.to_envelope(),
    }


#! ─── error family resolution  ─────────────────────────────────────────

# DRF exception classes whose own default_code is not part of the public
# vocabulary, mapped onto the family each one actually represents.
_DRF_ERROR_FAMILIES: dict[type[Exception], str] = {
    drf_exceptions.ValidationError: ErrorCode.VALIDATION_ERROR,
    drf_exceptions.ParseError: ErrorCode.PARSE_ERROR,
    drf_exceptions.NotAuthenticated: ErrorCode.AUTHENTICATION_ERROR,
    drf_exceptions.AuthenticationFailed: ErrorCode.AUTHENTICATION_ERROR,
    drf_exceptions.PermissionDenied: ErrorCode.PERMISSION_ERROR,
    drf_exceptions.NotFound: ErrorCode.NOT_FOUND,
    drf_exceptions.MethodNotAllowed: ErrorCode.METHOD_NOT_ALLOWED,
    drf_exceptions.NotAcceptable: ErrorCode.NOT_ACCEPTABLE,
    drf_exceptions.UnsupportedMediaType: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    drf_exceptions.Throttled: ErrorCode.RATE_LIMIT_EXCEEDED,
}

# Django's Http404 / PermissionDenied keep their identity here. DRF rebuilds
# them as fresh objects inside exception_handler(), so the exception reaching
# this module is still the original Django class and carries no default_code.
# 5xx intentionally resolve to server_error: detail is not published above a
# server error, so the family name is the most specific true statement.
_DJANGO_ERROR_FAMILIES: dict[type[Exception], str] = {
    Http404: ErrorCode.NOT_FOUND,
    DjangoPermissionDenied: ErrorCode.PERMISSION_ERROR,
}

_ERROR_FAMILY_BY_CLASS: dict[type[Exception], str] = {
    **_DRF_ERROR_FAMILIES,
    **_DJANGO_ERROR_FAMILIES,
}


def _resolve_error_family(exc: Exception, status_code: int) -> str:
    """Name the error family from the exception's declared identity.

    Walks the MRO so subclasses inherit their family, which is what makes
    SimpleJWT's InvalidToken (a DRF AuthenticationFailed subclass) resolve
    without naming it here. Status is only a fallback for exceptions that
    declare nothing at all.
    """
    for cls in type(exc).__mro__:
        family = _ERROR_FAMILY_BY_CLASS.get(cls)
        if family is not None:
            return family
    return _status_to_error_code(status_code)


def _exception_message(exc: Exception, response_data: Any) -> str | None:
    """Return the exception's own top-level message when it has a usable one.

    ValidationError carries a dict of field errors, not a single sentence, so it
    gets None and the caller keeps the generic status summary. Same for 5xx:
    their detail is not published, so only the family name is reported.
    """
    if isinstance(exc, ValidationError):
        return None
    if getattr(exc, "status_code", 500) >= 500:
        return None
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str) and detail:
        return str(detail)
    if isinstance(response_data, dict):
        fallback = response_data.get("detail")
        if isinstance(fallback, str) and fallback:
            return str(fallback)
    return None


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
    error_code: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Choose the interpretation using the category selected by the caller.

    The default preserves serializer-error handling in BaseAPIView.error_response().
    Other DRF errors must not interpret public response metadata as input fields.
    error_code and message are supplied by the handler when it knows the
    exception's identity; both fall back to the status maps when omitted.
    """
    if category == "validation":
        return _format_validation_errors(data, status_code, error_code=error_code)
    return _format_general_error(
        data, status_code, category=category, error_code=error_code, message=message
    )


def _format_validation_errors(
    data: Any, status_code: int, *, error_code: str | None = None
) -> dict[str, Any]:
    """Preserve the first-message policy while keeping every reported message.

    Reaching this function already means the payload is serializer validation,
    regardless of whether the caller passed an explicit code.
    """
    top_level_code = error_code or ErrorCode.VALIDATION_ERROR
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
    error_code: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    """Format DRF's public error body without applying serializer-field rules.

    Additional public keys retain their structure under extra. A structured detail
    value is retained under extra.detail with a status-based message. No exception
    attributes are inspected, and the input body is not mutated.
    """
    top_level_code = error_code or _status_to_error_code(status_code)
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
            "message": message or _status_to_message(status_code),
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
    """Fallback family name for exceptions that declare none of their own.

    400 is bad_request, not validation_error: malformed JSON and business-rule
    failures both return 400, and only one of them is validation. Validation
    itself is detected from the exception class, not from the number.
    """
    return {
        400: ErrorCode.BAD_REQUEST,
        401: ErrorCode.AUTHENTICATION_ERROR,
        403: ErrorCode.PERMISSION_ERROR,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        406: ErrorCode.NOT_ACCEPTABLE,
        409: ErrorCode.CONFLICT_ERROR,
        415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
        422: ErrorCode.UNPROCESSABLE_ENTITY_ERROR,
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
    message: str | None = None,
) -> Response:
    """Build the error envelope. message is the exception's own text when known."""
    meta: dict[str, Any] = {"request_id": request_id}

    rate_info = getattr(request, "_rate_limit_info", None) if request else None
    if rate_info:
        meta["rateLimit"] = {
            "limit": rate_info["limit"],
            "remaining": rate_info["remaining"],
            "resetAt": datetime.fromtimestamp(rate_info["reset_at"], tz=dt_timezone.utc).isoformat(),
        }

    response = Response(
        {
            "success": False,
            "message": message or _status_to_message(status_code),
            "data": None,
            "errors": errors,
            "meta": meta,
        },
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
            message=exc.message,
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

        # Name the family and message from the exception itself; the status
        # maps are only reached for exceptions that declare nothing.
        error_code = _resolve_error_family(exc, response.status_code)
        response_message = _exception_message(exc, response.data)
        status_summary = _status_to_message(response.status_code)

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
                response.data,
                response.status_code,
                category=category,
                error_code=error_code,
                message=status_summary,
            ),
            request_id=request_id,
            request=request,
            headers=dict(response.items()),
            message=response_message or status_summary,
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