# apps/logistics/selectors/shipment.py
from __future__ import annotations

"""
Logistics selectors — database reads for shipment retrieval.

Responsibility:
    All Shipment and ShipmentStatusLog database queries live here.
    Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Ownership enforcement:
    Customer-facing queries scope by order__user to prevent
    tracking number enumeration attacks.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db.models import QuerySet

from apps.logistics.models import Shipment

logger = logging.getLogger("apps.logistics")


def get_shipment_by_tracking(tracking_number: str) -> Shipment:
    """
    Fetch a single shipment by its AWB tracking number.

    Loads status_logs and order with shipping_address in one
    query set to avoid N+1 on detail and webhook processing views.

    Args:
        tracking_number: AWB string assigned by courier.

    Returns:
        Shipment instance with prefetched status_logs.

    Raises:
        Shipment.DoesNotExist — caller returns 404.
    """
    return (
        Shipment.objects
        .select_related(
            "order",
            "order__shipping_address",
            "order__user",
        )
        .prefetch_related("status_logs")
        .get(tracking_number=tracking_number)
    )


def get_shipment_for_order(order) -> Shipment | None:
    """
    Return the active original shipment for an order, or None.

    Filters by shipment_type=ORIGINAL — reshipments and return
    pickups are separate records and excluded here.
    Used by the customer-facing tracking endpoint.

    Args:
        order: Order instance whose shipment to retrieve.

    Returns:
        Shipment instance or None if no shipment created yet.
    """
    return (
        Shipment.objects
        .prefetch_related("status_logs")
        .filter(
            order=order,
            shipment_type=Shipment.ShipmentType.ORIGINAL,
        )
        .exclude(status__in=[
            Shipment.Status.RTO_DELIVERED,
            Shipment.Status.LOST,
        ])
        .order_by("-created_at")
        .first()
    )
