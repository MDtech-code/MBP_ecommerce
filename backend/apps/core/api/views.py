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


class BaseAPIView(APIResponseMixin, GenericAPIView):
    """
    Base API view for all endpoints.

    Provides standardized response helpers so every endpoint in the
    project returns the same envelope shape, whether the response
    represents success, a raised exception the global handler caught,
    or a manually constructed error a view builds inline.

    Response helper decision guide
    ─────────────────────────────────
    serializer.errors, bad raw input      → error_response()
    A BaseAppError caught/built in a view → app_error_response()
    Resource does not exist               → not_found_response()
    Auth credentials missing              → unauthorized_response()
    Auth present but access denied        → forbidden_response()

    Envelope consistency guarantee
    ─────────────────────────────────
    not_found_response(), unauthorized_response(), and forbidden_response()
    each raise the equivalent BaseAppError subclass and return the same
    envelope custom_exception_handler would produce for that exception —
    both paths call build_envelope_from_exception() on the same instance,
    so there is exactly one function in the codebase that knows how to
    describe a BaseAppError, not two independently maintained ones.
    """

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
        """
        Return a standardized success response.

        Args:
            data: The response payload.
            message: Human-readable summary.
            status_code: HTTP status, expected to be 2xx.
            meta: Additional metadata (pagination, etc).
        """
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
        """Return a standardized 201 Created response."""
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
        """
        Return a standardized error response for raw DRF-shaped errors.

        Use this specifically for serializer.errors, plain strings, or
        raw DRF error dicts — anything that is not already a BaseAppError
        instance. This is why it still uses _format_drf_errors rather
        than build_envelope_from_exception: there is no exception
        instance here to ask for its own envelope, only raw data DRF
        produced, which is exactly the case _format_drf_errors exists for.

        For a BaseAppError instance, use app_error_response() instead, so
        the response is built the same way the global handler would build
        it for the same exception, rather than reformatted here.

        Args:
            message: Human-readable error summary.
            errors: serializer.errors, a plain string, or a raw dict.
            status_code: HTTP status code.
        """
        return self.build_response(
            message=message,
            errors=_format_drf_errors(errors, status_code) if errors is not None else None,
            status_code=status_code,
        )

    def app_error_response(self, *, exc: BaseAppError) -> Response:
        """
        Return a standardized error response built from a BaseAppError
        instance the view constructed or caught directly.

        Delegates entirely to build_envelope_from_exception(exc) — the
        same function custom_exception_handler calls for an uncaught
        exception of the same type. This is what guarantees "raise the
        exception" and "call this helper with the same exception" produce
        byte-identical output: both paths call the identical function.

        When to use this
        ────────────────────
        Only when a view needs to return immediately rather than raise
        (e.g. inside a loop where control flow needs to continue after
        returning). In every other case, prefer raising the BaseAppError
        subclass directly and letting the global handler process it —
        that keeps error handling out of the view's control flow entirely.

        Args:
            exc: The BaseAppError instance (any subclass) to convert.

        Example:
            def post(self, request):
                if not request.user.has_active_subscription():
                    return self.app_error_response(
                        exc=DomainError(
                            "An active subscription is required.",
                            code="subscription_required",
                        )
                    )
        """
        return self.build_response(
            message=exc.message,
            errors=build_envelope_from_exception(exc),
            status_code=exc.status_code,
        )

    def not_found_response(
        self, *, message: str = "The requested resource was not found."
    ) -> Response:
        """
        Return a 404 response with the standard errors envelope.

        Builds a NotFoundError and hands it to app_error_response(), so
        the output is identical to what would be produced by raising
        NotFoundError(message) and letting the global handler catch it.

        Args:
            message: Human-readable explanation of what was not found.
        """
        return self.app_error_response(exc=NotFoundError(message))

    def unauthorized_response(
        self, *, message: str = "Authentication required."
    ) -> Response:
        """
        Return a 401 response with the standard errors envelope.

        Builds an AuthenticationRequiredError and hands it to
        app_error_response(), for the same equivalence guarantee as
        not_found_response().

        Args:
            message: Human-readable explanation of the missing credentials.
        """
        return self.app_error_response(exc=AuthenticationRequiredError(message))

    def forbidden_response(
        self,
        *,
        message: str = "You do not have permission to perform this action.",
    ) -> Response:
        """
        Return a 403 response with the standard errors envelope.

        Builds a PermissionDeniedError and hands it to app_error_response(),
        for the same equivalence guarantee as not_found_response().

        Args:
            message: Human-readable explanation of the denied access.
        """
        return self.app_error_response(exc=PermissionDeniedError(message))

    # ── Payload hook ──────────────────────────────────────────────────────────

    def transform_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Inject request_id into every response's meta automatically.

        Overrides APIResponseMixin.transform_payload(), called by
        build_response() on every response before it is sent. If the
        request has no id attribute (e.g. RequestIDMiddleware is not
        active, such as in a test), this is a silent no-op — meta is
        left as whatever the caller passed, or None.

        Args:
            payload: The assembled envelope dict, before being sent.
        """
        request_id = getattr(self.request, "id", None)
        if request_id:
            if payload.get("meta") is None:
                payload["meta"] = {}
            payload["meta"]["request_id"] = request_id
        return payload