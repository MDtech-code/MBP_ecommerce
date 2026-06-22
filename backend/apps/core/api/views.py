"""
Base API views for production-ready backend architecture.
"""

from typing import Any
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny

from .mixins import APIResponseMixin


class BaseAPIView(APIResponseMixin, GenericAPIView):
    """
    Base API view for all CRUD-based endpoints.

    Features:
    - Standardized response format
    - Serializer support
    - Queryset support
    - Pagination & filtering ready
    - Easily extendable
    """

    permission_classes = [AllowAny]

    def success_response(
        self,
        *,
        data: Any = None,
        message: str = "Request successful",
        status_code: int = 200,
    ):
        return self.build_response(
            data=data,
            message=message,
            status_code=status_code,
        )

    def error_response(
        self,
        *,
        message: str = "Request failed",
        errors: Any = None,
        status_code: int = 400,
    ):
        return self.build_response(
            message=message,
            errors=errors,
            status_code=status_code,
        )