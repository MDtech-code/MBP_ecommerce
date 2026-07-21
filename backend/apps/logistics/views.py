# apps/logistics/views.py
from __future__ import annotations

"""
Logistics app — view layer.

Responsibility:
    HTTP concerns only: parse request, validate input via serializers,
    call service layer for mutations, call selectors for reads,
    serialize results, return standardized response via BaseAPIView helpers.
    Zero business logic. Zero transaction management. Zero direct ORM mutations.

Permission policy:
    All admin endpoints: IsAuthenticated + IsAdmin.
    Customer tracking:  IsAuthenticated only — ownership via order selector.

Exception handling:
    DomainError from service propagates to global handler automatically.
    Order.DoesNotExist → 404.
    Shipment.DoesNotExist → 404.

Dependency direction:
    selectors/shipment.py       (reads)
    services/shipment_service.py (mutations)
         ↑
    views.py  ← this file
"""

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.core.api.views import BaseAPIView
from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from apps.core.pagination import build_pagination_meta, get_pagination_params
from apps.core.permissions import IsAdmin
from apps.logistics.models import Shipment, ShipmentStatusLog
from apps.logistics.selectors.shipment import (
    get_shipment_by_tracking,
    get_shipment_for_order,
    
)
from apps.logistics.serializers import (
    OrderTrackingSerializer,
   
)
from apps.logistics.services.shipment_service import ShipmentService
from apps.orders.models import Order
from apps.orders.selectors.order import get_order_by_number

logger = logging.getLogger("apps.logistics")

