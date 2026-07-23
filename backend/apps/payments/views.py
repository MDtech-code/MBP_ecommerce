# apps/payments/views.py
from __future__ import annotations

"""
Payment views — HTTP layer for the payments app.

Endpoints:
    POST /api/payments/initiate/
        PaymentInitiateAPIView — customer initiates online payment.

    GET  /api/payments/status/<order_number>/
        PaymentStatusAPIView — customer polls payment status.

    POST /api/payments/webhooks/jazzcash/
        JazzCashWebhookView — JazzCash gateway callback.

    POST /api/payments/webhooks/easypaisa/
        EasypaisaWebhookView — Easypaisa gateway callback.

    POST /api/payments/webhooks/safepay/
        SafepayWebhookView — Safepay gateway callback.

Webhook design rules (same pattern as logistics courier webhooks):
    1. Save WebhookLog immediately — return 200 to gateway.
    2. Dispatch Celery task — never process inline.
    3. No auth on webhook endpoints — HMAC is the verification.
    4. CSRF exempt on webhook endpoints — external POST requests.
    5. Never raise an exception that changes the 200 response
       to the gateway. Gateways retry on non-200 — duplicates are bad.

Permission:
    PaymentInitiateAPIView  — IsAuthenticated, IsVerified.
    PaymentStatusAPIView    — IsAuthenticated.
    Webhook views           — AllowAny (HMAC verified in Celery task).

Dependency direction:
    models → selectors → services → serializers → views
"""

import json
import logging

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.api.views import BaseAPIView
from apps.core.exceptions import DomainError
from apps.core.permissions import IsVerified
from apps.payments.models import WebhookLog
from apps.payments.selectors.payment_selectors import (
    get_latest_transaction_for_order,
    get_order_by_number_for_user,
)
from apps.payments.serializers import (
    PaymentInitiateSerializer,
    PaymentStatusSerializer,
)
from apps.payments.services.payment_service import PaymentService
from apps.payments.tasks import process_payment_webhook

logger = logging.getLogger("apps.payments")


class PaymentInitiateAPIView(BaseAPIView):
    """
    POST /api/payments/initiate/

    Customer initiates online payment for a placed PENDING order.

    Validates input, locates order, calls PaymentService.
    Returns redirect_url or payment_token from gateway.
    DomainError and InfrastructureError from service propagate
    automatically to custom_exception_handler.
    """

    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request: Request) -> Response:
        serializer = PaymentInitiateSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Payment initiation failed.",
                errors=serializer.errors,
                status_code=400,
            )

        validated    = serializer.validated_data
        order_number = validated["order_number"]
        gateway_name = validated["gateway"]

        # ── Locate order — ownership enforced ─────────────────────────────────

        order = get_order_by_number_for_user(order_number, request.user)
        if order is None:
            return self.not_found_response(
                message="Order not found.",
            )

        # ── Initiate payment — DomainError/InfrastructureError propagates ─────

        response = PaymentService.initiate_payment(
            user=request.user,
            order=order,
            gateway_name=gateway_name,
        )

        logger.info(
            "PaymentInitiateAPIView.post: payment initiated | "
            "order=%s gateway=%s user=%s",
            order_number,
            gateway_name,
            request.user.pk,
        )

        # Build response data — include whichever of redirect_url /
        # payment_token the gateway returned
        data: dict = {
            "gateway":    gateway_name,
            "order":      order_number,
        }
        if response.redirect_url:
            data["redirect_url"] = response.redirect_url
        if response.payment_token:
            data["payment_token"] = response.payment_token
        if response.gateway_reference:
            data["gateway_reference"] = response.gateway_reference

        return self.success_response(
            data=data,
            message="Payment initiated. Please complete payment on the "
                    "gateway page.",
        )


