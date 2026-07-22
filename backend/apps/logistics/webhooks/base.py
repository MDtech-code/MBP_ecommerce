# apps/logistics/webhooks/base.py
from __future__ import annotations

"""
Abstract base class for courier webhook handlers.

Every courier integration must implement this interface.
The Celery task only knows this interface — never the
concrete courier class directly.

Strategy Pattern:
    Each courier is a concrete strategy.
    The task is the context that uses the strategy.
    Adding a new courier = add a new class here + one line in registry.

Implementation contract:
    verify_signature() — must return bool, never raise.
                         Failure = log + return False.
    parse_tracking_number() — returns str or None.
                              None = payload did not contain AWB.
    parse_status() — returns Shipment.Status string or None.
                     None = courier status not mappable to our system.
    Both parse methods receive the already-parsed dict payload —
    not the raw request body.
"""

from abc import ABC, abstractmethod


class BaseCourierWebhookHandler(ABC):
    """
    Abstract courier webhook handler.

    All concrete courier handlers must inherit from this class
    and implement all three abstract methods.

    Usage:
        handler = PostExWebhookHandler()
        if not handler.verify_signature(payload, headers, secret):
            # reject webhook
        tracking = handler.parse_tracking_number(payload)
        status   = handler.parse_status(payload)
    """

    @abstractmethod
    def verify_signature(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        """
        Verify the HMAC signature of the incoming webhook.

        Args:
            payload: Parsed JSON payload dict from courier request.
            headers: HTTP headers dict from courier request.
            secret:  Courier-specific webhook secret from settings.

        Returns:
            True if signature is valid.
            False if signature is missing, malformed, or does not match.
            Never raises — caller treats any exception as False.
        """

    @abstractmethod
    def parse_tracking_number(self, payload: dict) -> str | None:
        """
        Extract the AWB tracking number from the webhook payload.

        Args:
            payload: Parsed JSON payload dict from courier request.

        Returns:
            Tracking number string if found and non-empty.
            None if the field is missing or empty.
        """

    @abstractmethod
    def parse_status(self, payload: dict) -> str | None:
        """
        Map courier-specific status string to Shipment.Status value.

        Each courier uses different status terminology.
        This method normalizes their string to our internal enum value.

        Args:
            payload: Parsed JSON payload dict from courier request.

        Returns:
            Shipment.Status string value (e.g. "delivered", "in_transit").
            None if courier status is unknown or not mappable.
        """