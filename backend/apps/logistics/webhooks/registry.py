# apps/logistics/webhooks/registry.py
from __future__ import annotations

"""
Courier webhook handler registry.

Registry Pattern:
    Maps CourierPartner string values to their handler classes.
    The Celery task looks up the handler here — never imports
    courier classes directly.

    Adding a new courier:
        1. Create apps/logistics/webhooks/newcourier.py
        2. Implement BaseCourierWebhookHandler
        3. Add one line to WEBHOOK_REGISTRY below
        Zero changes required in tasks.py or views.py.

Keys must match CourierPartner.choices values exactly:
    postex, tcs, leopards, trax, instaworld, movex, self_delivery
"""

from apps.logistics.webhooks.postex import PostExWebhookHandler
from apps.logistics.webhooks.tcs import TCSWebhookHandler
from apps.logistics.webhooks.leopards import LeopardsWebhookHandler
from apps.logistics.webhooks.base import BaseCourierWebhookHandler

WEBHOOK_REGISTRY: dict[str, type[BaseCourierWebhookHandler]] = {
    "postex":   PostExWebhookHandler,
    "tcs":      TCSWebhookHandler,
    "leopards": LeopardsWebhookHandler,
}


def get_handler(courier: str) -> BaseCourierWebhookHandler | None:
    """
    Return an instantiated handler for the given courier name.

    Args:
        courier: CourierPartner value string e.g. "postex".

    Returns:
        Instantiated handler or None if courier not in registry.
    """
    handler_class = WEBHOOK_REGISTRY.get(courier)
    if handler_class is None:
        return None
    return handler_class()