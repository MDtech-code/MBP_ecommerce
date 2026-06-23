

from typing import Any, Dict
import sentry_sdk
from rest_framework.views import exception_handler
from rest_framework.response import Response


def custom_exception_handler(exc: Exception, context: Dict[str, Any]) -> Response:
    """
    Ensures all unhandled exceptions follow standardized API structure.
    """

    # ← capture to Sentry BEFORE handling
    sentry_sdk.capture_exception(exc)
    response = exception_handler(exc, context)

    if response is None:
        return Response(
            {
                "success": False,
                "message": "Internal server error",
                "data": None,
                "errors": str(exc),
            },
            status=500,
        )

    return Response(
        {
            "success": False,
            "message": "Request failed",
            "data": None,
            "errors": response.data,
        },
        status=response.status_code,
    )