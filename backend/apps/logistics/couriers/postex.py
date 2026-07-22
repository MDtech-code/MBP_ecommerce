# apps/logistics/couriers/postex.py
from __future__ import annotations

"""
PostEx outbound API client — shipment booking.

STUB STATUS:
    This file is architecturally complete. The HTTP call structure,
    error handling, timeout handling, InfrastructureError wrapping,
    and response parsing are all production-ready.

    Search for: # ← POSTEX_API_DOCS_REQUIRED
    These markers show the exact lines to update once you have:
        1. PostEx API base URL
        2. Your PostEx API key
        3. Their booking endpoint path
        4. Their exact request payload field names
        5. Their exact response field names for AWB number

How to get PostEx API credentials:
    1. Create seller account at https://postex.pk
    2. Go to Settings → API Integration
    3. Copy your API Key → add to .env as POSTEX_API_KEY
    4. Copy API base URL → add to .env as POSTEX_API_BASE_URL
       (typically https://api.postex.pk or https://merchant.postex.pk/api)
    5. Ask their support for the booking endpoint documentation
       or check their Postman collection in the integration section

Local testing without live credentials:
    Set POSTEX_API_BASE_URL to a mock server like mockoon.com
    or use requests-mock in tests to simulate responses.

Authentication pattern (typical for Pakistani couriers):
    Most use: Authorization: Token <api_key> header
    Some use: X-API-Key header
    Confirm with PostEx documentation.

Booking endpoint (typical):
    POST /api/v1/order/booking
    or
    POST /api/CreateOrder
    Confirm exact path from their documentation.
"""

import logging

import requests
from django.conf import settings

from apps.core.exceptions import InfrastructureError
from apps.core.error_codes import ErrorCode
from apps.logistics.couriers.base import (
    BaseCourierClient,
    BookingRequest,
    BookingResponse,
)

logger = logging.getLogger("apps.logistics")


