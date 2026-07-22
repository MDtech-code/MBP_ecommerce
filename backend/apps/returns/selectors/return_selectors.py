# apps/returns/selectors/return_selectors.py
from __future__ import annotations

"""
Return selectors — all database reads for the returns app.

Responsibility:
    Every query that touches ReturnRequest or ReturnItemPhoto
    lives here. Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Ownership enforcement:
    Customer-facing selectors always scope by user to prevent
    one customer seeing or acting on another customer's data.
    A valid ReturnRequest belonging to another user raises
    ReturnRequest.DoesNotExist — not PermissionDenied.
    This prevents return request ID enumeration attacks.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db.models import QuerySet, Prefetch

from apps.returns.models import ReturnRequest, ReturnItemPhoto
from apps.orders.models import Order, OrderItem

logger = logging.getLogger("apps.returns")


def get_return_by_id(return_id: int, user) -> ReturnRequest:
    """
    Fetch a single ReturnRequest by pk, scoped to the requesting user.

    Ownership is enforced by filtering on requested_by=user.
    A valid return belonging to another user raises DoesNotExist
    rather than PermissionDenied — prevents ID enumeration.

    Prefetches photos so the detail serializer renders without
    additional queries.

    Args:
        return_id: ReturnRequest primary key from URL.
        user:      Authenticated user requesting the detail.

    Returns:
        ReturnRequest instance with photos and related order prefetched.

    Raises:
        ReturnRequest.DoesNotExist — caller returns 404.
    """
    return (
        ReturnRequest.objects
        .select_related(
            "order",
            "order_item",
            "requested_by",
            "reviewed_by",
        )
        .prefetch_related(
            Prefetch(
                "photos",
                queryset=ReturnItemPhoto.objects.order_by("created_at"),
            )
        )
        .get(pk=return_id, requested_by=user)
    )


def list_returns_for_user(user) -> QuerySet:
    """
    Return all ReturnRequests submitted by the requesting user.

    Ordered by most recent first (default on model Meta).
    Selects related order for order_number display in list serializer.
    Does not prefetch photos — list view does not show photo detail.

    Args:
        user: Authenticated user whose returns to list.

    Returns:
        QuerySet of ReturnRequest instances scoped to user.
    """
    return (
        ReturnRequest.objects
        .select_related("order", "order_item")
        .filter(requested_by=user)
        .order_by("-created_at")
    )


def get_order_item_for_return(order_item_id: int, user) -> OrderItem:
    """
    Fetch an OrderItem and verify it belongs to the requesting user.

    Used by ReturnService.create_return_request() to validate
    ownership before eligibility checks proceed.

    Loads order in one query to avoid N+1 on the eligibility
    checks in the service layer (delivered_at, status, user).

    Args:
        order_item_id: OrderItem primary key from return submission.
        user:          Authenticated user submitting the return.

    Returns:
        OrderItem with order loaded via select_related.

    Raises:
        OrderItem.DoesNotExist — caller returns 404.
                                  Ownership enforced by order__user=user —
                                  a valid item belonging to another user
                                  raises DoesNotExist, not 403.
                                  Prevents order item enumeration attacks.
    """
    return (
        OrderItem.objects
        .select_related("order")
        .get(pk=order_item_id, order__user=user)
    )


def get_existing_return_for_order_item(order_item: OrderItem) -> ReturnRequest | None:
    """
    Return an existing ReturnRequest for a given OrderItem, or None.

    Used by ReturnService.create_return_request() to enforce the
    one-return-per-order-item rule. Returns the request regardless
    of its status — a REJECTED request still blocks a new submission.
    Admin must intervene for second attempts.

    Args:
        order_item: OrderItem instance to check.

    Returns:
        ReturnRequest instance if one exists, else None.
    """
    return (
        ReturnRequest.objects
        .filter(order_item=order_item)
        .first()
    )