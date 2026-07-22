# apps/logistics/couriers/base.py
from __future__ import annotations

"""
Abstract base class for outbound courier API clients.

Every courier integration must implement this interface.
ShipmentService.create_shipment() only knows this interface —
never the concrete courier class directly.

Strategy Pattern (same as webhook handlers):
    Each courier is a concrete strategy.
    ShipmentService is the context that uses the strategy.
    Adding a new courier = add one class + one line in the
    courier registry. Zero changes to service logic.

Sync vs Async decision (Phase 4):
    All methods are synchronous — Option A chosen deliberately.
    The call happens in the request cycle. Admin waits 2-5 seconds.
    InfrastructureError handles courier API failures cleanly.

Migration path to Option B (Celery) when needed:
    1. Add Shipment.Status.PENDING_LABEL choice to models.py
    2. Create migration
    3. In create_shipment(): create shipment with PENDING_LABEL
    4. Dispatch Celery task with shipment.pk
    5. Task calls book_shipment() and updates to LABEL_CREATED
    6. The base interface below does NOT change
    7. The PostEx client below does NOT change
    Only the orchestration in ShipmentService changes.
    This is why the interface is kept clean and stateless.

Timeout contract:
    All concrete implementations MUST respect the timeout_seconds
    argument. Never make an unbounded HTTP call to an external API.
    Default is 10 seconds — sufficient for Pakistani courier APIs.
    InfrastructureError is raised on timeout, not a raw exception.

Error contract:
    book_shipment() raises InfrastructureError on any failure.
    Never returns None. Never swallows exceptions silently.
    Caller (ShipmentService) does not need to check return value
    validity — if it returns, it succeeded.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class BookingRequest:
    """
    Courier-agnostic shipment booking request.

    Built by ShipmentService from Order and Shipment data.
    Passed to the courier client's book_shipment() method.
    The courier client maps these fields to its own API payload.

    All fields are sourced from already-validated model data —
    no validation needed here.

    Fields:
        order_number:       Your internal order reference.
        tracking_number:    Pre-assigned AWB if courier requires it
                            upfront. Empty string if courier assigns it.
        recipient_name:     From OrderShippingAddress.full_name.
        recipient_phone:    From OrderShippingAddress.phone.
        address_line1:      From OrderShippingAddress.address_line1.
        address_line2:      From OrderShippingAddress.address_line2.
        city:               From OrderShippingAddress.city.
        province:           From OrderShippingAddress.province.
        postal_code:        From OrderShippingAddress.postal_code.
        is_cod:             True for COD orders.
        cod_amount:         PKR amount courier collects on delivery.
                            Zero for non-COD orders.
        weight_kg:          Parcel weight in kilograms.
        pieces:             Number of parcels in this shipment.
                            Almost always 1 for ecommerce.
        description:        Brief contents description for courier label.
    """

    order_number:    str
    tracking_number: str
    recipient_name:  str
    recipient_phone: str
    address_line1:   str
    address_line2:   str
    city:            str
    province:        str
    postal_code:     str
    is_cod:          bool
    cod_amount:      Decimal
    weight_kg:       Decimal
    pieces:          int
    description:     str


@dataclass(frozen=True)
class BookingResponse:
    """
    Courier-agnostic shipment booking response.

    Returned by book_shipment() on success.
    ShipmentService reads awb_number to store as tracking_number.

    Fields:
        awb_number:         Airway Bill number assigned by courier.
                            This is what gets stored as
                            Shipment.tracking_number.
        courier_reference:  Courier's internal reference ID if any.
                            Stored in Shipment.raw_courier_response.
        raw_response:       Complete raw API response dict.
                            Stored in Shipment.raw_courier_response
                            for debugging API issues.
        label_url:          URL to downloadable PDF label if courier
                            provides one. None if not available.
    """

    awb_number:        str
    courier_reference: str
    raw_response:      dict
    label_url:         str | None = None


class BaseCourierClient(ABC):
    """
    Abstract courier API client.

    All concrete courier clients must inherit from this class
    and implement book_shipment().

    Usage:
        client = PostExCourierClient()
        response = client.book_shipment(request, timeout_seconds=10)
        # response.awb_number is the tracking number to store
    """

    @abstractmethod
    def book_shipment(
        self,
        request: BookingRequest,
        *,
        timeout_seconds: int = 10,
    ) -> BookingResponse:
        """
        Call the courier API to book a shipment and get an AWB number.

        This is a synchronous HTTP call. It blocks until the courier
        API responds or the timeout is reached.

        Args:
            request:         BookingRequest with all shipment details.
            timeout_seconds: Maximum seconds to wait for API response.
                             Raises InfrastructureError on timeout.

        Returns:
            BookingResponse with awb_number and raw_response.
            Never returns None — raises on any failure.

        Raises:
            InfrastructureError — on timeout, connection error,
                                  API error response, or any other
                                  failure. Always notify=True so
                                  on-call is alerted.
        """