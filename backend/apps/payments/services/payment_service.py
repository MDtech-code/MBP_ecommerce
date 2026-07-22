# apps/payments/services/payment_service.py
from __future__ import annotations

"""
Payment service — business logic for online payment initiation
and webhook result processing.

Responsibility:
    PaymentService.initiate_payment()      — validates order state,
        updates PaymentTransaction gateway if needed, calls gateway
        client, returns GatewayInitResponse to view.
    PaymentService.handle_webhook_result() — processes a verified,
        parsed WebhookParseResult: updates PaymentTransaction status,
        transitions Order, links WebhookLog.

COD is never routed here:
    COD PaymentTransaction is created at checkout and resolved by
    the logistics webhook (ShipmentService._handle_delivered).
    PaymentService.initiate_payment() explicitly rejects COD gateway.

Idempotency:
    The PaymentTransaction.idempotency_key is auto-generated at
    checkout. PaymentService passes str(transaction.idempotency_key)
    to every gateway client. The gateway uses this as the merchant
    reference to prevent double-charging on network retries.

Gateway field update on initiation:
    OrderService.checkout() maps ONLINE payment_method → SAFEPAY
    gateway as a placeholder. If the customer chooses JazzCash at
    initiation time, PaymentService updates the PENDING transaction's
    gateway field before calling the client. This is safe because
    no money has moved on a PENDING transaction.

Order transition rule:
    Order.transition_to(CONFIRMED) happens ONLY when webhook is
    verified and parsed as SUCCESS. Never on redirect. Never on
    frontend claim. The document is explicit on this — it is the
    most critical security rule in the payments flow.

Dependency direction:
    models → selectors → services → views
"""

import logging
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import transaction

from apps.core.exceptions import DomainError, InfrastructureError
from apps.core.error_codes import ErrorCode
from apps.orders.models import Order
from apps.payments.gateways.base import GatewayInitRequest, WebhookParseResult
from apps.payments.gateways.registry import ONLINE_GATEWAYS, get_gateway_client
from apps.payments.models import PaymentTransaction, WebhookLog
from apps.payments.selectors.payment_selectors import (
    get_latest_transaction_for_order,
    get_pending_transaction_for_order,
    get_success_transaction_for_order,
)

if TYPE_CHECKING:
    from apps.payments.gateways.base import GatewayInitResponse

logger = logging.getLogger("apps.payments")

# COD gateway — never goes through PaymentService.initiate_payment()
_COD_GATEWAY = PaymentTransaction.Gateway.COD