class PaymentStatusAPIView(BaseAPIView):
    """
    GET /api/payments/status/<order_number>/

    Customer polls payment status after redirect back from gateway.

    Returns the most recent PaymentTransaction for the order.
    Ownership enforced by get_order_by_number_for_user() selector.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, order_number: str) -> Response:
        order = get_order_by_number_for_user(order_number, request.user)
        if order is None:
            return self.not_found_response(
                message="Order not found.",
            )

        transaction = get_latest_transaction_for_order(order)
        if transaction is None:
            return self.not_found_response(
                message="No payment transaction found for this order.",
            )

        serializer = PaymentStatusSerializer(
            transaction,
            context={"request": request},
        )

        logger.info(
            "PaymentStatusAPIView.get: retrieved | "
            "order=%s user=%s status=%s",
            order_number,
            request.user.pk,
            transaction.status,
        )

        return self.success_response(
            data=serializer.data,
            message="Payment status retrieved successfully.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# WEBHOOK BASE VIEW
# ─────────────────────────────────────────────────────────────────────────────

@method_decorator(csrf_exempt, name="dispatch")
class BaseWebhookView(BaseAPIView):
    """
    Base class for all payment gateway webhook receivers.

    Subclasses set gateway_name class attribute.
    All webhooks follow the same pattern:
        1. Read raw body for Safepay HMAC (must be read before parsing).
        2. Parse JSON payload.
        3. Extract headers.
        4. Create WebhookLog immediately.
        5. Dispatch Celery task.
        6. Return 200 unconditionally.

    Rule: Never return non-200 to a gateway webhook.
    Gateways interpret non-200 as delivery failure and retry —
    which creates duplicate WebhookLogs and double-processing risk.
    All errors are handled inside the Celery task.
    """

    permission_classes = [AllowAny]
    gateway_name: str  = ""

    def post(self, request: Request) -> Response:
        # ── Read raw body before DRF parses it ───────────────────────────────
        # Safepay HMAC is computed over raw body bytes.
        # DRF has already parsed request.data by the time post() runs,
        # but request.body is still available and not consumed.
        raw_body: bytes = request.body

        # ── Parse payload ─────────────────────────────────────────────────────
        try:
            if isinstance(request.data, dict):
                payload: dict = request.data
            else:
                payload = json.loads(raw_body or b"{}")
        except (json.JSONDecodeError, Exception):
            payload = {}

        # ── Extract and sanitise headers ──────────────────────────────────────
        # Store relevant headers only — not auth headers, cookies, etc.
        # Include __raw_body for Safepay HMAC verification in task.
        headers: dict = {
            "Content-Type":      request.META.get("CONTENT_TYPE", ""),
            "X-SFPY-SIGNATURE":  request.META.get(
                "HTTP_X_SFPY_SIGNATURE", ""
            ),
            "X-Hash":            request.META.get("HTTP_X_HASH", ""),
            "__raw_body":        raw_body.decode("utf-8", errors="replace"),
        }

        # ── Get IP address ────────────────────────────────────────────────────
        ip_address: str = (
            request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "")
        )

        # ── Create WebhookLog immediately — immutable evidence ────────────────
        try:
            webhook_log = WebhookLog.objects.create(
                gateway=self.gateway_name,
                payload=payload,
                headers=headers,
                ip_address=ip_address or None,
                is_verified=False,
                processed_successfully=False,
            )

            logger.info(
                "BaseWebhookView.post: WebhookLog created | "
                "gateway=%s webhook_log_id=%s ip=%s",
                self.gateway_name,
                webhook_log.pk,
                ip_address,
            )

        except Exception as exc:
            # Even WebhookLog creation failure must not return non-200.
            logger.exception(
                "BaseWebhookView.post: WebhookLog creation failed | "
                "gateway=%s exc=%s",
                self.gateway_name,
                str(exc),
            )
            return self.success_response(
                message="Webhook received.",
                data=None,
            )

        # ── Dispatch Celery task ──────────────────────────────────────────────
        try:
            process_payment_webhook.delay(
                webhook_log_id=webhook_log.pk,
                gateway_name=self.gateway_name,
            )

            logger.info(
                "BaseWebhookView.post: Celery task dispatched | "
                "gateway=%s webhook_log_id=%s",
                self.gateway_name,
                webhook_log.pk,
            )

        except Exception as exc:
            # Task dispatch failure must not return non-200.
            logger.exception(
                "BaseWebhookView.post: task dispatch failed | "
                "gateway=%s webhook_log_id=%s exc=%s",
                self.gateway_name,
                webhook_log.pk,
                str(exc),
            )

        # ── Always return 200 ─────────────────────────────────────────────────
        return self.success_response(
            message="Webhook received.",
            data=None,
        )


class JazzCashWebhookView(BaseWebhookView):
    """POST /api/payments/webhooks/jazzcash/"""
    gateway_name = "jazzcash"


class EasypaisaWebhookView(BaseWebhookView):
    """POST /api/payments/webhooks/easypaisa/"""
    gateway_name = "easypaisa"


class SafepayWebhookView(BaseWebhookView):
    """POST /api/payments/webhooks/safepay/"""
    gateway_name = "safepay"