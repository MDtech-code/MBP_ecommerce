# apps/payments/gateways/safepay.py
from __future__ import annotations

"""
Safepay gateway client — stub implementation.

Full implementation requires:
    SAFEPAY_API_KEY
    SAFEPAY_WEBHOOK_SECRET

in Django settings.

Safepay uses a token-based flow — initiate_payment() returns
a payment_token, not a redirect_url. The frontend uses this
token to render the Safepay hosted checkout iframe/redirect.

HMAC algorithm for Safepay webhooks: HMAC-SHA256
Signature field in headers: X-SFPY-SIGNATURE

Reference: Safepay API Documentation
"""

import hashlib
import hmac
import json
import logging
from decimal import Decimal

from django.conf import settings

from apps.core.exceptions import InfrastructureError
from apps.core.error_codes import ErrorCode
from apps.payments.gateways.base import (
    BaseGatewayClient,
    GatewayInitRequest,
    GatewayInitResponse,
    WebhookParseResult,
)

logger = logging.getLogger("apps.payments")


class SafepayGatewayClient(BaseGatewayClient):
    """
    Safepay payment gateway client.

    Stub — raises InfrastructureError on initiate_payment() until
    credentials are configured in settings.

    Safepay webhook signature is in the X-SFPY-SIGNATURE header —
    computed over the raw request body, not individual payload fields.
    verify_webhook() requires the raw body bytes, passed via headers dict.
    """

    GATEWAY_NAME = "safepay"

    def __init__(self) -> None:
        self.api_key        = getattr(settings, "SAFEPAY_API_KEY",        "")
        self.webhook_secret = getattr(settings, "SAFEPAY_WEBHOOK_SECRET", "")
        self._configured    = bool(self.api_key)

        if not self._configured:
            logger.warning(
                "SafepayGatewayClient: credentials not configured. "
                "Set SAFEPAY_API_KEY, SAFEPAY_WEBHOOK_SECRET in settings."
            )

    def initiate_payment(
        self,
        request: GatewayInitRequest,
    ) -> GatewayInitResponse:
        """
        Initiate Safepay token-based payment.

        Raises InfrastructureError if credentials are not configured.
        Full implementation: POST to Safepay /order/create,
        receive tracker token, return as payment_token in response.
        Frontend uses token to redirect to Safepay checkout.
        """
        if not self._configured:
            raise InfrastructureError(
                "Safepay payment gateway is not configured. "
                "Please contact support.",
                code=ErrorCode.PAYMENT_GATEWAY_NOT_CONFIGURED,
                notify=False,
                internal={
                    "gateway": self.GATEWAY_NAME,
                    "reason":  "credentials_missing",
                    "settings": ["SAFEPAY_API_KEY", "SAFEPAY_WEBHOOK_SECRET"],
                },
            )

        raise NotImplementedError(
            "Safepay initiate_payment() full implementation pending."
        )

    def verify_webhook(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        """
        Verify Safepay webhook HMAC-SHA256 signature.

        Safepay sends signature in X-SFPY-SIGNATURE header.
        Signature is computed over the raw JSON body bytes.
        The raw body is passed in headers dict under the key
        '__raw_body' — set by the webhook view before passing headers.

        Args:
            payload: Parsed JSON payload (not used for signature — raw
                     body is used).
            headers: HTTP headers dict. Must contain '__raw_body' key
                     with raw request bytes.
            secret:  SAFEPAY_WEBHOOK_SECRET from settings.

        Returns:
            True if signature is valid. False otherwise.
        """
        if not secret:
            logger.warning(
                "SafepayGatewayClient.verify_webhook: "
                "SAFEPAY_WEBHOOK_SECRET not configured — rejecting webhook."
            )
            return False

        received_signature = headers.get("X-SFPY-SIGNATURE", "")
        if not received_signature:
            logger.warning(
                "SafepayGatewayClient.verify_webhook: "
                "X-SFPY-SIGNATURE header missing."
            )
            return False

        raw_body: bytes = headers.get("__raw_body", b"")
        if not raw_body:
            # Fallback: re-encode payload as JSON
            raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        computed = hmac.new(
            secret.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(computed, received_signature.lower())

        if not is_valid:
            logger.warning(
                "SafepayGatewayClient.verify_webhook: "
                "HMAC mismatch — possible fraudulent webhook."
            )

        return is_valid

    def parse_webhook(
        self,
        payload: dict,
    ) -> WebhookParseResult:
        """
        Parse Safepay webhook payload.

        Safepay webhook event types:
            payment:created  — payment initiated (not success yet)
            payment:success  — payment confirmed SUCCESS
            payment:failed   — payment failed

        Order reference: data.order.ref or data.tracker.ref
        Gateway reference: data.tracker.token
        Amount: data.order.amount (in PKR)

        Args:
            payload: Verified Safepay webhook payload.

        Returns:
            WebhookParseResult with extracted payment data.
        """
        try:
            event      = payload.get("event", "")
            data       = payload.get("data", {})
            order_data = data.get("order", {})
            tracker    = data.get("tracker", {})

            order_number      = order_data.get("ref", "")
            gateway_reference = tracker.get("token", "")
            raw_status        = event

            try:
                amount_pkr = Decimal(str(order_data.get("amount", "0")))
            except Exception:
                amount_pkr = Decimal("0.00")

            is_success = event == "payment:success"

            return WebhookParseResult(
                is_verified=True,
                is_success=is_success,
                order_number=order_number,
                gateway_reference=gateway_reference,
                amount_pkr=amount_pkr,
                raw_status=raw_status,
                error_message="" if is_success else f"Gateway event: {event}",
            )

        except Exception as exc:
            logger.exception(
                "SafepayGatewayClient.parse_webhook: "
                "unexpected parse error — exc=%s",
                str(exc),
            )
            return WebhookParseResult(
                is_verified=True,
                is_success=False,
                error_message=f"Parse error: {exc}",
            )