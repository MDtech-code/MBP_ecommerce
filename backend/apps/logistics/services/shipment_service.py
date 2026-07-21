# apps/logistics/services/shipment_service.py
from __future__ import annotations

"""
Shipment service — business logic for logistics operations.

Responsibility:
    All shipment creation, status transitions, and RTO handling
    live here. Views pass validated data in. Service returns
    Shipment instances out.
    Zero DRF imports. Zero serializer calls. Zero HTTP concerns.

Transaction boundaries:
    create_shipment()    — one transaction.atomic() covers shipment
                           creation + status log + order transition.
    update_status()      — one transaction.atomic() covers status log
                           + shipment update + order sync + stock restore.

Order synchronization rule:
    Order.transition_to() is ALWAYS used for Order status changes.
    Direct Order.status assignment NEVER happens here.
    This guarantees OrderStatusLog is always written.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db import models, transaction
from django.utils import timezone

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.logistics.models import Shipment, ShipmentStatusLog
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction
from apps.products.services.product_service import ProductService

logger = logging.getLogger("apps.logistics")


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT STATUS → ORDER STATUS SYNCHRONIZATION MAP
# ─────────────────────────────────────────────────────────────────────────────

# Maps Shipment.Status values to the Order.Status they trigger.
# None means no Order status change for that shipment event.
SHIPMENT_TO_ORDER_STATUS: dict[str, str | None] = {
    Shipment.Status.LABEL_CREATED:    Order.Status.PROCESSING,
    Shipment.Status.PICKED_UP:        None,
    Shipment.Status.IN_TRANSIT:       None,
    Shipment.Status.OUT_FOR_DELIVERY: None,
    Shipment.Status.DELIVERED:        Order.Status.DELIVERED,
    Shipment.Status.RETURN_REQUESTED: None,
    Shipment.Status.RTO_IN_TRANSIT:   None,
    Shipment.Status.RTO_DELIVERED:    Order.Status.CANCELLED,
    Shipment.Status.LOST:             None,
}


class ShipmentService:
    """
    Business operations for Shipment lifecycle management.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    Global custom_exception_handler converts DomainError to response.
    """

    @staticmethod
    def create_shipment(
        *,
        order: Order,
        courier: str,
        tracking_number: str,
        weight_kg,
        shipping_cost_pkr,
        estimated_delivery_date=None,
        created_by,
    ) -> Shipment:
        """
        Create a shipment record for a CONFIRMED order.

        Validates order is in CONFIRMED status and no active original
        shipment already exists. Creates Shipment, ShipmentStatusLog,
        and transitions Order to PROCESSING — all atomically.

        Args:
            order:                  Order instance in CONFIRMED status.
            courier:                CourierPartner choice value.
            tracking_number:        AWB number from courier.
            weight_kg:              Parcel weight for courier records.
            shipping_cost_pkr:      Cost charged by courier to seller.
            estimated_delivery_date: Optional expected delivery date.
            created_by:             Staff User creating this shipment.

        Returns:
            Created Shipment instance.

        Raises:
            DomainError (400) — order not in CONFIRMED status.
            DomainError (409) — active original shipment already exists.
            DomainError (409) — tracking number already in use.
        """
        # ── Pre-checks (outside atomic) ───────────────────────────────────

        # Order must be CONFIRMED before shipment can be created
        if order.status != Order.Status.CONFIRMED:
            raise DomainError(
                f"Shipment can only be created for CONFIRMED orders. "
                f"Current status: '{order.get_status_display()}'.",
                code=ErrorCode.ORDER_NOT_CONFIRMED,
                status_code=400,
            )

        # Check no active original shipment exists
        existing = Shipment.objects.filter(
            order=order,
            shipment_type=Shipment.ShipmentType.ORIGINAL,
        ).exclude(
            status__in=[Shipment.Status.RTO_DELIVERED, Shipment.Status.LOST]
        ).exists()

        if existing:
            raise DomainError(
                "An active shipment already exists for this order.",
                code=ErrorCode.SHIPMENT_ALREADY_EXISTS,
                status_code=409,
            )

        # Check tracking number uniqueness
        if Shipment.objects.filter(tracking_number=tracking_number).exists():
            raise DomainError(
                f"Tracking number '{tracking_number}' is already in use.",
                code=ErrorCode.TRACKING_NUMBER_EXISTS,
                status_code=409,
            )

        # ── Atomic block ──────────────────────────────────────────────────
        with transaction.atomic():

            # Determine COD fields from order payment method
            is_cod     = (order.payment_method == Order.PaymentMethod.COD)
            cod_amount = order.total_price if is_cod else __import__(
                "decimal"
            ).Decimal("0.00")

            # Create Shipment
            shipment = Shipment.objects.create(
                order=order,
                shipment_type=Shipment.ShipmentType.ORIGINAL,
                courier=courier,
                tracking_number=tracking_number,
                status=Shipment.Status.LABEL_CREATED,
                is_cod=is_cod,
                cod_amount=cod_amount,
                shipping_cost_pkr=shipping_cost_pkr,
                destination_city=order.shipping_address.city,
                weight_kg=weight_kg,
                estimated_delivery_date=estimated_delivery_date,
            )

            logger.info(
                "ShipmentService.create_shipment: created | "
                "order=%s tracking=%s courier=%s",
                order.order_number,
                tracking_number,
                courier,
            )

            # Create initial ShipmentStatusLog
            ShipmentStatusLog.objects.create(
                shipment=shipment,
                from_status="",
                to_status=Shipment.Status.LABEL_CREATED,
                source=ShipmentStatusLog.Source.MANUAL,
            )

            # Transition Order to PROCESSING via state machine
            order.transition_to(
                Order.Status.PROCESSING,
                changed_by=created_by,
                note=(
                    f"Shipment created. "
                    f"AWB: {tracking_number} via "
                    f"{shipment.get_courier_display()}."
                ),
            )

        # ── Post-atomic ───────────────────────────────────────────────────
        # Notify customer — ORDER_SHIPPED
        try:
            from apps.notifications.tasks import send_order_shipped_notification
            send_order_shipped_notification.delay(
                order_id=order.pk,
                tracking_number=tracking_number,
                courier=courier,
            )
        except ImportError:
            logger.warning(
                "ShipmentService.create_shipment: "
                "shipped notification task not available | order=%s",
                order.order_number,
            )

        return shipment

    @staticmethod
    def update_status(
        *,
        shipment: Shipment,
        new_status: str,
        source: str,
        updated_by=None,
        raw_webhook_data: dict | None = None,
    ) -> Shipment:
        """
        Transition a shipment to a new status and sync Order accordingly.

        Creates ShipmentStatusLog for every transition.
        Syncs Order.status via transition_to() when required.
        Handles DELIVERED and RTO_DELIVERED special cases atomically.

        Args:
            shipment:         Shipment instance to update.
            new_status:       Target Shipment.Status value.
            source:           ShipmentStatusLog.Source value.
            updated_by:       User or None (None = system/webhook).
            raw_webhook_data: Raw courier payload for webhook-sourced updates.

        Returns:
            Updated Shipment instance.

        Raises:
            DomainError (400) — new_status is same as current status.
        """
        if shipment.status == new_status:
            raise DomainError(
                f"Shipment is already in '{new_status}' status.",
                code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
                status_code=400,
            )

        old_status = shipment.status
        order      = shipment.order

        with transaction.atomic():

            # Create ShipmentStatusLog first — immutable audit entry
            ShipmentStatusLog.objects.create(
                shipment=shipment,
                from_status=old_status,
                to_status=new_status,
                source=source,
                raw_webhook_data=raw_webhook_data,
            )

            # Update Shipment status
            Shipment.objects.filter(pk=shipment.pk).update(status=new_status)
            shipment.status = new_status

            logger.info(
                "ShipmentService.update_status: %s → %s | "
                "tracking=%s order=%s source=%s",
                old_status,
                new_status,
                shipment.tracking_number,
                order.order_number,
                source,
            )

            # ── DELIVERED special handling ─────────────────────────────────
            if new_status == Shipment.Status.DELIVERED:
                shipment.actual_delivery_date = timezone.now()
                Shipment.objects.filter(pk=shipment.pk).update(
                    actual_delivery_date=shipment.actual_delivery_date
                )

                # Transition Order to DELIVERED
                if order.can_transition_to(Order.Status.DELIVERED):
                    order.transition_to(
                        Order.Status.DELIVERED,
                        changed_by=updated_by,
                        note=(
                            f"Delivered confirmed by "
                            f"{shipment.get_courier_display()} webhook."
                        ),
                    )

                # Mark COD PaymentTransaction as SUCCESS
                PaymentTransaction.objects.filter(
                    order=order,
                    gateway=PaymentTransaction.Gateway.COD,
                    status=PaymentTransaction.Status.PENDING,
                ).update(status=PaymentTransaction.Status.SUCCESS)

                logger.info(
                    "ShipmentService.update_status: COD transaction "
                    "marked SUCCESS | order=%s",
                    order.order_number,
                )

            # ── RTO_DELIVERED special handling ─────────────────────────────
            elif new_status == Shipment.Status.RTO_DELIVERED:
                ShipmentService._handle_rto_delivered(
                    order=order,
                    updated_by=updated_by,
                )

        # ── Post-atomic ───────────────────────────────────────────────────
        # Sync Order status for non-special transitions
        order_status = SHIPMENT_TO_ORDER_STATUS.get(new_status)
        if order_status and new_status not in (
            Shipment.Status.DELIVERED,
            Shipment.Status.RTO_DELIVERED,
        ):
            # These are handled inside atomic above — skip here
            pass

        # Customer notification based on new shipment status
        ShipmentService._fire_status_notification(
            order=order,
            new_status=new_status,
            tracking_number=shipment.tracking_number,
        )

        # Cache invalidation — order status may have changed
        ProductService.invalidate_list_cache()

        return shipment

    @staticmethod
    def _handle_rto_delivered(*, order: Order, updated_by) -> None:
        """
        Handle RTO_DELIVERED — parcel returned to seller warehouse.

        Cancels the Order, restores stock for all items via F(),
        decrements coupon times_used if coupon was applied.
        Called inside an existing transaction.atomic() block from
        update_status() — do not wrap in another atomic here.

        Args:
            order:      Order instance to cancel.
            updated_by: User or None (None = system/webhook).
        """
        # Transition Order to CANCELLED via state machine
        if order.can_transition_to(Order.Status.CANCELLED):
            order.transition_to(
                Order.Status.CANCELLED,
                changed_by=updated_by,
                note="RTO delivered — parcel returned to warehouse.",
            )

        # Restore stock via F() — same pattern as customer cancel
        order_items = list(order.items.select_related("product").all())
        for item in order_items:
            from apps.products.models import Product
            Product.objects.filter(pk=item.product_id).update(
                stock=models.F("stock") + item.quantity
            )

        logger.info(
            "ShipmentService._handle_rto_delivered: stock restored | "
            "order=%s items=%s",
            order.order_number,
            [(i.product_id, i.quantity) for i in order_items],
        )

        # Decrement coupon times_used if coupon was applied
        # CouponUsage is a financial record — never delete it
        if order.coupon_id:
            from apps.coupons.models import Coupon
            Coupon.objects.filter(pk=order.coupon_id).update(
                times_used=models.F("times_used") - 1
            )
            logger.info(
                "ShipmentService._handle_rto_delivered: "
                "coupon times_used decremented | order=%s coupon_id=%s",
                order.order_number,
                order.coupon_id,
            )

        # Mark COD PaymentTransaction as FAILED
        PaymentTransaction.objects.filter(
            order=order,
            status=PaymentTransaction.Status.PENDING,
        ).update(status=PaymentTransaction.Status.FAILED)

        # Post-atomic cache invalidation (called after outer atomic commits)
        # Cannot call here — still inside atomic. Caller handles this.
        logger.info(
            "ShipmentService._handle_rto_delivered: complete | order=%s",
            order.order_number,
        )

    @staticmethod
    def _fire_status_notification(
        *,
        order: Order,
        new_status: str,
        tracking_number: str,
    ) -> None:
        """
        Dispatch the appropriate notification task for a shipment status change.

        Wraps task imports in try/except — notification tasks may not
        be wired for all status values yet.

        Args:
            order:           Order instance for context.
            new_status:      New Shipment.Status value.
            tracking_number: AWB for inclusion in notification body.
        """
        try:
            if new_status == Shipment.Status.OUT_FOR_DELIVERY:
                from apps.notifications.tasks import (
                    send_out_for_delivery_notification,
                )
                send_out_for_delivery_notification.delay(
                    order_id=order.pk,
                    tracking_number=tracking_number,
                )
            elif new_status == Shipment.Status.DELIVERED:
                from apps.notifications.tasks import (
                    send_delivery_confirmation_notification,
                )
                send_delivery_confirmation_notification.delay(
                    order_id=order.pk,
                )
            elif new_status == Shipment.Status.RTO_DELIVERED:
                from apps.notifications.tasks import send_rto_admin_alert
                send_rto_admin_alert.delay(order_id=order.pk)
        except ImportError:
            logger.warning(
                "ShipmentService._fire_status_notification: "
                "task not available | order=%s status=%s",
                order.order_number,
                new_status,
            )