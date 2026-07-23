# apps/payments/gateways/jazzcash.py
from __future__ import annotations

"""
JazzCash gateway client — stub implementation.

Full implementation requires:
    JAZZCASH_MERCHANT_ID
    JAZZCASH_PASSWORD
    JAZZCASH_INTEGRITY_SALT

in Django settings. These are obtained from JazzCash merchant portal.

Until credentials are available, initiate_payment() raises
InfrastructureError with notify=False so no false Sentry alerts
fire during development.

HMAC algorithm for JazzCash: HMAC-SHA256
Signature field in payload: pp_SecureHash
Signature fields order: sorted alphabetically by key, concatenated
with integrity salt, then HMAC-SHA256.

Reference: JazzCash Payment Gateway Integration Guide v2.0
"""

import hashlib
import hmac
import logging

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


class JazzCashGatewayClient(BaseGatewayClient):
    """
    JazzCash payment gateway client.

    Stub — raises InfrastructureError on initiate_payment() until
    credentials are configured in settings.

    verify_webhook() and parse_webhook() are implemented and tested
    independently of credentials — webhook processing works as soon
    as JazzCash starts sending callbacks.
    """

    GATEWAY_NAME = "jazzcash"

    def __init__(self) -> None:
        self.merchant_id     = getattr(settings, "JAZZCASH_MERCHANT_ID",     "")
        self.password        = getattr(settings, "JAZZCASH_PASSWORD",        "")
        self.integrity_salt  = getattr(settings, "JAZZCASH_INTEGRITY_SALT",  "")
        self.webhook_secret  = getattr(settings, "JAZZCASH_INTEGRITY_SALT",  "")
        self._configured     = all([
            self.merchant_id,
            self.password,
            self.integrity_salt,
        ])

        if not self._configured:
            logger.warning(
                "JazzCashGatewayClient: credentials not configured. "
                "Set JAZZCASH_MERCHANT_ID, JAZZCASH_PASSWORD, "
                "JAZZCASH_INTEGRITY_SALT in settings."
            )

    def initiate_payment(
        self,
        request: GatewayInitRequest,
    ) -> GatewayInitResponse:
        """
        Initiate JazzCash payment.

        Raises InfrastructureError if credentials are not configured.
        Full implementation: build pp_* fields, compute HMAC-SHA256
        secure hash, POST to JazzCash checkout URL, return redirect_url.
        """
        if not self._configured:
            raise InfrastructureError(
                "JazzCash payment gateway is not configured. "
                "Please contact support.",
                code=ErrorCode.PAYMENT_GATEWAY_NOT_CONFIGURED,
                notify=False,
                internal={
                    "gateway":  self.GATEWAY_NAME,
                    "reason":   "credentials_missing",
                    "settings": [
                        "JAZZCASH_MERCHANT_ID",
                        "JAZZCASH_PASSWORD",
                        "JAZZCASH_INTEGRITY_SALT",
                    ],
                },
            )

        # ── Full implementation placeholder ───────────────────────────────
        # When credentials arrive:
        #   1. Build pp_* parameter dict per JazzCash spec.
        #   2. Compute HMAC-SHA256 secure hash over sorted pp_* values.
        #   3. POST to JazzCash checkout endpoint.
        #   4. Parse response and return GatewayInitResponse.
        raise NotImplementedError(
            "JazzCash initiate_payment() full implementation pending. "
            "Wire after receiving merchant credentials."
        )

    def verify_webhook(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        """
        Verify JazzCash webhook HMAC-SHA256 signature.

        JazzCash includes pp_SecureHash in the payload itself.
        Verification: sort all pp_* keys alphabetically (excluding
        pp_SecureHash), concatenate values with integrity salt as
        prefix, compute HMAC-SHA256, compare with pp_SecureHash.

        Args:
            payload: Parsed webhook JSON payload.
            headers: HTTP headers (not used by JazzCash — signature is
                     in payload).
            secret:  JAZZCASH_INTEGRITY_SALT from settings.

        Returns:
            True if computed hash matches pp_SecureHash. False otherwise.
        """
        if not secret:
            logger.warning(
                "JazzCashGatewayClient.verify_webhook: "
                "JAZZCASH_INTEGRITY_SALT not configured — "
                "rejecting webhook."
            )
            return False

        received_hash = payload.get("pp_SecureHash", "")
        if not received_hash:
            logger.warning(
                "JazzCashGatewayClient.verify_webhook: "
                "pp_SecureHash missing from payload."
            )
            return False

        # Build sorted hash string per JazzCash spec
        hash_fields = {
            k: v for k, v in payload.items()
            if k != "pp_SecureHash" and k.startswith("pp_")
        }
        sorted_values = "&".join(
            str(v) for k, v in sorted(hash_fields.items())
        )
        hash_string = f"{secret}&{sorted_values}"

        computed_hash = hmac.new(
            secret.encode("utf-8"),
            hash_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()

        is_valid = hmac.compare_digest(computed_hash, received_hash.upper())

        if not is_valid:
            logger.warning(
                "JazzCashGatewayClient.verify_webhook: "
                "HMAC mismatch — possible fraudulent webhook. "
                "computed=%s received=%s",
                computed_hash[:8] + "...",
                received_hash[:8] + "...",
            )

        return is_valid

    def parse_webhook(
        self,
        payload: dict,
    ) -> WebhookParseResult:
        """
        Parse JazzCash webhook payload into WebhookParseResult.

        JazzCash success indicator: pp_ResponseCode == "000"
        Order reference field:      pp_MerchantInvoiceNumber
        Gateway reference field:    pp_TxnRefNo
        Amount field:               pp_Amount (in paisa — divide by 100)

        Args:
            payload: Verified JazzCash webhook payload.

        Returns:
            WebhookParseResult with extracted payment data.
        """
        try:
            response_code     = payload.get("pp_ResponseCode", "")
            order_number      = payload.get("pp_MerchantInvoiceNumber", "")
            gateway_reference = payload.get("pp_TxnRefNo", "")
            raw_status        = payload.get("pp_ResponseMessage", "")

            # JazzCash sends amount in paisa — convert to PKR
            amount_paisa = payload.get("pp_Amount", "0")
            try:
                from decimal import Decimal as _Decimal
                amount_pkr = _Decimal(str(amount_paisa)) / _Decimal("100")
            except Exception:
                amount_pkr = _Decimal("0.00")

            is_success = response_code == "000"

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
                "JazzCashGatewayClient.parse_webhook: "
                "unexpected parse error — exc=%s",
                str(exc),
            )
            return WebhookParseResult(
                is_verified=True,
                is_success=False,
                error_message=f"Parse error: {exc}",
            )