class PostExCourierClient(BaseCourierClient):
    """
    PostEx outbound API client.

    Implements BaseCourierClient.book_shipment() for PostEx.

    All POSTEX_API_DOCS_REQUIRED markers must be filled in
    once PostEx API documentation is received. Nothing else
    in this file or in ShipmentService needs to change.

    Settings required (add to .env once credentials obtained):
        POSTEX_API_KEY=your_api_key_here
        POSTEX_API_BASE_URL=https://api.postex.pk
    """

    def book_shipment(
        self,
        request: BookingRequest,
        *,
        timeout_seconds: int = 10,
    ) -> BookingResponse:
        """
        Call PostEx API to book a shipment and receive an AWB number.

        Flow:
            1. Build request payload from BookingRequest fields
            2. POST to PostEx booking endpoint with API key auth
            3. Parse AWB number from response
            4. Return BookingResponse

        On any failure (timeout, connection error, API error,
        unexpected response structure) — raises InfrastructureError
        with notify=True so on-call is alerted immediately.

        Args:
            request:         BookingRequest with all shipment details.
            timeout_seconds: Max seconds to wait. Default 10.

        Returns:
            BookingResponse with awb_number from PostEx.

        Raises:
            InfrastructureError 503 — on any API failure.
        """

        api_key      = getattr(settings, "POSTEX_API_KEY", "")
        api_base_url = getattr(settings, "POSTEX_API_BASE_URL", "")

        # ── Credentials check ─────────────────────────────────────────────

        if not api_key or not api_base_url:
            raise InfrastructureError(
                "PostEx API is not configured. "
                "Set POSTEX_API_KEY and POSTEX_API_BASE_URL in .env "
                "after creating your PostEx seller account.",
                code=ErrorCode.COURIER_API_NOT_CONFIGURED,
                notify=True,
                internal={
                    "courier":      "postex",
                    "order_number": request.order_number,
                    "missing":      [
                        k for k, v in {
                            "POSTEX_API_KEY":      api_key,
                            "POSTEX_API_BASE_URL": api_base_url,
                        }.items() if not v
                    ],
                },
            )

        # ── Build request payload ─────────────────────────────────────────

        # ← POSTEX_API_DOCS_REQUIRED
        # Replace all placeholder key names with actual PostEx
        # API field names from their documentation.
        #
        # Example of what this might look like once documented:
        #   "orderRefNo":    request.order_number,
        #   "consigneeName": request.recipient_name,
        #   "consigneePhone": request.recipient_phone,
        #   "address":       request.address_line1,
        #   "city":          request.city,
        #   "cod":           str(request.cod_amount),
        #   "weight":        str(request.weight_kg),
        #
        # Pakistani courier APIs typically use camelCase keys.
        # Confirm exact field names from PostEx documentation.

        payload = {
            # ← POSTEX_API_DOCS_REQUIRED: replace placeholder keys
            "orderRefNo":       request.order_number,
            "consigneeName":    request.recipient_name,
            "consigneePhone":   request.recipient_phone,
            "consigneeAddress": request.address_line1,
            "consigneeCity":    request.city,
            "isCOD":            1 if request.is_cod else 0,
            "codAmount":        str(request.cod_amount),
            "weight":           str(request.weight_kg),
            "pieces":           request.pieces,
            "description":      request.description,
        }

        # ← POSTEX_API_DOCS_REQUIRED: confirm exact endpoint path
        # Common PostEx endpoint patterns:
        #   /api/v1/order/booking
        #   /api/CreateShipment
        #   /api/v2/orders
        endpoint = f"{api_base_url.rstrip('/')}/api/v1/order/booking"

        # ← POSTEX_API_DOCS_REQUIRED: confirm auth header format
        # Common patterns:
        #   Authorization: Token <api_key>
        #   Authorization: Bearer <api_key>
        #   X-API-Key: <api_key>
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

        logger.info(
            "PostExCourierClient.book_shipment: calling API | "
            "order=%s city=%s cod=%s weight=%s",
            request.order_number,
            request.city,
            request.cod_amount,
            request.weight_kg,
        )

        # ── HTTP call ─────────────────────────────────────────────────────

        try:
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=timeout_seconds,
            )

        except requests.Timeout:
            raise InfrastructureError(
                "PostEx API timed out. Please try again in a moment.",
                code=ErrorCode.COURIER_API_TIMEOUT,
                notify=True,
                internal={
                    "courier":          "postex",
                    "order_number":     request.order_number,
                    "timeout_seconds":  timeout_seconds,
                    "endpoint":         endpoint,
                },
            )

        except requests.ConnectionError:
            raise InfrastructureError(
                "Cannot reach PostEx API. "
                "Check your internet connection or PostEx service status.",
                code=ErrorCode.COURIER_API_TIMEOUT,
                notify=True,
                internal={
                    "courier":      "postex",
                    "order_number": request.order_number,
                    "endpoint":     endpoint,
                },
            )

        except requests.RequestException as exc:
            raise InfrastructureError(
                "PostEx API request failed unexpectedly. "
                "The shipment was not booked.",
                code=ErrorCode.COURIER_API_TIMEOUT,
                notify=True,
                internal={
                    "courier":      "postex",
                    "order_number": request.order_number,
                    "error":        str(exc),
                },
            )

        # ── Response validation ───────────────────────────────────────────

        logger.info(
            "PostExCourierClient.book_shipment: response received | "
            "order=%s status_code=%s",
            request.order_number,
            response.status_code,
        )

        # ← POSTEX_API_DOCS_REQUIRED: confirm their success status codes
        # Most courier APIs return 200 for success.
        # Some return 201. Confirm from their documentation.
        if response.status_code not in (200, 201):
            raise InfrastructureError(
                f"PostEx API returned an error response. "
                f"The shipment was not booked. "
                f"Please try again or contact PostEx support.",
                code=ErrorCode.COURIER_API_ERROR,
                notify=True,
                internal={
                    "courier":      "postex",
                    "order_number": request.order_number,
                    "status_code":  response.status_code,
                    "response_body": response.text[:500],
                },
            )

        try:
            response_data = response.json()
        except ValueError:
            raise InfrastructureError(
                "PostEx API returned a non-JSON response. "
                "The shipment booking status is unknown.",
                code=ErrorCode.COURIER_API_ERROR,
                notify=True,
                internal={
                    "courier":       "postex",
                    "order_number":  request.order_number,
                    "response_body": response.text[:500],
                },
            )

        # ── Extract AWB number ────────────────────────────────────────────

        # ← POSTEX_API_DOCS_REQUIRED
        # Replace "trackingNumber" with the actual field name
        # PostEx uses in their booking response JSON.
        # Common field names: "trackingNo", "awb", "cn",
        #                     "trackingNumber", "orderNo"
        #
        # Some APIs nest the AWB inside a data object:
        #   response_data.get("data", {}).get("trackingNumber")
        # Confirm exact structure from PostEx documentation
        # or by inspecting a real API response.

        awb_number = (
            response_data.get("trackingNumber")          # ← POSTEX_API_DOCS_REQUIRED
            or response_data.get("data", {}).get("trackingNumber")
        )

        if not awb_number:
            raise InfrastructureError(
                "PostEx API responded successfully but did not return "
                "a tracking number. The shipment may have been booked — "
                "check PostEx dashboard before retrying.",
                code=ErrorCode.COURIER_API_ERROR,
                notify=True,
                internal={
                    "courier":       "postex",
                    "order_number":  request.order_number,
                    "response_data": response_data,
                },
            )

        # ← POSTEX_API_DOCS_REQUIRED
        # Replace "referenceNo" with PostEx's internal reference field.
        # This is optional — used for debugging only.
        courier_reference = str(
            response_data.get("referenceNo", "")
            or response_data.get("data", {}).get("referenceNo", "")
        )

        # ← POSTEX_API_DOCS_REQUIRED
        # Replace "labelUrl" with PostEx's label download URL field.
        # Not all couriers return this — None is acceptable.
        label_url = (
            response_data.get("labelUrl")
            or response_data.get("data", {}).get("labelUrl")
        )

        logger.info(
            "PostExCourierClient.book_shipment: SUCCESS | "
            "order=%s awb=%s",
            request.order_number,
            awb_number,
        )

        return BookingResponse(
            awb_number=str(awb_number).strip(),
            courier_reference=courier_reference,
            raw_response=response_data,
            label_url=label_url,
        )