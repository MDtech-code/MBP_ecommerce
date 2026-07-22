# apps/logistics/couriers/registry.py
from __future__ import annotations

"""
Outbound courier client registry.

Registry Pattern — mirrors the webhook handler registry.
ShipmentService looks up the correct client here.
Adding a new courier = one class + one line in COURIER_REGISTRY.
Zero changes required in ShipmentService.

Keys must match CourierPartner.choices values exactly:
    postex, tcs, leopards, trax, instaworld, movex, self_delivery

SELF_DELIVERY note:
    self_delivery has no external API — admin enters AWB manually.
    It is intentionally absent from this registry.
    ShipmentService checks for self_delivery before registry lookup
    and keeps Phase 1 manual flow for that courier.
"""

from apps.logistics.couriers.base import BaseCourierClient
from apps.logistics.couriers.postex import PostExCourierClient
from apps.logistics.couriers.tcs import TCSCourierClient
from apps.logistics.couriers.leopards import LeopardsCourierClient

COURIER_REGISTRY: dict[str, type[BaseCourierClient]] = {
    "postex":   PostExCourierClient,
    "tcs":      TCSCourierClient,
    "leopards": LeopardsCourierClient,
}


def get_courier_client(courier: str) -> BaseCourierClient | None:
    """
    Return an instantiated client for the given courier name.

    Args:
        courier: CourierPartner value string e.g. "postex".

    Returns:
        Instantiated client or None if courier not in registry
        (e.g. self_delivery which has no API).
    """
    client_class = COURIER_REGISTRY.get(courier)
    if client_class is None:
        return None
    return client_class()