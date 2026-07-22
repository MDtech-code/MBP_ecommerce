# apps/payments/gateways/easypaisa.py
from __future__ import annotations

"""
Easypaisa gateway client — stub implementation.

Full implementation requires:
    EASYPAISA_STORE_ID
    EASYPAISA_HASH_KEY

in Django settings.

HMAC algorithm for Easypaisa: HMAC-SHA256
Signature field in headers: X-Hash (varies by integration type).

Reference: Easypaisa Payment Gateway Integration Guide
"""

import hashlib
import hmac
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


class EasypaisaGatewayClient(BaseGatewayClient):
    """
    Easypaisa payment gateway client.

    Stub — raises InfrastructureError on initiate_payment() until
    credentials are configured in settings.
    """

    GATEWAY_NAME = "easypaisa"

    def __init__(self) -> None:
        self.store_id   = getattr(settings, "EASYPAISA_STORE_ID", "")
        self.hash_key   = getattr(settings, "EASYPAISA_HASH_KEY", "")
        self._configured = all([self.store_id, self.hash_key])

        if not self._configured:
            logger.warning(
                "EasypaisaGatewayClient: credentials not configured. "
                "Set EASYPAISA_STORE_ID, EASYPAISA_HASH_KEY in settings."
            )

    def initiate_payment(
        self,
        request: GatewayInitRequest,
    ) -> GatewayInitResponse:
        """
        Initiate Easypaisa payment.

        Raises InfrastructureError if credentials are not configured.
        """
        if not self._configured:
            raise InfrastructureError(
                "Easypaisa payment gateway is not configured. "
                "Please contact support.",
                code=ErrorCode.PAYMENT_GATEWAY_NOT_CONFIGURED,
                notify=False,
                internal={
                    "gateway": self.GATEWAY_NAME,
                    "reason":  "credentials_missing",
                    "settings": [
                        "EASYPAISA_STORE_ID",
                        "EASYPAISA_HASH_KEY",
                    ],
                },
            )

        raise NotImplementedError(
            "Easypaisa initiate_payment() full implementation pending."
        )

    def verify_webhook(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        """
        Verify Easypaisa webhook HMAC-SHA256 signature.

        Easypaisa sends the hash in the payload under 'hash' key.
        Hash is computed over all payload fields except 'hash' itself,
        sorted alphabetically, concatenated with hash_key.

        Args:
            payload: Parsed webhook JSON payload.
            headers: HTTP headers.
            secret:  EASYPAISA_HASH_KEY from settings.

        Returns:
            True if computed hash matches payload hash. False otherwise.
        """
        if not secret:
            logger.warning(
                "EasypaisaGatewayClient.verify_webhook: "
                "EASYPAISA_HASH_KEY not configured — rejecting webhook."
            )
            return False

        received_hash = payload.get("hash", "")
        if not received_hash:
            logger.warning(
                "EasypaisaGatewayClient.verify_webhook: "
                "hash field missing from payload."
            )
            return False

        hash_fields = {k: v for k, v in payload.items() if k != "hash"}
        sorted_string = "&".join(
            f"{k}={v}" for k, v in sorted(hash_fields.items())
        )
        hash_string = f"{sorted_string}&{secret}"

        computed = hmac.new(
            secret.encode("utf-8"),
            hash_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        is_valid = hmac.compare_digest(computed, received_hash.lower())

        if not is_valid:
            logger.warning(
                "EasypaisaGatewayClient.verify_webhook: "
                "HMAC mismatch — possible fraudulent webhook."
            )

        return is_valid

    def parse_webhook(
        self,
        payload: dict,
    ) -> WebhookParseResult:
        """
        Parse Easypaisa webhook payload.

        Easypaisa success indicator: status == "0000" or "00"
        Order reference field:       orderId or merchantOrderId
        Gateway reference field:     transactionId
        Amount field:                amount (in PKR directly)

        Args:
            payload: Verified Easypaisa webhook payload.

        Returns:
            WebhookParseResult with extracted payment data.
        """
        try:
            status_code       = str(payload.get("status", ""))
            order_number      = (
                payload.get("orderId")
                or payload.get("merchantOrderId", "")
            )
            gateway_reference = payload.get("transactionId", "")
            raw_status        = payload.get("statusDesc", "")

            try:
                amount_pkr = Decimal(str(payload.get("amount", "0")))
            except Exception:
                amount_pkr = Decimal("0.00")

            is_success = status_code in ("0000", "00")

            return WebhookParseResult(
                is_verified=True,
                is_success=is_success,
                order_number=order_number,
                gateway_reference=gateway_reference,
                amount_pkr=amount_pkr,
                raw_status=raw_status,
                error_message="" if is_success else raw_status,
            )

        except Exception as exc:
            logger.exception(
                "EasypaisaGatewayClient.parse_webhook: "
                "unexpected parse error — exc=%s",
                str(exc),
            )
            return WebhookParseResult(
                is_verified=True,
                is_success=False,
                error_message=f"Parse error: {exc}",
            )