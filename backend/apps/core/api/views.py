"""
apps/core/api/views.py
─────────────────────────
"""

from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core.exceptions import (  
    AuthenticationRequiredError,
    BaseAppError,
    NotFoundError,
    PermissionDeniedError,
)
from .exceptions import build_envelope_from_exception, _format_drf_errors
from .mixins import APIResponseMixin
from datetime import datetime, timezone as dt_timezone


class BaseAPIView(APIResponseMixin, GenericAPIView):
    

    permission_classes = [AllowAny]

    # ── Success helpers ───────────────────────────────────────────────────────

    def success_response(
        self,
        *,
        data: Any = None,
        message: str = "Request successful",
        status_code: int = status.HTTP_200_OK,
        meta: dict[str, Any] | None = None,
    ) -> Response:
        
        return self.build_response(
            data=data,
            message=message,
            status_code=status_code,
            meta=meta,
        )



    def list_response(self,*,data: Any,message: str = "Request successful",meta: dict[str, Any] | None = None,) -> Response:

        if isinstance(data, dict):
            raise TypeError(
                "list_response() received a dict — use success_response() for single resources."
            )
    
        return self.success_response(
            data=list(data) if data is not None else [],
            message=message,
            meta=meta,
        )

    def created_response(
        self,
        *,
        data: Any = None,
        message: str = "Resource created successfully",
        meta: dict[str, Any] | None = None,
    ) -> Response:

        return self.build_response(
            data=data,
            message=message,
            status_code=status.HTTP_201_CREATED,
            meta=meta,
        )

    # ── Error helpers ─────────────────────────────────────────────────────────

    def error_response(
        self,
        *,
        message: str = "Request failed",
        errors: Any = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ) -> Response:
       
        return self.build_response(
            message=message,
            errors=_format_drf_errors(errors, status_code) if errors is not None else None,
            status_code=status_code,
        )

    def app_error_response(self, *, exc: BaseAppError) -> Response:
        
        return self.build_response(
            message=exc.message,
            errors=build_envelope_from_exception(exc),
            status_code=exc.status_code,
        )

    def not_found_response(
        self, *, message: str = "The requested resource was not found."
    ) -> Response:
        return self.app_error_response(exc=NotFoundError(message))

    def unauthorized_response(
        self, *, message: str = "Authentication required."
    ) -> Response:

        return self.app_error_response(exc=AuthenticationRequiredError(message))

    def forbidden_response(
        self,
        *,
        message: str = "You do not have permission to perform this action.",
    ) -> Response:
        
        return self.app_error_response(exc=PermissionDeniedError(message))

    # ── Payload hook ──────────────────────────────────────────────────────────

    def transform_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Inject request_id into every response's meta .       
        """
        request_id = getattr(self.request, "id", None)
        if request_id:
            if payload.get("meta") is None:
                payload["meta"] = {}
            payload["meta"]["request_id"] = request_id
        rate_info = getattr(self.request, "_rate_limit_info", None)
        if rate_info:
            if payload.get("meta") is None:
                payload["meta"] = {}
            payload["meta"]["rateLimit"] = {
                "limit": rate_info["limit"],
                "remaining": rate_info["remaining"],
                "resetAt": datetime.fromtimestamp(rate_info["reset_at"], tz=dt_timezone.utc).isoformat(),
            }
        return payload