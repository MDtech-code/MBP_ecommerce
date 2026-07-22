# apps/logistics/couriers/tcs.py
from __future__ import annotations

"""
TCS outbound API client — STUB.

← TCS_API_DOCS_REQUIRED throughout this file.

TCS API documentation:
    Contact TCS integration team directly.
    Their API is less documented than PostEx.
    Ask for: endpoint URL, auth method, payload schema,
             AWB field name in response.

Settings required (add to .env once credentials obtained):
    TCS_API_KEY=your_api_key_here
    TCS_API_BASE_URL=https://api.tcs.com.pk

This stub raises InfrastructureError immediately so any attempt
to use TCS before implementation is caught at development time,
not silently ignored.
"""

import logging

from apps.core.exceptions import InfrastructureError
from apps.core.error_codes import ErrorCode
from apps.logistics.couriers.base import (
    BaseCourierClient,
    BookingRequest,
    BookingResponse,
)

logger = logging.getLogger("apps.logistics")


class TCSCourierClient(BaseCourierClient):
    """TCS outbound API client — not yet implemented."""

    def book_shipment(
        self,
        request: BookingRequest,
        *,
        timeout_seconds: int = 10,
    ) -> BookingResponse:
        """
        ← TCS_API_DOCS_REQUIRED
        Implement once TCS API documentation is obtained.

        Follow the same pattern as PostExCourierClient:
            1. Check credentials from settings
            2. Build payload with TCS field names
            3. POST to TCS endpoint
            4. Handle timeout and connection errors
            5. Extract AWB from response
            6. Return BookingResponse

        Raises InfrastructureError until implemented.
        """
        raise InfrastructureError(
            "TCS courier API integration is not yet implemented. "
            "Use PostEx or enter AWB manually for TCS shipments.",
            code=ErrorCode.COURIER_API_NOT_CONFIGURED,
            notify=False,
            internal={
                "courier":      "tcs",
                "order_number": request.order_number,
                "reason":       "TCS client stub — not implemented",
            },
        )