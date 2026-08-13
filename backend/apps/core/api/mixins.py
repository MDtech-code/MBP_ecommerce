"""
apps/core/api/mixins.py
─────────────────────────

"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.response import Response


class APIResponseMixin:
    """
    Mixin providing build_response(), the single function every response
    helper on BaseAPIView delegates to.

    Guarantees every endpoint returns the same top-level shape:

        {
            "success": bool,        - True if 2xx, False otherwise,
                                       derived from status_code, never
                                       passed in directly
            "message": str | None,  - human-readable summary
            "data":    Any,         - response payload, None on error
            "errors":  Any | None,  - error detail, None on success
            "meta":    dict | None  - pagination, request_id, extras
        }

    transform_payload() is a hook subclasses override to inject
    cross-cutting data (BaseAPIView uses it to add request_id) without
    this mixin needing to know that concern exists.
    """

    MESSAGE_KEY: str = "message"
    ERRORS_KEY: str = "errors"
    DATA_KEY: str = "data"
    SUCCESS_KEY: str = "success"
    META_KEY: str = "meta"

    def build_response(
        self,
        *,
        data: Any = None,
        message: str | None = None,
        errors: Any = None,
        status_code: int = status.HTTP_200_OK,
        meta: dict[str, Any] | None = None,
        included: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Response:
        
        payload: dict[str, Any] = {
            self.SUCCESS_KEY: 200 <= status_code < 300,
            self.MESSAGE_KEY: message,
            self.DATA_KEY: data,
            self.ERRORS_KEY: errors,
            self.META_KEY: meta,
        }
        payload = self.transform_payload(payload)

        response = Response(payload, status=status_code)

        if included is not None:
            payload["included"] = included

        if headers:
            for key, value in headers.items():
                response[key] = value

        return response

    def transform_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        
        return payload