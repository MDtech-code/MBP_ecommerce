# apps/core/api/exceptions.py
from __future__ import annotations

import logging
from typing import Any, Callable

from django.conf import settings
from rest_framework.exceptions import ErrorDetail
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

from apps.core.error_codes import ErrorCode

logger = logging.getLogger("apps.core")


# ─── Monitoring registry ──────────────────────────────────────────────────────

_monitors: list[Callable[[Exception], None]] = []


def register_monitor(fn: Callable[[Exception], None]) -> None:
    """
    Register a monitoring backend (e.g. Sentry, PagerDuty).

    Registered monitors are called only on unexpected (unhandled) exceptions —
    NOT on standard DRF validation/auth errors.
    """
    _monitors.append(fn)


def _notify_monitors(exc: Exception) -> None:
    """
    Invoke all registered monitors.

    Failures in individual monitors are caught and logged so one
    broken monitor cannot suppress others.
    """
    for monitor in _monitors:
        try:
            monitor(exc)
        except Exception as monitor_exc:
            logger.error(
                "Monitor failed: %s",
                monitor_exc,
                exc_info=True,
            )


# ─── Error code extraction ────────────────────────────────────────────────────

def _extract_error_detail(detail: Any) -> dict[str, str]:
    """
    Extract message and code from a single error value.

    DRF wraps every error string in an ErrorDetail object which carries
    both the human-readable string and a machine-readable code.

    Handles:
        - ErrorDetail instance       → extract str + .code directly
        - Plain string               → use as message, code falls back to "error"
        - Anything else              → str() coerce, code falls back to "error"

    Args:
        detail: A single error value from DRF's exception data.

    Returns:
        dict with guaranteed ``message`` and ``code`` keys.
    """
    if isinstance(detail, ErrorDetail):
        return {
            "message": str(detail),
            "code": str(detail.code) if detail.code else "error",
        }
    return {
        "message": str(detail),
        "code": "error",
    }


def _resolve_single(value: Any) -> dict[str, str]:
    """
    Resolve a field's error value to a single {message, code} dict.

    DRF always wraps field errors in lists even when there is only one.
    We always surface only the first error per field — showing multiple
    errors per field simultaneously is poor UX and not needed.

    Args:
        value: The error value for a single field — list or scalar.

    Returns:
        dict with ``message`` and ``code`` keys.
    """
    if isinstance(value, list) and len(value) > 0:
        return _extract_error_detail(value[0])
    return _extract_error_detail(value)


# ─── Error normalization ──────────────────────────────────────────────────────

def _format_errors(data: Any, status_code: int = 400) -> dict[str, Any]:
    """
    Normalize DRF error structures into the standardized error envelope.

    DRF returns errors in multiple formats depending on exception type:
        - dict: {"email": [ErrorDetail(...)], "non_field_errors": [...]}
        - list: [ErrorDetail("detail message")]
        - str:  "Not found."

    Output contract (always):
        {
            "code":       str,           # top-level category code
            "fields":     dict | null,   # field-level errors
            "non_fields": dict | null    # non-field / cross-field errors
        }

    The top-level ``code`` is derived from the HTTP status code so the
    frontend always knows the error category without inspecting fields.

    Args:
        data:        Raw error data from DRF response.
        status_code: HTTP status from the DRF response object.

    Returns:
        Standardized error dict matching the contract above.
    """
    top_level_code = _status_to_error_code(status_code)
    fields: dict[str, Any] = {}
    non_fields: dict[str, str] | None = None

    # ── Dict — standard validation error shape from DRF ───────────────────────
    if isinstance(data, dict):
        for field, value in data.items():
            if field == "non_field_errors":
                # Cross-field errors — not tied to a specific field
                non_fields = _resolve_single(value)
            else:
                # Field-level error — map onto fields dict
                fields[field] = _resolve_single(value)

    # ── List — e.g. top-level AuthenticationFailed, PermissionDenied ─────────
    elif isinstance(data, list) and len(data) > 0:
        non_fields = _extract_error_detail(data[0])

    # ── Plain string — e.g. "Not found." ─────────────────────────────────────
    elif isinstance(data, str):
        non_fields = {"message": data, "code": top_level_code}

    return {
        "code":       top_level_code,
        "fields":     fields if fields else None,
        "non_fields": non_fields,
    }


