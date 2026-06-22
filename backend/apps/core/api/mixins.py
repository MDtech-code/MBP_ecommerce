

from typing import Any, Dict, Optional

from rest_framework.response import Response
from rest_framework import status


class APIResponseMixin:
    """
    Provides standardized API response formatting.

    Standard Response Structure:
    {
        "success": bool,
        "message": str | None,
        "data": Any,
        "errors": Any | None
    }
    """

    MESSAGE_KEY: str = "message"
    ERRORS_KEY: str = "errors"
    DATA_KEY: str = "data"
    SUCCESS_KEY: str = "success"

    def build_response(
        self,
        *,
        data: Any = None,
        message: Optional[str] = None,
        errors: Any = None,
        status_code: int = status.HTTP_200_OK,
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
        }

        response = Response(payload, status=status_code)

        if headers:
            for key, value in headers.items():
                response[key] = value

        return response