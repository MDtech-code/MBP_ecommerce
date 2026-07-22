# apps/payments/gateways/base.py
from __future__ import annotations

"""
Gateway base — abstract contract for all payment gateway clients.

Every gateway client must implement this interface exactly.
PaymentService and webhook views depend only on this interface —
they never import JazzCashGatewayClient or SafepayGatewayClient directly.
This is the Strategy pattern: swap gateway implementations without
touching any other code.

Data classes:
    GatewayInitRequest  — what we send to the gateway to initiate payment.
    GatewayInitResponse — what the gateway returns after initiation.
    WebhookParseResult  — structured result of parsing a gateway webhook.

Abstract class:
    BaseGatewayClient   — interface every gateway client implements.

Dependency direction:
    base.py has ZERO imports from any app layer.
    It is safe to import from any layer including models and tasks.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

logger = logging.getLogger("apps.payments")


# ─────────────────────────────────────────────────────────────────────────────
# DATA CLASSES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class GatewayInitRequest:
    """
    Gateway-agnostic payment initiation request.

    Built by PaymentService from Order and PaymentTransaction data.
    Passed to BaseGatewayClient.initiate_payment() — each gateway
    client maps these fields to its own API format.

    Fields:
        order_number:     Human-readable order identifier. Sent as
                          merchant reference so gateway callbacks
                          can be matched back to the order.
        amount_pkr:       Decimal amount in Pakistani Rupees.
        idempotency_key:  UUID string from PaymentTransaction.idempotency_key.
                          Prevents double-charging on network retries.
        customer_email:   Customer contact — some gateways require it.
        customer_phone:   Customer phone — required by JazzCash/Easypaisa.
        return_url:       URL customer is redirected to after payment.
        webhook_url:      URL gateway POSTs to on payment events.
        description:      Human-readable payment description shown on
                          gateway payment page.
    """
    order_number:    str
    amount_pkr:      Decimal
    idempotency_key: str
    customer_email:  str
    customer_phone:  str
    return_url:      str
    webhook_url:     str
    description:     str = ""


@dataclass(frozen=True)
class GatewayInitResponse:
    """
    Structured response from gateway after payment initiation.

    Fields:
        success:          True if gateway accepted the initiation request.
        redirect_url:     URL to redirect customer to for payment.
                          None for token-based flows (e.g. Safepay).
        payment_token:    Token for embedded/hosted payment flows.
                          None for redirect-only gateways.
        gateway_reference: Gateway-assigned reference for this payment attempt.
                           Stored on PaymentTransaction.transaction_reference.
        raw_response:     Complete raw response from gateway for logging.
        error_message:    Human-readable error if success=False.
    """
    success:           bool
    redirect_url:      str | None       = None
    payment_token:     str | None       = None
    gateway_reference: str | None       = None
    raw_response:      dict             = field(default_factory=dict)
    error_message:     str              = ""


@dataclass(frozen=True)
class WebhookParseResult:
    """
    Structured result of parsing and verifying a gateway webhook payload.

    Fields:
        is_verified:          True if HMAC signature matched gateway secret.
        is_success:           True if payment was successful per gateway.
        order_number:         Extracted from payload — used to find the Order.
        gateway_reference:    Gateway transaction ID from payload.
                              Stored on PaymentTransaction.transaction_reference.
        amount_pkr:           Amount from payload — cross-checked against
                              PaymentTransaction.amount_pkr for fraud detection.
        raw_status:           Raw status string from gateway payload.
                              Stored for debugging.
        error_message:        Gateway error message if is_success=False.
        extra:                Any additional gateway-specific data.
    """
    is_verified:       bool
    is_success:        bool
    order_number:      str              = ""
    gateway_reference: str              = ""
    amount_pkr:        Decimal          = Decimal("0.00")
    raw_status:        str              = ""
    error_message:     str              = ""
    extra:             dict             = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# ABSTRACT BASE CLIENT
# ─────────────────────────────────────────────────────────────────────────────

class BaseGatewayClient(ABC):
    """
    Abstract interface for all payment gateway clients.

    Every concrete gateway client (JazzCash, Easypaisa, Safepay)
    must implement all three abstract methods.

    PaymentService and webhook views only depend on this class —
    never on concrete implementations. This means:
        - Adding a new gateway = one new class + one registry line.
        - Removing a gateway  = delete class + remove registry line.
        - Zero changes to PaymentService, views, or tasks.

    Configuration:
        Each subclass reads its credentials from Django settings
        inside __init__. If credentials are missing, __init__ raises
        ImproperlyConfigured so the error surfaces at startup, not
        at the moment of first payment attempt.
    """

    @abstractmethod
    def initiate_payment(
        self,
        request: GatewayInitRequest,
    ) -> GatewayInitResponse:
        """
        Initiate a payment with the gateway.

        Builds the gateway-specific API request from GatewayInitRequest,
        calls the gateway API, and returns a GatewayInitResponse.

        Args:
            request: GatewayInitRequest with all payment parameters.

        Returns:
            GatewayInitResponse with redirect_url or payment_token.

        Raises:
            InfrastructureError — on API timeout, connection error,
                                  or unexpected gateway response format.
        """
        ...

    @abstractmethod
    def verify_webhook(
        self,
        payload: dict,
        headers: dict,
        secret: str,
    ) -> bool:
        """
        Verify the HMAC signature of an incoming webhook.

        Each gateway signs its webhook payloads differently.
        This method encapsulates the gateway-specific verification logic.

        Args:
            payload: Parsed JSON payload from webhook request.
            headers: HTTP headers from webhook request.
            secret:  Gateway webhook secret from Django settings.

        Returns:
            True if signature is valid. False if invalid or missing.
            Never raises — always returns bool.
        """
        ...

    @abstractmethod
    def parse_webhook(
        self,
        payload: dict,
    ) -> WebhookParseResult:
        """
        Parse a verified webhook payload into a structured result.

        Called only after verify_webhook() returns True.
        Extracts order_number, payment status, gateway reference,
        and amount from the gateway-specific payload format.

        Args:
            payload: Raw JSON payload from webhook request.

        Returns:
            WebhookParseResult with extracted payment data.
            Never raises — returns WebhookParseResult with
            is_success=False and error_message on parse failure.
        """
        ...