'''
# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT LIST + CREATE (Admin)
# ─────────────────────────────────────────────────────────────────────────────


class ShipmentListCreateAPIView(BaseAPIView):
    """
    GET  /api/logistics/shipments/  — paginated shipment list (admin)
    POST /api/logistics/shipments/  — create shipment for confirmed order

    GET supports optional query filters:
        ?status=delivered
        ?courier=postex
        ?city=Lahore
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request: Request):
        # ── 1. Pagination params ───────────────────────────────────────────
        params = get_pagination_params(request, default_page_size=20)
        if not params.is_valid:
            return self.error_response(
                message=_("Invalid pagination parameters."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── 2. Read optional filters from query params ─────────────────────
        status_filter  = request.query_params.get("status")
        courier_filter = request.query_params.get("courier")
        city_filter    = request.query_params.get("city")

        # ── 3. Fetch queryset ──────────────────────────────────────────────
        queryset = list_shipments(
            status=status_filter,
            courier=courier_filter,
            city=city_filter,
        )
        total = queryset.count()

        # ── 4. Paginate ────────────────────────────────────────────────────
        offset    = (params.page - 1) * params.page_size
        shipments = queryset[offset: offset + params.page_size]

        # ── 5. Serialize + respond ─────────────────────────────────────────
        meta = build_pagination_meta(params.page, params.page_size, total)

        logger.info(
            "ShipmentListCreateAPIView.get: OK | "
            "admin=%s total=%s request_id=%s",
            request.user.pk,
            total,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=ShipmentListSerializer(shipments, many=True).data,
            message=_("Shipments retrieved successfully."),
            meta=meta,
        )

    def post(self, request: Request):
        # ── 1. Validate input ──────────────────────────────────────────────
        serializer = ShipmentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "ShipmentListCreateAPIView.post: validation failed | "
                "admin=%s errors=%s request_id=%s",
                request.user.pk,
                serializer.errors,
                getattr(request, "id", "n/a"),
            )
            return self.error_response(
                message=_("Could not create shipment."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── 2. Fetch order by order_number from request body ───────────────
        order_number = request.data.get("order_number", "").strip()
        if not order_number:
            return self.error_response(
                message=_("order_number is required."),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            order = Order.objects.select_related(
                "shipping_address"
            ).get(order_number=order_number)
        except Order.DoesNotExist:
            return self.not_found_response(
                message=_("Order not found.")
            )

        # ── 3. Delegate to service ─────────────────────────────────────────
        vd       = serializer.validated_data
        shipment = ShipmentService.create_shipment(
            order=order,
            courier=vd["courier"],
            tracking_number=vd["tracking_number"],
            weight_kg=vd["weight_kg"],
            shipping_cost_pkr=vd["shipping_cost_pkr"],
            estimated_delivery_date=vd.get("estimated_delivery_date"),
            created_by=request.user,
        )

        logger.info(
            "ShipmentListCreateAPIView.post: OK | "
            "order=%s tracking=%s admin=%s request_id=%s",
            order_number,
            vd["tracking_number"],
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        return self.created_response(
            data=ShipmentDetailSerializer(shipment).data,
            message=_("Shipment created successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT DETAIL (Admin)
# ─────────────────────────────────────────────────────────────────────────────


class ShipmentDetailAPIView(BaseAPIView):
    """
    GET /api/logistics/shipments/<tracking_number>/

    Returns full shipment detail including status log history.
    Admin only.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request: Request, tracking_number: str):
        try:
            shipment = get_shipment_by_tracking(tracking_number)
        except Shipment.DoesNotExist:
            logger.warning(
                "ShipmentDetailAPIView: not found | "
                "tracking=%s admin=%s request_id=%s",
                tracking_number,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(
                message=_("Shipment not found.")
            )

        logger.info(
            "ShipmentDetailAPIView: OK | "
            "tracking=%s admin=%s request_id=%s",
            tracking_number,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=ShipmentDetailSerializer(shipment).data,
            message=_("Shipment retrieved successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT STATUS UPDATE (Admin)
# ─────────────────────────────────────────────────────────────────────────────


class ShipmentStatusUpdateAPIView(BaseAPIView):
    """
    PATCH /api/logistics/shipments/<tracking_number>/status/

    Manually update shipment status. Used when courier webhook
    is unavailable or for manual corrections. Admin only.
    Creates ShipmentStatusLog and syncs Order status automatically
    via ShipmentService.update_status().
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request: Request, tracking_number: str):
        # ── 1. Fetch shipment ──────────────────────────────────────────────
        try:
            shipment = get_shipment_by_tracking(tracking_number)
        except Shipment.DoesNotExist:
            logger.warning(
                "ShipmentStatusUpdateAPIView: not found | "
                "tracking=%s admin=%s request_id=%s",
                tracking_number,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(
                message=_("Shipment not found.")
            )

        # ── 2. Validate input ──────────────────────────────────────────────
        serializer = ShipmentStatusUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "ShipmentStatusUpdateAPIView: validation failed | "
                "tracking=%s errors=%s request_id=%s",
                tracking_number,
                serializer.errors,
                getattr(request, "id", "n/a"),
            )
            return self.error_response(
                message=_("Could not update shipment status."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # ── 3. Delegate to service ─────────────────────────────────────────
        shipment = ShipmentService.update_status(
            shipment=shipment,
            new_status=serializer.validated_data["new_status"],
            source=ShipmentStatusLog.Source.MANUAL,
            updated_by=request.user,
        )

        logger.info(
            "ShipmentStatusUpdateAPIView: OK | "
            "tracking=%s new_status=%s admin=%s request_id=%s",
            tracking_number,
            serializer.validated_data["new_status"],
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        # Re-fetch for fresh serialization with updated status_logs
        shipment = get_shipment_by_tracking(tracking_number)
        return self.success_response(
            data=ShipmentDetailSerializer(shipment).data,
            message=_("Shipment status updated successfully."),
        )

'''
# ─────────────────────────────────────────────────────────────────────────────
# ORDER TRACKING (Customer-facing)
# ─────────────────────────────────────────────────────────────────────────────


class OrderTrackingAPIView(BaseAPIView):
    """
    GET /api/orders/<order_number>/tracking/

    Returns shipment tracking information for a specific order.
    Scoped to the requesting user — ownership enforced by
    get_order_by_number() which filters by both order_number AND user.

    Returns 404 if no shipment created yet for this order.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, order_number: str):
        # ── 1. Fetch order (ownership enforced by selector) ────────────────
        try:
            order = get_order_by_number(order_number, request.user)
        except Order.DoesNotExist:
            logger.warning(
                "OrderTrackingAPIView: order not found | "
                "order_number=%s user_id=%s request_id=%s",
                order_number,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(message=_("Order not found."))

        # ── 2. Fetch shipment for this order ───────────────────────────────
        shipment = get_shipment_for_order(order)
        if shipment is None:
            raise DomainError(
                "No shipment has been created for this order yet.",
                code=ErrorCode.ORDER_HAS_NO_SHIPMENT,
                status_code=400,
            )

        logger.info(
            "OrderTrackingAPIView: OK | "
            "order=%s user_id=%s request_id=%s",
            order_number,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=OrderTrackingSerializer(shipment).data,
            message=_("Tracking information retrieved successfully."),
        )