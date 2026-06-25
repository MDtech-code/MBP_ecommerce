"""
Base API views for production-ready backend architecture.
"""

from typing import Any,Optional,Dict
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework import status
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
        status_code: int =   status.HTTP_200_OK,
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
        return self.build_response(
            message=message,
            errors=errors,
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
     """Add request ID to every response meta automatically."""
     request_id = getattr(self.request, 'id', None)
     if request_id:
         if payload.get('meta') is None:
             payload['meta'] = {}
         payload['meta']['request_id'] = request_id
     return payload