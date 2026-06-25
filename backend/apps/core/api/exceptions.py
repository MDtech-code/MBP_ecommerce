
from __future__ import annotations
import logging
from typing import Any, Dict, Callable, List

from rest_framework.views import exception_handler
from rest_framework.response import Response

logger = logging.getLogger('apps.core')


# ─── Monitoring backends — add/remove without touching handler ────────────
_monitors: List[Callable[[Exception], None]] = []

def register_monitor(fn: Callable[[Exception], None]) -> None:
    """Register a monitoring backend. Called on every unhandled exception."""
    _monitors.append(fn)

def _notify_monitors(exc: Exception) -> None:
    for monitor in _monitors:
        try:
            monitor(exc)
        except Exception as e:
            logger.error("Monitor failed: %s", e)


# ─── Structured error model ───────────────────────────────────────────────
def _format_errors(data: Any) -> Any:
    """
    Normalize DRF error data into consistent structure.
    
    DRF returns errors in various formats:
    - string: "Not found."
    - list: ["This field is required."]
    - dict: {"email": ["Enter a valid email address."]}
    
    We normalize to always return structured dict or string.
    """
    if isinstance(data, dict):
        formatted = {}
        for field, messages in data.items():
            if isinstance(messages, list):
                formatted[field] = messages[0] if len(messages) == 1 else messages
            else:
                formatted[field] = messages
        return formatted
    if isinstance(data, list) and len(data) == 1:
        return data[0]
    return data


# ─── Exception handler ────────────────────────────────────────────────────
def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Global exception handler — standardizes all error responses.
    Notifies all registered monitoring backends.
    """
    _notify_monitors(exc)

    response = exception_handler(exc, context)

    if response is None:
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return Response(
            {
                "success": False,
                "message": "Internal server error",
                "data": None,
                "errors": str(exc),
                "meta": None,
            },
            status=500,
        )

    return Response(
        {
            "success": False,
            "message": "Request failed",
            "data": None,
            "errors": _format_errors(response.data),
            "meta": None,
        },
        status=response.status_code,
    )   