class PaymentService:
    """
    Business operations for online payment initiation and processing.

    All methods are static — no instance state required.
    All methods raise DomainError or InfrastructureError for failures.
    """

    # ─────────────────────────────────────────────────────────────────────────
    # INITIATE PAYMENT
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def initiate_payment(
        *,
        user,
        order: Order,
        gateway_name: str,
    ) -> "GatewayInitResponse":
        """
        Initiate an online payment for a PENDING order.

        Validates:
            1. Order is in PENDING status — cannot re-pay confirmed order.
            2. gateway_name is a valid ONLINE gateway (not COD).
            3. No existing SUCCESS transaction for this order.
            4. A PENDING PaymentTransaction exists (created at checkout).

        Updates:
            - PaymentTransaction.gateway to requested gateway_name
              if different from the placeholder set at checkout.

        Calls:
            - get_gateway_client(gateway_name).initiate_payment()

        Args:
            user:         Authenticated customer initiating payment.
            order:        Order instance in PENDING status.
            gateway_name: PaymentTransaction.Gateway value for online gateway.

        Returns:
            GatewayInitResponse with redirect_url or payment_token.

        Raises:
            DomainError 400  — order not in PENDING status.
            DomainError 400  — gateway not valid for online payment.
            DomainError 409  — order already has a SUCCESS transaction.
            DomainError 400  — no PENDING transaction found for order.
            InfrastructureError 503 — gateway not configured or API failure.
        """

        # ── Guard 1 — Order must be PENDING ───────────────────────────────────

        if order.status != Order.Status.PENDING:
            raise DomainError(
                f"Payment can only be initiated for pending orders. "
                f"Current order status: {order.get_status_display()}.",
                code=ErrorCode.ORDER_NOT_PAYABLE,
                status_code=400,
            )

        # ── Guard 2 — Gateway must be a valid online gateway ──────────────────

        if gateway_name not in ONLINE_GATEWAYS:
            raise DomainError(
                f"'{gateway_name}' is not a supported online payment gateway. "
                f"Supported gateways: {', '.join(sorted(ONLINE_GATEWAYS))}.",
                code=ErrorCode.INVALID_GATEWAY,
                status_code=400,
            )

        # ── Guard 3 — No existing SUCCESS transaction ─────────────────────────

        existing_success = get_success_transaction_for_order(order)
        if existing_success is not None:
            raise DomainError(
                "This order has already been paid successfully. "
                "No further payment is required.",
                code=ErrorCode.PAYMENT_ALREADY_SUCCESS,
                status_code=409,
            )

        # ── Guard 4 — PENDING transaction must exist ──────────────────────────

        pending_transaction = get_pending_transaction_for_order(order)
        if pending_transaction is None:
            raise DomainError(
                "No pending payment transaction found for this order. "
                "Please contact support.",
                code=ErrorCode.ORDER_NOT_PAYABLE,
                status_code=400,
            )

        # ── Update gateway if checkout placeholder differs ────────────────────
        # checkout() sets gateway=SAFEPAY as placeholder for all ONLINE orders.
        # If customer chose JazzCash or Easypaisa, update to actual gateway.

        if pending_transaction.gateway != gateway_name:
            PaymentTransaction.objects.filter(
                pk=pending_transaction.pk,
            ).update(gateway=gateway_name)
            pending_transaction.gateway = gateway_name

            logger.info(
                "PaymentService.initiate_payment: gateway updated | "
                "transaction_id=%s old_gateway=safepay new_gateway=%s",
                pending_transaction.pk,
                gateway_name,
            )

        # ── Get gateway client ────────────────────────────────────────────────

        client = get_gateway_client(gateway_name)
        if client is None:
            raise DomainError(
                f"Payment gateway '{gateway_name}' is not available.",
                code=ErrorCode.INVALID_GATEWAY,
                status_code=400,
            )

        # ── Build GatewayInitRequest ──────────────────────────────────────────

        return_url  = getattr(settings, "PAYMENT_RETURN_URL",  "")
        webhook_url = getattr(settings, "PAYMENT_WEBHOOK_BASE_URL", "")

        gateway_request = GatewayInitRequest(
            order_number=order.order_number,
            amount_pkr=pending_transaction.amount_pkr,
            idempotency_key=str(pending_transaction.idempotency_key),
            customer_email=getattr(user, "email", ""),
            customer_phone=getattr(user, "phone", ""),
            return_url=f"{return_url}?order={order.order_number}",
            webhook_url=f"{webhook_url}/api/payments/webhooks/{gateway_name}/",
            description=f"Payment for order {order.order_number}",
        )

        # ── Call gateway — may raise InfrastructureError ──────────────────────

        try:
            response = client.initiate_payment(gateway_request)
        except InfrastructureError:
            # Let it propagate — custom_exception_handler handles it.
            raise
        except Exception as exc:
            logger.exception(
                "PaymentService.initiate_payment: unexpected gateway error | "
                "order=%s gateway=%s exc=%s",
                order.order_number,
                gateway_name,
                str(exc),
            )
            raise InfrastructureError(
                "Payment gateway is temporarily unavailable. "
                "Please try again.",
                code=ErrorCode.PAYMENT_GATEWAY_ERROR,
                notify=True,
                internal={
                    "gateway":      gateway_name,
                    "order_number": order.order_number,
                    "exc":          str(exc),
                },
            )

        if not response.success:
            logger.warning(
                "PaymentService.initiate_payment: gateway rejected | "
                "order=%s gateway=%s error=%s",
                order.order_number,
                gateway_name,
                response.error_message,
            )
            raise InfrastructureError(
                "Payment gateway returned an error. Please try again.",
                code=ErrorCode.PAYMENT_GATEWAY_ERROR,
                notify=False,
                internal={
                    "gateway":       gateway_name,
                    "order_number":  order.order_number,
                    "error_message": response.error_message,
                    "raw_response":  response.raw_response,
                },
            )

        # ── Store gateway reference if returned ───────────────────────────────

        if response.gateway_reference:
            PaymentTransaction.objects.filter(
                pk=pending_transaction.pk,
            ).update(transaction_reference=response.gateway_reference)

        logger.info(
            "PaymentService.initiate_payment: initiated | "
            "order=%s gateway=%s transaction_id=%s",
            order.order_number,
            gateway_name,
            pending_transaction.pk,
        )

        return response

    # ─────────────────────────────────────────────────────────────────────────
    # HANDLE WEBHOOK RESULT
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def handle_webhook_result(
        *,
        webhook_log: WebhookLog,
        parse_result: WebhookParseResult,
        gateway_name: str,
    ) -> None:
        """
        Process a verified and parsed webhook result.

        Called by the Celery task after HMAC verification and parsing.
        Updates PaymentTransaction status and transitions Order.

        On SUCCESS:
            - PaymentTransaction.status → SUCCESS
            - PaymentTransaction.transaction_reference set
            - Order.transition_to(CONFIRMED)
            - WebhookLog linked to transaction

        On FAILURE:
            - PaymentTransaction.status → FAILED
            - PaymentTransaction.error_message set
            - Order stays PENDING (customer can retry)
            - WebhookLog linked to transaction

        All updates inside a single transaction.atomic() — either
        all succeed or all roll back.

        Args:
            webhook_log:   WebhookLog instance created by webhook view.
            parse_result:  WebhookParseResult from gateway client.
            gateway_name:  Gateway string for transaction lookup.

        Returns:
            None — side effects only.
        """
        from apps.payments.selectors.payment_selectors import (
            get_order_by_number_for_user,
        )

        # ── Find the Order ────────────────────────────────────────────────────

        order = (
            Order.objects
            .filter(order_number=parse_result.order_number)
            .select_related("user")
            .first()
        )

        if order is None:
            logger.warning(
                "PaymentService.handle_webhook_result: "
                "order not found | order_number=%s gateway=%s",
                parse_result.order_number,
                gateway_name,
            )
            webhook_log.save(update_fields=[
                "processed_successfully",
                "error_message",
            ])
            return

        # ── Find the PaymentTransaction ───────────────────────────────────────

        transaction_qs = PaymentTransaction.objects.filter(
            order=order,
            gateway=gateway_name,
            status__in=[
                PaymentTransaction.Status.PENDING,
                PaymentTransaction.Status.AUTHORIZED,
            ],
        ).order_by("-created_at")

        payment_transaction = transaction_qs.first()

        if payment_transaction is None:
            logger.warning(
                "PaymentService.handle_webhook_result: "
                "no matching PENDING transaction | "
                "order=%s gateway=%s",
                parse_result.order_number,
                gateway_name,
            )
            webhook_log.error_message = (
                "No matching PENDING transaction found for this order."
            )
            webhook_log.save(update_fields=[
                "processed_successfully",
                "error_message",
            ])
            return

        # ── Process inside atomic transaction ─────────────────────────────────

        with transaction.atomic():

            if parse_result.is_success:
                # ── SUCCESS path ──────────────────────────────────────────────

                PaymentTransaction.objects.filter(
                    pk=payment_transaction.pk,
                ).update(
                    status=PaymentTransaction.Status.SUCCESS,
                    transaction_reference=parse_result.gateway_reference or None,
                )
                payment_transaction.status = PaymentTransaction.Status.SUCCESS

                # Transition Order: PENDING → CONFIRMED
                # Only if order is still PENDING — idempotency guard.
                if order.can_transition_to(Order.Status.CONFIRMED):
                    order.transition_to(
                        Order.Status.CONFIRMED,
                        changed_by=None,
                        note=(
                            f"Payment confirmed via {gateway_name}. "
                            f"Gateway ref: {parse_result.gateway_reference}."
                        ),
                    )
                else:
                    logger.warning(
                        "PaymentService.handle_webhook_result: "
                        "order already past PENDING — skipping transition | "
                        "order=%s current_status=%s",
                        order.order_number,
                        order.status,
                    )

                # Link WebhookLog to transaction
                webhook_log.payment_transaction_id = payment_transaction.pk
                webhook_log.is_verified            = True
                webhook_log.processed_successfully = True
                webhook_log.save(update_fields=[
                    "payment_transaction_id",
                    "is_verified",
                    "processed_successfully",
                ])

                logger.info(
                    "PaymentService.handle_webhook_result: SUCCESS | "
                    "order=%s gateway=%s gateway_ref=%s",
                    order.order_number,
                    gateway_name,
                    parse_result.gateway_reference,
                )

            else:
                # ── FAILURE path ──────────────────────────────────────────────

                PaymentTransaction.objects.filter(
                    pk=payment_transaction.pk,
                ).update(
                    status=PaymentTransaction.Status.FAILED,
                    error_message=parse_result.error_message,
                )

                # Order stays PENDING — customer can retry with new payment
                webhook_log.payment_transaction_id = payment_transaction.pk
                webhook_log.is_verified            = True
                webhook_log.processed_successfully = True
                webhook_log.error_message          = parse_result.error_message
                webhook_log.save(update_fields=[
                    "payment_transaction_id",
                    "is_verified",
                    "processed_successfully",
                    "error_message",
                ])

                logger.info(
                    "PaymentService.handle_webhook_result: FAILED | "
                    "order=%s gateway=%s error=%s",
                    order.order_number,
                    gateway_name,
                    parse_result.error_message,
                )