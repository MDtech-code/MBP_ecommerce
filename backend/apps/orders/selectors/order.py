# apps/orders/selectors/order.py
from __future__ import annotations

"""
Order selectors — database reads for order retrieval.

Responsibility:
    All Order-related database queries live here.
    Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Ownership enforcement:
    Every query filters by user — ownership is enforced at the
    database query level, not in the view or service layer.
    This prevents any possibility of a user accessing another
    user's order by guessing an order number.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db.models import QuerySet

from apps.orders.models import Order

logger = logging.getLogger("apps.orders")


def get_order_by_number(order_number: str, user) -> Order:
    """
    Fetch a single order by order number, scoped to the requesting user.

    Loads all related data needed for OrderDetailSerializer in one
    query set — avoids N+1 on shipping address, items, products,
    payment transactions, and status logs.

    Args:
        order_number: The ORD-YYYYMMDD-XXXXXXXX string identifier.
        user:         Authenticated user — ownership enforced here.

    Returns:
        Order instance with all related data prefetched.

    Raises:
        Order.DoesNotExist — caller returns 404.
        Ownership is enforced by filtering on user — a valid order
        number belonging to another user raises DoesNotExist here,
        not a 403. This prevents order number enumeration attacks.
    """
    return (
        Order.objects
        .select_related(
            "shipping_address",
            "coupon",
            "user",
        )
        .prefetch_related(
            "items__product",
            "payment_transactions",
            "status_logs",
        )
        .get(order_number=order_number, user=user)
    )


def list_orders_for_user(user) -> QuerySet:
    """
    Return a QuerySet of all orders for the authenticated user.

    Ordered by most recent first. select_related on shipping_address
    covers city/province display on list cards without extra queries.
    Returns a lazy QuerySet — the view applies pagination slice.

    Args:
        user: Authenticated user whose orders to retrieve.

    Returns:
        Lazy QuerySet of Order instances ordered by -placed_at.
    """
    return (
        Order.objects
        .select_related("shipping_address")
        .prefetch_related("payment_transactions")
        .filter(user=user)
        .order_by("-placed_at")
    )