def _status_to_error_code(status_code: int) -> str:
    """
    Map HTTP status codes to top-level ErrorCode category strings.

    These populate the ``errors.code`` field so the frontend always
    knows the error category without inspecting message strings.
    """
    return {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.AUTHENTICATION_ERROR,
        403: ErrorCode.PERMISSION_ERROR,
        404: ErrorCode.NOT_FOUND,
        405: ErrorCode.METHOD_NOT_ALLOWED,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.SERVER_ERROR,
    }.get(status_code, ErrorCode.SERVER_ERROR)


def _status_to_message(status_code: int) -> str:
    """
    Map HTTP status codes to human-readable default messages.

    Provides more useful default messages than a single generic string
    while keeping sensitive implementation details out of responses.
    """
    return {
        400: "Invalid request data.",
        401: "Authentication required.",
        403: "You do not have permission to perform this action.",
        404: "The requested resource was not found.",
        405: "Method not allowed.",
        429: "Too many requests. Please slow down.",
        500: "An unexpected error occurred. Please try again later.",
    }.get(status_code, "Request failed.")


# ─── Handler ─────────────────────────────────────────────────────────────────

def custom_exception_handler(
    exc: Exception,
    context: dict[str, Any],
) -> Response:
    """
    Global DRF exception handler — standardizes all error responses.

    Behaviour:
        - Expected DRF exceptions (4xx): formatted response, no monitor alert.
        - Unhandled exceptions (response is None / 5xx):
            - Monitors notified.
            - Logged at ERROR with full traceback.
            - Raw exception detail NEVER exposed to client in production.
            - request_id included in response for client-side correlation.

    Args:
        exc: The raised exception.
        context: DRF handler context (contains ``request``, ``view``).

    Returns:
        Standardized ``Response`` object.
    """
    request: Request | None = context.get("request")
    request_id: str | None = getattr(request, "id", None)

    response = exception_handler(exc, context)

    # ── Unhandled exception (no DRF response produced) ────────────────────────
    if response is None:
        _notify_monitors(exc)
        logger.error(
            "Unhandled exception in view",
            exc_info=True,
            extra={
                "request_id": request_id,
                "exception_type": type(exc).__name__,
            },
        )
        return Response(
            {
                "success": False,
                "message": _status_to_message(500),
                "data": None,
                "errors": {
                    "code": ErrorCode.SERVER_ERROR,
                    "fields": None,
                    # In DEBUG we expose the exception for local dev convenience.
                    # In production this is always None — never leak internals.
                    "non_fields": (
                        {"message": str(exc), "code": ErrorCode.SERVER_ERROR}
                        if settings.DEBUG
                        else None
                    ),
                },
                "meta": {"request_id": request_id},
            },
            status=500,
        )

    # ── Known DRF exception (4xx / standard 5xx) ─────────────────────────────
    if response.status_code >= 500:
        _notify_monitors(exc)
        logger.error(
            "Server error via DRF exception handler",
            exc_info=True,
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
            },
        )
    else:
        logger.warning(
            "Client error handled",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "exception_type": type(exc).__name__,
            },
        )

    return Response(
        {
            "success": False,
            "message": _status_to_message(response.status_code),
            "data": None,
            "errors": _format_errors(response.data, response.status_code),
            "meta": {"request_id": request_id},
        },
        status=response.status_code,
    )

    
# # apps/core/api/exceptions.py
# from __future__ import annotations

# import logging
# from typing import Any, Callable

# from django.conf import settings
# from rest_framework.request import Request
# from rest_framework.response import Response
# from rest_framework.views import exception_handler

# logger = logging.getLogger("apps.core")


# # ─── Monitoring registry ──────────────────────────────────────────────────────

# _monitors: list[Callable[[Exception], None]] = []


# def register_monitor(fn: Callable[[Exception], None]) -> None:
#     """
#     Register a monitoring backend (e.g. Sentry, PagerDuty).

#     Registered monitors are called only on unexpected (unhandled) exceptions —
#     NOT on standard DRF validation/auth errors.
#     """
#     _monitors.append(fn)


# def _notify_monitors(exc: Exception) -> None:
#     """
#     Invoke all registered monitors.

