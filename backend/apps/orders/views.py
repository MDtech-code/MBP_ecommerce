# apps/orders/views.py
from __future__ import annotations

"""
Order app — view layer.

Responsibility:
    HTTP concerns only: parse request, validate input via serializers,
    call service layer for mutations, call selectors for reads,
    serialize results, return standardized response via BaseAPIView helpers.
    Zero business logic. Zero transaction management. Zero direct ORM mutations.

Exception handling policy:
    No try/except wraps normal operations.
    Global custom_exception_handler handles all unhandled exceptions.
    Cart.DoesNotExist → 500 (signal failure, not client error).
    Order.DoesNotExist → 404 via not_found_response.
    DomainError from service propagates to global handler automatically.

Dependency direction:
    selectors/order.py      (reads)
    services/order_service.py  (mutations)
         ↑
    views.py  ← this file
"""

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.cart.models import Cart
from apps.cart.selectors.cart import get_cart_for_user
from apps.core.api.views import BaseAPIView
from apps.core.pagination import build_pagination_meta, get_pagination_params
from apps.core.permissions import IsVerified

from .models import Order
from .selectors.order import get_order_by_number, list_orders_for_user
from .serializers import (
    CheckoutInputSerializer,
    OrderDetailSerializer,
    OrderListSerializer,
)
from .services.order_service import OrderService

logger = logging.getLogger("apps.orders")


# ─────────────────────────────────────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────────────────────────────────────


class CheckoutAPIView(BaseAPIView):
    """
    POST /api/orders/checkout/

    Executes the full atomic checkout operation.
    Requires authentication and email verification.

    Validates input via CheckoutInputSerializer, fetches the user's
    cart, delegates to OrderService.checkout() for the full atomic
    transaction block, and returns the created order via
    OrderDetailSerializer.

    Cart.DoesNotExist → 500 because cart is auto-created on registration.
    Missing cart means post_save signal failure — server defect, not
    client error.
    """

    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request: Request):
        # ── 1. Validate input ──────────────────────────────────────────────
        serializer = CheckoutInputSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "CheckoutAPIView: validation failed | "
                "user_id=%s request_id=%s errors=%s",
                request.user.pk,
                getattr(request, "id", "n/a"),
                serializer.errors,
            )
            return self.error_response(
                message=_("Checkout failed. Please correct the errors below."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── 2. Fetch cart ──────────────────────────────────────────────────
        try:
            cart = get_cart_for_user(request.user)
        except Cart.DoesNotExist:
            logger.error(
                "CheckoutAPIView: cart missing | "
                "user_id=%s request_id=%s — post_save signal failure suspected",
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 3. Delegate to order service ───────────────────────────────────
        # DomainError (cart empty, stock, coupon) propagates to handler.
        order = OrderService.checkout(
            user=request.user,
            validated_data=serializer.validated_data,
            cart=cart,
        )

        logger.info(
            "CheckoutAPIView: OK | "
            "order=%s user_id=%s request_id=%s",
            order.order_number,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        # ── 4. Re-fetch order with full prefetch for serialization ─────────
        order = get_order_by_number(order.order_number, request.user)

        return self.created_response(
            data=OrderDetailSerializer(order).data,
            message=_("Order placed successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ORDER LIST
# ─────────────────────────────────────────────────────────────────────────────


class OrderListAPIView(BaseAPIView):
    """
    GET /api/orders/

    Returns paginated list of the authenticated user's orders.
    Most recent orders first. Lightweight list card serialization —
    no nested items in list response.
    """

    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request: Request):
        # ── 1. Pagination params ───────────────────────────────────────────
        params = get_pagination_params(request, default_page_size=10)
        if not params.is_valid:
            return self.error_response(
                message=_("Invalid pagination parameters."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── 2. Fetch queryset ──────────────────────────────────────────────
        queryset = list_orders_for_user(request.user)
        total    = queryset.count()

        # ── 3. Slice for current page ──────────────────────────────────────
        offset = (params.page - 1) * params.page_size
        orders = queryset[offset: offset + params.page_size]

        # ── 4. Serialize ───────────────────────────────────────────────────
        data = OrderListSerializer(orders, many=True).data

        # ── 5. Build pagination meta ───────────────────────────────────────
        meta = build_pagination_meta(
            params.page,
            params.page_size,
            total,
        )

        logger.info(
            "OrderListAPIView: OK | "
            "user_id=%s page=%s total=%s request_id=%s",
            request.user.pk,
            params.page,
            total,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=data,
            message=_("Orders retrieved successfully."),
            meta=meta,
        )


# ─────────────────────────────────────────────────────────────────────────────
# ORDER DETAIL
# ─────────────────────────────────────────────────────────────────────────────


class OrderDetailAPIView(BaseAPIView):
    """
    GET /api/orders/<order_number>/

    Returns full order detail including nested shipping address,
    all line items, and payment status.

    Ownership enforced at selector level — get_order_by_number()
    filters by both order_number AND user. A valid order number
    belonging to another user raises DoesNotExist, returned as 404.
    This prevents order number enumeration attacks.
    """

    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request: Request, order_number: str):
        try:
            order = get_order_by_number(order_number, request.user)
        except Order.DoesNotExist:
            logger.warning(
                "OrderDetailAPIView: not found | "
                "order_number=%s user_id=%s request_id=%s",
                order_number,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(
                message=_("Order not found.")
            )

        logger.info(
            "OrderDetailAPIView: OK | "
            "order=%s user_id=%s request_id=%s",
            order_number,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=OrderDetailSerializer(order).data,
            message=_("Order retrieved successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ORDER CANCEL
# ─────────────────────────────────────────────────────────────────────────────


class OrderCancelAPIView(BaseAPIView):
    """
    POST /api/orders/<order_number>/cancel/

    Cancels a PENDING order. Restores stock, decrements coupon
    times_used, and marks PaymentTransaction as FAILED.

    Only PENDING orders can be cancelled by the customer.
    DomainError (409) is raised by service for any other status.

    Ownership enforced at selector level — same as OrderDetailAPIView.
    """

    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request: Request, order_number: str):
        # ── 1. Fetch order (ownership enforced by selector) ────────────────
        try:
            order = get_order_by_number(order_number, request.user)
        except Order.DoesNotExist:
            logger.warning(
                "OrderCancelAPIView: not found | "
                "order_number=%s user_id=%s request_id=%s",
                order_number,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(
                message=_("Order not found.")
            )

        # ── 2. Delegate to service ─────────────────────────────────────────
        # DomainError (409, order_not_cancellable) propagates to handler.
        order = OrderService.cancel_order(order=order, user=request.user)

        logger.info(
            "OrderCancelAPIView: OK | "
            "order=%s user_id=%s request_id=%s",
            order_number,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        # ── 3. Re-fetch for fresh serialization ───────────────────────────
        order = get_order_by_number(order.order_number, request.user)

        return self.success_response(
            data=OrderDetailSerializer(order).data,
            message=_("Order cancelled successfully."),
        )