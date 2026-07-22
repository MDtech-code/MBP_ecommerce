# apps/logistics/webhooks/tcs.py
from __future__ import annotations

"""
TCS courier webhook handler — STUB.

← TCS_DOCS_REQUIRED throughout this file.
TCS webhook documentation is inconsistent.
Contact TCS integration team for payload schema and HMAC details.

This stub exists so the registry and task work without errors.
verify_signature returns False until implemented — all TCS
webhooks are logged but not processed until this is completed.
"""

import logging

from apps.logistics.webhooks.base import BaseCourierWebhookHandler

logger = logging.getLogger("apps.logistics")


class TCSWebhookHandler(BaseCourierWebhookHandler):
    """TCS webhook handler — stub, not yet implemented."""

    def verify_signature(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        logger.warning(
            "TCSWebhookHandler.verify_signature: "
            "TCS webhook handler is not yet implemented. "
            "Webhook received but rejected. "
            "Implement once TCS documentation is available."
        )
        return False

    def parse_tracking_number(self, payload: dict) -> str | None:
        # ← TCS_DOCS_REQUIRED
        return None

    def parse_status(self, payload: dict) -> str | None:
        # ← TCS_DOCS_REQUIRED
        return None