#     Failures in individual monitors are caught and logged so one
#     broken monitor cannot suppress others.
#     """
#     for monitor in _monitors:
#         try:
#             monitor(exc)
#         except Exception as monitor_exc:
#             logger.error(
#                 "Monitor failed: %s",
#                 monitor_exc,
#                 exc_info=True,
#             )


# # ─── Error normalization ──────────────────────────────────────────────────────

# def _format_errors(data: Any) -> Any:
#     """
#     Normalize DRF error structures into a consistent shape.

#     DRF returns errors in multiple formats depending on the exception type:
#         - str:  "Not found."
#         - list: ["This field is required."]
#         - dict: {"email": ["Enter a valid email address."]}

#     Single-item lists are unwrapped to plain strings for cleaner client output.
#     Dict values that are single-item lists are similarly unwrapped.
#     """
#     if isinstance(data, dict):
#         formatted: dict[str, Any] = {}
#         for field, messages in data.items():
#             if isinstance(messages, list):
#                 formatted[field] = messages[0] if len(messages) == 1 else messages
#             else:
#                 formatted[field] = messages
#         return formatted

#     if isinstance(data, list) and len(data) == 1:
#         return data[0]

#     return data


# def _status_to_message(status_code: int) -> str:
#     """
#     Map HTTP status codes to human-readable default messages.

#     Provides more useful default messages than a single generic string
#     while keeping sensitive implementation details out of responses.
#     """
#     return {
#         400: "Invalid request data.",
#         401: "Authentication required.",
#         403: "You do not have permission to perform this action.",
#         404: "The requested resource was not found.",
#         405: "Method not allowed.",
#         429: "Too many requests. Please slow down.",
#         500: "An unexpected error occurred. Please try again later.",
#     }.get(status_code, "Request failed.")


# # ─── Handler ─────────────────────────────────────────────────────────────────

# def custom_exception_handler(
#     exc: Exception,
#     context: dict[str, Any],
# ) -> Response:
#     """
#     Global DRF exception handler — standardizes all error responses.

#     Behaviour:
#         - Expected DRF exceptions (4xx): formatted response, no monitor alert.
#         - Unhandled exceptions (response is None / 5xx):
#             - Monitors notified.
#             - Logged at ERROR with full traceback.
#             - Raw exception detail NEVER exposed to client in production.
#             - request_id included in response for client-side correlation.

#     Args:
#         exc: The raised exception.
#         context: DRF handler context (contains ``request``, ``view``).

#     Returns:
#         Standardized ``Response`` object.
#     """
#     request: Request | None = context.get("request")
#     request_id: str | None = getattr(request, "id", None)

#     response = exception_handler(exc, context)

#     # ── Unhandled exception (no DRF response produced) ────────────────────────
#     if response is None:
#         _notify_monitors(exc)
#         logger.error(
#             "Unhandled exception in view",
#             exc_info=True,
#             extra={
#                 "request_id": request_id,
#                 "exception_type": type(exc).__name__,
#             },
#         )
#         return Response(
#             {
#                 "success": False,
#                 "message": _status_to_message(500),
#                 "data": None,
#                 # In DEBUG we expose the exception for local dev convenience.
#                 # In production this is always None — never leak internals.
#                 "errors": str(exc) if settings.DEBUG else None,
#                 "meta": {"request_id": request_id},
#             },
#             status=500,
#         )

#     # ── Known DRF exception (4xx / standard 5xx) ─────────────────────────────
#     # Only notify monitors for server-side errors, not client errors.
#     if response.status_code >= 500:
#         _notify_monitors(exc)
#         logger.error(
#             "Server error via DRF exception handler",
#             exc_info=True,
#             extra={
#                 "request_id": request_id,
#                 "status_code": response.status_code,
#             },
#         )
#     else:
#         logger.warning(
#             "Client error handled",
#             extra={
#                 "request_id": request_id,
#                 "status_code": response.status_code,
#                 "exception_type": type(exc).__name__,
#             },
#         )

#     return Response(
#         {
#             "success": False,
#             "message": _status_to_message(response.status_code),
#             "data": None,
#             "errors": _format_errors(response.data),
#             "meta": {"request_id": request_id},
#         },
#         status=response.status_code,
#     )

