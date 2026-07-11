# apps/core/api/views.py
"""
Base API views for production-ready backend architecture.
"""

from typing import Any, Optional, Dict
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework import status

from .mixins import APIResponseMixin
from .exceptions import _format_errors


class BaseAPIView(APIResponseMixin, GenericAPIView):
    """
    Base API view for all endpoints.

    Provides:
        - Standardized response helpers (success, created, error, etc.)
        - Automatic request_id injection into every response meta.
        - Automatic error formatting via _format_errors() in error_response().
        - Serializer + queryset support via GenericAPIView.
        - Pagination and filtering ready.

    All views in the project must inherit from this class.
    Never use APIView or GenericAPIView directly.

    Error formatting:
        error_response() automatically calls _format_errors() on whatever
        errors value is passed. This guarantees the {code, fields, non_fields}
        contract is enforced whether errors comes from serializer.errors,
        a plain string, or a custom dict. No view needs to call
        _format_errors() manually.
    """

    permission_classes = [AllowAny]

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

    def error_response(
        self,
        *,
        message: str = "Request failed",
        errors: Any = None,
        status_code: int = status.HTTP_400_BAD_REQUEST,
    ):
        """
        Return a standardized error response.

        Automatically formats errors into the {code, fields, non_fields}
        contract via _format_errors(). No view ever needs to call
        _format_errors() manually — passing serializer.errors directly
        is safe and will always produce the correct structured output.

        Use for:
            400 — Validation errors, business logic failures.
            401 — Use unauthorized_response() instead.
            403 — Use forbidden_response() instead.
            404 — Use not_found_response() instead.
            500 — Unexpected server errors.

        Args:
            message:     Human-readable error summary.
            errors:      Raw errors — serializer.errors, plain string,
                         or any dict. Formatted automatically.
            status_code: HTTP status code (default 400).
        """
        return self.build_response(
            message=message,
            errors=_format_errors(errors, status_code) if errors is not None else None,
            status_code=status_code,
        )

    def not_found_response(
        self,
        *,
        message: str = "Resource not found",
    ):
        return self.build_response(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
        )

    def unauthorized_response(
        self,
        *,
        message: str = "Authentication required",
    ):
        return self.build_response(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    def forbidden_response(
        self,
        *,
        message: str = "You do not have permission to perform this action",
    ):
        return self.build_response(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
        )

    def transform_payload(self, payload):
        """
        Inject request_id into every response meta automatically.

        Overrides APIResponseMixin.transform_payload().
        Called by build_response() on every response before it is sent.

        If request has no id attribute (e.g. in tests without
        RequestIDMiddleware), this is a silent no-op.
        """
        request_id = getattr(self.request, "id", None)
        if request_id:
            if payload.get("meta") is None:
                payload["meta"] = {}
            payload["meta"]["request_id"] = request_id
        return payload
# """
# Base API views for production-ready backend architecture.
# """

# from typing import Any,Optional,Dict
# from rest_framework.generics import GenericAPIView
# from rest_framework.permissions import AllowAny
# from rest_framework import status
# from .mixins import APIResponseMixin


# class BaseAPIView(APIResponseMixin, GenericAPIView):
#     """
#     Base API view for all endpoints.

#     Provides:
#         - Standardized response helpers (success, created, error, etc.)
#         - Automatic request_id injection into every response meta.
#         - Serializer + queryset support via GenericAPIView.
#         - Pagination and filtering ready.

#     All views in the project must inherit from this class.
#     Never use APIView or GenericAPIView directly.
#     """

#     permission_classes = [AllowAny]

#     def success_response(
#         self,
#         *,
#         data: Any = None,
#         message: str = "Request successful",
#         status_code: int =   status.HTTP_200_OK,
#         meta: Optional[Dict[str, Any]] = None,  
#     ):
#         return self.build_response(
#             data=data,
#             message=message,
#             status_code=status_code,
#             meta=meta,
#         )
    
#     def created_response(
#         self,
#         *,
#         data: Any = None,
#         message: str = "Resource created successfully",
#         meta: Optional[Dict[str, Any]] = None,
#     ):
#         return self.build_response(
#             data=data,
#             message=message,
#             status_code=status.HTTP_201_CREATED,
#             meta=meta,
#         )
    
#     def error_response(
#         self,
#         *,
#         message: str = "Request failed",
#         errors: Any = None,
#         status_code: int = status.HTTP_400_BAD_REQUEST,
#     ):
        
#         """
#         Return an error response.

#         Use for:
#             400 — Validation errors, business logic failures.
#             401 — Use unauthorized_response() instead.
#             403 — Use forbidden_response() instead.
#             404 — Use not_found_response() instead.
#             500 — Unexpected server errors.

#         Args:
#             message:     Human-readable error summary.
#             errors:      Field-level or structured error detail.
#             status_code: HTTP status code (default 400).
#         """
#         return self.build_response(
#             message=message,
#             errors=errors,
#             status_code=status_code,
#         )
    
#     def not_found_response(
#         self,
#         *,
#         message: str = "Resource not found",
#     ):
#         return self.build_response(
#             message=message,
#             status_code=status.HTTP_404_NOT_FOUND,
#         )
    
#     def unauthorized_response(
#         self,
#         *,
#         message: str = "Authentication required",
#     ):
#         return self.build_response(
#             message=message,
#             status_code=status.HTTP_401_UNAUTHORIZED,
#         )

#     def forbidden_response(
#         self,
#         *,
#         message: str = "You do not have permission to perform this action",
#     ):
#         return self.build_response(
#             message=message,
#             status_code=status.HTTP_403_FORBIDDEN,
#         )
#     def transform_payload(self, payload):
#      """
#         Inject request_id into every response meta automatically.

#         Overrides APIResponseMixin.transform_payload().
#         Called by build_response() on every response before it is sent.

#         If request has no id attribute (e.g. in tests without
#         RequestIDMiddleware), this is a silent no-op.
#     """
#      request_id = getattr(self.request, 'id', None)
#      if request_id:
#          if payload.get('meta') is None:
#              payload['meta'] = {}
#          payload['meta']['request_id'] = request_id
#      return payload