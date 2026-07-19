"""
apps/core/api/views.py
──────────────────────


All views in the project must inherit from BaseAPIView.
Never use APIView or GenericAPIView directly to stay consistance accross backend 
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny

from apps.core.exceptions import DomainError
from .exceptions import (
    _format_drf_errors,
    _non_fields_domain,
    _status_to_error_code,

)
from .mixins import APIResponseMixin


class BaseAPIView(APIResponseMixin, GenericAPIView):
    """
    Base API view for all endpoints.

    Provides
    ────────
    - Standardized response helpers: success_response, created_response,
      error_response, domain_error_response, not_found_response,
      unauthorized_response, forbidden_response.
    - Automatic request_id injection into every response meta.
    - Consistent errors envelope on every response — success or failure —
      so the frontend never receives two different shapes for the same
      semantic situation.

    Response helper decision guide
    ──────────────────────────────
    serializer.errors, bad raw input      → error_response()
    DomainError caught manually in view   → domain_error_response()
    Resource does not exist               → not_found_response()
    Auth credentials missing              → unauthorized_response()
    Auth present but access denied        → forbidden_response()

    Prefer raising over catching
    ────────────────────────────
    In most cases you should NOT catch DomainError or InfrastructureError
    in views at all. Raise them in your service/domain layer and let
    custom_exception_handler convert them to responses automatically.
    Use domain_error_response() only when a view constructs a domain error
    directly without a service layer in between (rare).

    Envelope consistency guarantee
    ──────────────────────────────
    Every helper — including not_found_response, unauthorized_response, and
    forbidden_response — produces the same full errors envelope that the
    global exception handler produces for the equivalent exception. The
    frontend always receives:
        { code, fields, non_fields: { category, message, code, extra } }
    and never receives errors: null for these helpers.
    """

    permission_classes = [AllowAny]

    # ── Success helpers ───────────────────────────────────────────────────────

    def success_response(
        self,
        *,
        data: Any = None,
        message: str = "Request successful",
        status_code: int = status.HTTP_200_OK,
        meta: Optional[Dict[str, Any]] = None,
    ):
        return self.build_response(
            data=data,
            message=message,
            status_code=status_code,
            meta=meta,
        )

    def created_response(
        self,
        *,
        data: Any = None,
        message: str = "Resource created successfully",
        meta: Optional[Dict[str, Any]] = None,
    ):
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
    ):
        """
        Return a standardized error response for DRF / serializer errors.

        Automatically formats errors into the {code, fields, non_fields}
        envelope via _format_drf_errors(). Callers pass serializer.errors,
        a plain string, or any dict — formatting is handled here, never
        in the view.

        Use for:
            - serializer.errors  (field-level validation failures)
            - Plain string error messages
            - Raw DRF error dicts

        Do NOT use for domain errors — use domain_error_response() so the
        frontend receives category="domain" instead of category="validation".

        Args:
            message:     Human-readable error summary.
            errors:      Raw errors — serializer.errors, string, or dict.
            status_code: HTTP status code (default 400).
        """
        return self.build_response(
            message=message,
            errors=_format_drf_errors(errors, status_code) if errors is not None else None,
            status_code=status_code,
        )

    def domain_error_response(self, *, exc: DomainError):
        """
        Return a standardized error response from a DomainError instance.

        Produces the identical envelope that custom_exception_handler produces
        for an uncaught DomainError — category="domain", correct status code,
        client_extra forwarded, internal excluded.

        When to use this
        ────────────────
        Only when a view constructs and handles a DomainError itself, without
        a service layer in between. In all other cases, raise DomainError in
        your service layer and let the global handler catch it. Do not catch
        and re-wrap what the handler would already handle correctly.

        Args:
            exc: The DomainError instance to convert to a response.

        Example::

            def post(self, request):
                if not request.user.has_active_subscription():
                    return self.domain_error_response(
                        exc=DomainError(
                            "An active subscription is required.",
                            code="subscription_required",
                        )
                    )
        """
        return self.build_response(
            message=exc.message,
            errors={
                "code":       _status_to_error_code(exc.status_code),
                "fields":     None,
                "non_fields": _non_fields_domain(exc),
            },
            status_code=exc.status_code,
        )

    def not_found_response(self, *, message: str = "Resource not found"):
        """
        Return a 404 response with a full structured errors envelope.

        Produces the same shape as the global handler for a 404 exception:
            errors.code             = "not_found"
            errors.non_fields.category = "validation"
            errors.non_fields.message  = message
        """
        return self.build_response(
            message=message,
            errors=_format_drf_errors(message, status.HTTP_404_NOT_FOUND),
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def unauthorized_response(self, *, message: str = "Authentication required"):
        """
        Return a 401 response with a full structured errors envelope.

        Produces the same shape as the global handler for a 401 exception:
            errors.code             = "authentication_error"
            errors.non_fields.category = "validation"
            errors.non_fields.message  = message
        """
        return self.build_response(
            message=message,
            errors=_format_drf_errors(message, status.HTTP_401_UNAUTHORIZED),
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    def forbidden_response(
        self,
        *,
        message: str = "You do not have permission to perform this action",
    ):
        """
        Return a 403 response with a full structured errors envelope.

        Produces the same shape as the global handler for a 403 exception:
            errors.code             = "permission_error"
            errors.non_fields.category = "validation"
            errors.non_fields.message  = message
        """
        return self.build_response(
            message=message,
            errors=_format_drf_errors(message, status.HTTP_403_FORBIDDEN),
            status_code=status.HTTP_403_FORBIDDEN,
        )

    # ── Payload hook ──────────────────────────────────────────────────────────

    def transform_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inject request_id into every response meta automatically.

        Overrides APIResponseMixin.transform_payload().
        Called by build_response() on every response before it is sent.

        If the request has no id attribute (e.g. in tests running without
        RequestIDMiddleware) this is a silent no-op — meta stays whatever
        the caller passed, or None if nothing was passed.
        """
        request_id = getattr(self.request, "id", None)
        if request_id:
            if payload.get("meta") is None:
                payload["meta"] = {}
            payload["meta"]["request_id"] = request_id
        return payload
