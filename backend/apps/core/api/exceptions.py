# apps/core/api/exceptions.py
from __future__ import annotations

import logging
from typing import Any, Callable

from django.conf import settings
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import exception_handler

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


# ─── Error normalization ──────────────────────────────────────────────────────

def _format_errors(data: Any) -> Any:
    """
    Normalize DRF error structures into a consistent shape.

    DRF returns errors in multiple formats depending on the exception type:
        - str:  "Not found."
        - list: ["This field is required."]
        - dict: {"email": ["Enter a valid email address."]}

    Single-item lists are unwrapped to plain strings for cleaner client output.
    Dict values that are single-item lists are similarly unwrapped.
    """
    if isinstance(data, dict):
        formatted: dict[str, Any] = {}
        for field, messages in data.items():
            if isinstance(messages, list):
                formatted[field] = messages[0] if len(messages) == 1 else messages
            else:
                formatted[field] = messages
        return formatted

    if isinstance(data, list) and len(data) == 1:
        return data[0]

    return data


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
                # In DEBUG we expose the exception for local dev convenience.
                # In production this is always None — never leak internals.
                "errors": str(exc) if settings.DEBUG else None,
                "meta": {"request_id": request_id},
            },
            status=500,
        )

    # ── Known DRF exception (4xx / standard 5xx) ─────────────────────────────
    # Only notify monitors for server-side errors, not client errors.
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
            "errors": _format_errors(response.data),
            "meta": {"request_id": request_id},
        },
        status=response.status_code,
    )
# from __future__ import annotations
# import logging
# from typing import Any, Dict, Callable, List

# from rest_framework.views import exception_handler
# from rest_framework.response import Response

# logger = logging.getLogger('apps.core')


# # ─── Monitoring backends — add/remove without touching handler ────────────
# _monitors: List[Callable[[Exception], None]] = []

# def register_monitor(fn: Callable[[Exception], None]) -> None:
#     """Register a monitoring backend. Called on every unhandled exception."""
#     _monitors.append(fn)

# def _notify_monitors(exc: Exception) -> None:
#     for monitor in _monitors:
#         try:
#             monitor(exc)
#         except Exception as e:
#             logger.error("Monitor failed: %s", e)


# # ─── Structured error model ───────────────────────────────────────────────
# def _format_errors(data: Any) -> Any:
#     """
#     Normalize DRF error data into consistent structure.
    
#     DRF returns errors in various formats:
#     - string: "Not found."
#     - list: ["This field is required."]
#     - dict: {"email": ["Enter a valid email address."]}
    
#     We normalize to always return structured dict or string.
#     """
#     if isinstance(data, dict):
#         formatted = {}
#         for field, messages in data.items():
#             if isinstance(messages, list):
#                 formatted[field] = messages[0] if len(messages) == 1 else messages
#             else:
#                 formatted[field] = messages
#         return formatted
#     if isinstance(data, list) and len(data) == 1:
#         return data[0]
#     return data


# # ─── Exception handler ────────────────────────────────────────────────────
# def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
#     """
#     Global exception handler — standardizes all error responses.
#     Notifies all registered monitoring backends.
#     """
#     _notify_monitors(exc)

#     response = exception_handler(exc, context)

#     if response is None:
#         logger.error("Unhandled exception: %s", exc, exc_info=True)
#         return Response(
#             {
#                 "success": False,
#                 "message": "Internal server error",
#                 "data": None,
#                 "errors": str(exc),
#                 "meta": None,
#             },
#             status=500,
#         )

#     return Response(
#         {
#             "success": False,
#             "message": "Request failed",
#             "data": None,
#             "errors": _format_errors(response.data),
#             "meta": None,
#         },
#         status=response.status_code,
#     )   
