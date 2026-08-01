"""
apps/core/api/mixins.py
─────────────────────────
Response envelope shape — the one place that decides what every API
response looks like at the top level, success or failure.

This module has no knowledge of exceptions, in either direction. It does
not import apps.core.exceptions or apps.core.api.exceptions, and nothing
in those two files imports this one for exception-related purposes.
Its only job is: given some data, a message, and an error payload,
produce a Response with a consistent envelope. Whether that data or
error payload came from a raised exception or a plain view return is
not this module's concern.
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
        headers: dict[str, str] | None = None,
    ) -> Response:
        """
        Assemble a Response with the standard envelope.

        success is computed from status_code (True for any 2xx) rather
        than accepted as a parameter, so it is never possible to return
        a response where success and status_code disagree.

        Args:
            data: The response payload. None for error responses.
            message: Human-readable summary shown at the top level.
            errors: Error detail. None for success responses.
            status_code: HTTP status code for this response.
            meta: Additional metadata (pagination info, request id, etc).
                Passed through transform_payload() before being sent,
                which may add to or replace this value.
            headers: Extra HTTP headers to attach to the response.

        Returns:
            A DRF Response object with the standard envelope as its body.
        """
        payload: dict[str, Any] = {
            self.SUCCESS_KEY: 200 <= status_code < 300,
            self.MESSAGE_KEY: message,
            self.DATA_KEY: data,
            self.ERRORS_KEY: errors,
            self.META_KEY: meta,
        }
        payload = self.transform_payload(payload)

        response = Response(payload, status=status_code)

        if headers:
            for key, value in headers.items():
                response[key] = value

        return response

    def transform_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Hook point for subclasses to modify the payload before it is sent.

        Called once, on every response, by build_response(), after the
        base envelope is assembled and before the Response object is
        constructed. Default implementation is a no-op — subclasses
        override this to add cross-cutting concerns (request id, timing,
        PII masking) without build_response() needing to know about them.

        Args:
            payload: The assembled envelope dict, before being sent.

        Returns:
            The payload to actually send. Default returns it unchanged.
        """
        return payload