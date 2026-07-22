# apps/payments/selectors/payment_selectors.py
from __future__ import annotations

"""
Payment selectors — all database reads for the payments app.

Responsibility:
    Every query that touches PaymentTransaction, RefundTransaction,
    or WebhookLog lives here.
    Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Dependency direction:
    models → selectors → services → views
"""

import logging

from apps.orders.models import Order
from apps.payments.models import PaymentTransaction, WebhookLog

logger = logging.getLogger("apps.payments")


def get_pending_transaction_for_order(
    order: Order,
) -> PaymentTransaction | None:
    """
    Return the most recent PENDING PaymentTransaction for an order.

    Used by PaymentService.initiate_payment() to find the transaction
    created at checkout before initiating with the gateway.

    Args:
        order: Order instance to look up.

    Returns:
        Most recent PENDING PaymentTransaction, or None.
    """
    return (
        PaymentTransaction.objects
        .filter(
            order=order,
            status=PaymentTransaction.Status.PENDING,
        )
        .order_by("-created_at")
        .first()
    )


def get_success_transaction_for_order(
    order: Order,
) -> PaymentTransaction | None:
    """
    Return the SUCCESS PaymentTransaction for an order, if any.

    Used by PaymentService.initiate_payment() to check whether
    the order has already been paid — guards against re-initiating
    payment for an already-paid order.

    Args:
        order: Order instance to check.

    Returns:
        SUCCESS PaymentTransaction, or None.
    """
    return (
        PaymentTransaction.objects
        .filter(
            order=order,
            status=PaymentTransaction.Status.SUCCESS,
        )
        .first()
    )


def get_transaction_by_idempotency_key(
    idempotency_key: str,
) -> PaymentTransaction | None:
    """
    Return a PaymentTransaction by idempotency key.

    Used by webhook processor to match incoming webhook payload
    to the correct PaymentTransaction when the gateway returns
    the idempotency key as the merchant reference.

    Args:
        idempotency_key: UUID string from gateway callback.

    Returns:
        Matching PaymentTransaction, or None.
    """
    return (
        PaymentTransaction.objects
        .select_related("order")
        .filter(idempotency_key=idempotency_key)
        .first()
    )


def get_transaction_for_order_by_status(
    order: Order,
    status: str,
) -> PaymentTransaction | None:
    """
    Return a PaymentTransaction for an order filtered by status.

    Generic selector used for payment status endpoint.

    Args:
        order:  Order instance.
        status: PaymentTransaction.Status value.

    Returns:
        Matching PaymentTransaction, or None.
    """
    return (
        PaymentTransaction.objects
        .filter(order=order, status=status)
        .order_by("-created_at")
        .first()
    )


def get_latest_transaction_for_order(
    order: Order,
) -> PaymentTransaction | None:
    """
    Return the most recent PaymentTransaction for an order
    regardless of status.

    Used by payment status endpoint to show current state.

    Args:
        order: Order instance.

    Returns:
        Most recent PaymentTransaction, or None.
    """
    return (
        PaymentTransaction.objects
        .filter(order=order)
        .order_by("-created_at")
        .first()
    )


def get_order_by_number_for_user(
    order_number: str,
    user,
) -> Order | None:
    """
    Return an Order by order_number scoped to the requesting user.

    Ownership enforced by user filter — a valid order belonging
    to another user returns None, not PermissionDenied.
    Prevents order number enumeration attacks.

    Args:
        order_number: Human-readable order identifier from URL/body.
        user:         Authenticated user making the request.

    Returns:
        Order instance, or None.
    """
    return (
        Order.objects
        .filter(order_number=order_number, user=user)
        .first()
    )