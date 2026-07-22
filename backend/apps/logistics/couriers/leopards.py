# apps/logistics/couriers/leopards.py
from __future__ import annotations

"""
Leopards courier outbound API client — STUB.

← LEOPARDS_API_DOCS_REQUIRED throughout this file.

Leopards API documentation:
    https://leopardscourier.com (API section after account creation)
    They have a public API documentation page.
    Ask for: merchant ID, API key, booking endpoint, payload schema.

Settings required (add to .env once credentials obtained):
    LEOPARDS_API_KEY=your_api_key_here
    LEOPARDS_API_BASE_URL=https://merchantapi.leopardscourier.com

This stub raises InfrastructureError immediately.
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


class LeopardsCourierClient(BaseCourierClient):
    """Leopards outbound API client — not yet implemented."""

    def book_shipment(
        self,
        request: BookingRequest,
        *,
        timeout_seconds: int = 10,
    ) -> BookingResponse:
        """
        ← LEOPARDS_API_DOCS_REQUIRED
        Implement once Leopards API documentation is obtained.
        Raises InfrastructureError until implemented.
        """
        raise InfrastructureError(
            "Leopards courier API integration is not yet implemented. "
            "Use PostEx or enter AWB manually for Leopards shipments.",
            code=ErrorCode.COURIER_API_NOT_CONFIGURED,
            notify=False,
            internal={
                "courier":      "leopards",
                "order_number": request.order_number,
                "reason":       "Leopards client stub — not implemented",
            },
        )