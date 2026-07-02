

from __future__ import annotations
from typing import Any, Dict, Optional
from rest_framework.response import Response
from rest_framework import status


class APIResponseMixin:
    """
    Standardized API response mixin.

    Provides build_response() which every BaseAPIView response helper
    delegates to. Enforces a consistent response envelope across
    every endpoint in the project:

    {
        "success": bool,        ← True if 2xx, False otherwise
        "message": str | null,  ← Human-readable summary
        "data": any,            ← Response payload (null on error)
        "errors": any | null,   ← Error detail (null on success)
        "meta": dict | null     ← Pagination, request_id, extras
    }

    transform_payload() is a hook point — BaseAPIView overrides it
    to inject request_id into meta on every response automatically.
    """

    MESSAGE_KEY: str = "message"
    ERRORS_KEY: str = "errors"
    DATA_KEY: str = "data"
    SUCCESS_KEY: str = "success"
    META_KEY:str='meta'

    def build_response(
        self,
        *,
        data: Any = None,
        message: Optional[str] = None,
        errors: Any = None,
        status_code: int = status.HTTP_200_OK,
        meta: Optional[Dict[str, Any]] = None,    
        headers: Optional[Dict[str, str]] = None,
    ) -> Response:
        """
        Build a standardized DRF Response object.

        :param data: Main response payload
        :param message: Informational message
        :param errors: Error details if any
        :param status_code: HTTP status code
        :param headers: Optional response headers
        :return: DRF Response
        """
        payload: Dict[str, Any] = {
            self.SUCCESS_KEY: 200 <= status_code < 300,
            self.MESSAGE_KEY: message,
            self.DATA_KEY: data,
            self.ERRORS_KEY: errors,
            self.META_KEY:meta,
        }
        # Hook point — subclasses can override to add trace id, timing, etc.
        payload = self.transform_payload(payload)

        response = Response(payload, status=status_code)

        if headers:
            for key, value in headers.items():
                response[key] = value

        return response

    
    def transform_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override in subclasses to add cross-cutting concerns.
        Example: add request ID, mask PII, add timing.
        Default: return payload unchanged.
        """
        return payload