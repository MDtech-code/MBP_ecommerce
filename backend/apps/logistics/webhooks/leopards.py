# apps/logistics/webhooks/leopards.py
from __future__ import annotations

"""
Leopards courier webhook handler — STUB.

← LEOPARDS_DOCS_REQUIRED throughout this file.
Same stub pattern as TCS.
"""

import logging

from apps.logistics.webhooks.base import BaseCourierWebhookHandler

logger = logging.getLogger("apps.logistics")


class LeopardsWebhookHandler(BaseCourierWebhookHandler):
    """Leopards webhook handler — stub, not yet implemented."""

    def verify_signature(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        logger.warning(
            "LeopardsWebhookHandler.verify_signature: "
            "Leopards webhook handler is not yet implemented. "
            "Webhook received but rejected."
        )
        return False

    def parse_tracking_number(self, payload: dict) -> str | None:
        # ← LEOPARDS_DOCS_REQUIRED
        return None

    def parse_status(self, payload: dict) -> str | None:
        # ← LEOPARDS_DOCS_REQUIRED
        return None