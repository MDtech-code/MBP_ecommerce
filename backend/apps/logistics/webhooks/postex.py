# apps/logistics/webhooks/postex.py
from __future__ import annotations

"""
PostEx courier webhook handler.

IMPORTANT — STUB STATUS:
    This file has placeholder markers wherever PostEx-specific
    field names and HMAC details are needed.

    Search for: # ← POSTEX_DOCS_REQUIRED
    These are the exact lines to update once you have:
        1. PostEx webhook documentation
        2. A sample webhook payload from their dashboard
        3. Their HMAC algorithm and header name confirmed

    Everything else — the task orchestration, WebhookLog saving,
    ShipmentService call — is complete and will not change.

PostEx webhook documentation:
    https://postex.pk (API/Integration section after account creation)
    Ask their support for: webhook payload schema + HMAC header name

Registration steps:
    1. Create seller account at postex.pk
    2. Go to Settings → API Integration
    3. Copy Webhook Secret → add to .env as POSTEX_WEBHOOK_SECRET
    4. Set webhook URL: https://yourdomain.com/api/logistics/webhooks/postex/
    5. Use their test webhook button to send a sample payload
    6. Check WebhookLog in admin — payload field shows exact structure
    7. Fill in the POSTEX_DOCS_REQUIRED markers below
"""

import hashlib
import hmac
import json
import logging

from apps.logistics.models import Shipment
from apps.logistics.webhooks.base import BaseCourierWebhookHandler

logger = logging.getLogger("apps.logistics")


# ─────────────────────────────────────────────────────────────────────────────
# STATUS MAPPING
# ─────────────────────────────────────────────────────────────────────────────

# Maps PostEx status strings → our Shipment.Status values.
#
# ← POSTEX_DOCS_REQUIRED
# Replace the placeholder keys with actual PostEx status strings.
# PostEx sends a status field in their payload — the exact string
# values come from their documentation or a real webhook payload.
#
# Example of what this might look like once documented:
#   "Shipment Booked"     → LABEL_CREATED
#   "Shipment Picked Up"  → PICKED_UP
#   "In Transit"          → IN_TRANSIT
#   "Out For Delivery"    → OUT_FOR_DELIVERY
#   "Delivered"           → DELIVERED
#   "Return Requested"    → RETURN_REQUESTED
#   "RTO In Transit"      → RTO_IN_TRANSIT
#   "RTO"                 → RTO_DELIVERED
#
# Until confirmed, all keys are placeholders.

POSTEX_STATUS_MAP: dict[str, str] = {
    # ← POSTEX_DOCS_REQUIRED: replace keys with real PostEx status strings
    "POSTEX_STATUS_BOOKED":        Shipment.Status.LABEL_CREATED,
    "POSTEX_STATUS_PICKED_UP":     Shipment.Status.PICKED_UP,
    "POSTEX_STATUS_IN_TRANSIT":    Shipment.Status.IN_TRANSIT,
    "POSTEX_STATUS_OUT_DELIVERY":  Shipment.Status.OUT_FOR_DELIVERY,
    "POSTEX_STATUS_DELIVERED":     Shipment.Status.DELIVERED,
    "POSTEX_STATUS_RETURN_REQ":    Shipment.Status.RETURN_REQUESTED,
    "POSTEX_STATUS_RTO_TRANSIT":   Shipment.Status.RTO_IN_TRANSIT,
    "POSTEX_STATUS_RTO":           Shipment.Status.RTO_DELIVERED,
    "POSTEX_STATUS_LOST":          Shipment.Status.LOST,
}


class PostExWebhookHandler(BaseCourierWebhookHandler):
    """
    PostEx-specific webhook handler.

    Implements HMAC verification, tracking number extraction,
    and status mapping for PostEx webhook payloads.

    All placeholder markers (← POSTEX_DOCS_REQUIRED) must be
    filled in once PostEx documentation or a real payload is available.
    """

    def verify_signature(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        """
        Verify PostEx HMAC signature.

        ← POSTEX_DOCS_REQUIRED
        PostEx sends an HMAC signature in a specific header.
        Once documented, update:
            1. SIGNATURE_HEADER — the exact header name PostEx uses
               e.g. "X-PostEx-Signature" or "X-Hub-Signature-256"
            2. The algorithm — HMAC-SHA256 is standard but confirm
            3. Whether they sign the raw body or a specific field

        Current implementation uses HMAC-SHA256 on raw JSON body.
        This is the most common pattern but may need adjustment.

        Args:
            payload: Parsed JSON dict — re-serialized for signing.
            headers: Request headers dict — signature extracted from here.
            secret:  POSTEX_WEBHOOK_SECRET from settings.

        Returns:
            True if signature matches.
            False if header missing, secret empty, or mismatch.
        """

        # ← POSTEX_DOCS_REQUIRED: confirm exact header name
        SIGNATURE_HEADER = "X-PostEx-Signature"

        if not secret:
            logger.warning(
                "PostExWebhookHandler.verify_signature: "
                "POSTEX_WEBHOOK_SECRET is empty — "
                "set it in .env after PostEx account creation."
            )
            return False

        received_signature = headers.get(SIGNATURE_HEADER, "")
        if not received_signature:
            logger.warning(
                "PostExWebhookHandler.verify_signature: "
                "signature header '%s' missing from request.",
                SIGNATURE_HEADER,
            )
            return False

        try:
            # ← POSTEX_DOCS_REQUIRED: confirm they sign raw JSON body
            # Re-serialize payload to bytes for signing
            body_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

            expected = hmac.new(
                secret.encode("utf-8"),
                body_bytes,
                hashlib.sha256,
            ).hexdigest()

            # Use hmac.compare_digest — timing-safe comparison
            # Prevents timing attacks on signature verification
            is_valid = hmac.compare_digest(expected, received_signature)

            if not is_valid:
                logger.warning(
                    "PostExWebhookHandler.verify_signature: "
                    "signature mismatch — possible fake webhook."
                )

            return is_valid

        except Exception:
            logger.exception(
                "PostExWebhookHandler.verify_signature: "
                "unexpected error during verification."
            )
            return False

    def parse_tracking_number(self, payload: dict) -> str | None:
        """
        Extract AWB tracking number from PostEx payload.

        ← POSTEX_DOCS_REQUIRED
        Replace "trackingNumber" with the actual field name
        PostEx uses in their webhook payload.
        Common field names: "tracking_number", "awb", "cn",
                            "trackingNumber", "order_id"

        Args:
            payload: Parsed JSON dict from PostEx webhook.

        Returns:
            Tracking number string or None if field missing/empty.
        """

        # ← POSTEX_DOCS_REQUIRED: replace with real field name
        tracking = payload.get("trackingNumber")  # placeholder key

        if not tracking:
            logger.warning(
                "PostExWebhookHandler.parse_tracking_number: "
                "tracking number field missing or empty in payload."
            )
            return None

        return str(tracking).strip()

    def parse_status(self, payload: dict) -> str | None:
        """
        Map PostEx status string to Shipment.Status value.

        ← POSTEX_DOCS_REQUIRED
        Replace "orderStatus" with the actual field name
        PostEx uses in their webhook payload.
        Common field names: "status", "orderStatus",
                            "shipmentStatus", "event"

        Args:
            payload: Parsed JSON dict from PostEx webhook.

        Returns:
            Shipment.Status string value or None if unmappable.
        """

        # ← POSTEX_DOCS_REQUIRED: replace with real field name
        raw_status = payload.get("orderStatus")  # placeholder key

        if not raw_status:
            logger.warning(
                "PostExWebhookHandler.parse_status: "
                "status field missing or empty in payload."
            )
            return None

        mapped = POSTEX_STATUS_MAP.get(str(raw_status).strip())

        if mapped is None:
            logger.warning(
                "PostExWebhookHandler.parse_status: "
                "unmapped PostEx status '%s' — "
                "add to POSTEX_STATUS_MAP once documented.",
                raw_status,
            )

        return mapped