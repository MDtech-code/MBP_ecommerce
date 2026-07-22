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
    create_shipment()  — one transaction.atomic() covers shipment
                         creation + status log + order transition.
    update_status()    — one transaction.atomic() covers status log
                         + shipment update + order sync + stock restore.

Order synchronization rule:
    Order.transition_to() is ALWAYS used for Order status changes.
    Direct Order.status assignment NEVER happens here.
    This guarantees OrderStatusLog is always written.

State machine mapping (Shipment.Status → Order.Status):
    LABEL_CREATED    → PROCESSING   (at shipment creation only)
    PICKED_UP        → SHIPPED      (closes the PROCESSING→DELIVERED gap)
    IN_TRANSIT       → no change
    OUT_FOR_DELIVERY → no change    (notification only)
    DELIVERED        → DELIVERED
    RETURN_REQUESTED → no change    (admin reviews)
    RTO_IN_TRANSIT   → no change
    RTO_DELIVERED    → CANCELLED    (stock restored, COD failed)
    LOST             → no change    (admin decides manually)

Dependency direction:
    models → selectors → services → views
"""

import logging
from decimal import Decimal

from django.db import models, transaction
from django.utils import timezone

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.logistics.models import Shipment, ShipmentStatusLog
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction

logger = logging.getLogger("apps.logistics")


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT STATUS → ORDER STATUS SYNCHRONIZATION MAP
# ─────────────────────────────────────────────────────────────────────────────

# Maps every Shipment.Status to the Order.Status it triggers.
# None means no Order status change for that shipment event.
#
# PICKED_UP → SHIPPED is the critical mapping that closes the
# state machine gap: PROCESSING → SHIPPED → DELIVERED is the
# only valid path to DELIVERED in Order.VALID_TRANSITIONS.
# Without this, DELIVERED webhook silently fails can_transition_to()
# because PROCESSING → DELIVERED is not a valid transition.

SHIPMENT_TO_ORDER_STATUS: dict[str, str | None] = {
    Shipment.Status.LABEL_CREATED:    Order.Status.PROCESSING,
    Shipment.Status.PICKED_UP:        Order.Status.SHIPPED,
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

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE SHIPMENT
    # ─────────────────────────────────────────────────────────────────────────

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
            order:                   Order instance in CONFIRMED status.
            courier:                 CourierPartner choice value.
            tracking_number:         AWB number from courier.
            weight_kg:               Parcel weight for courier records.
            shipping_cost_pkr:       Cost charged by courier to seller.
            estimated_delivery_date: Optional expected delivery date.
            created_by:              Staff User creating this shipment.

        Returns:
            Created Shipment instance.

        Raises:
            DomainError 400 — order not in CONFIRMED status.
            DomainError 409 — active original shipment already exists.
            DomainError 409 — tracking number already in use.
        """

        # ── Pre-checks (outside atomic — read-only queries) ───────────────

        if order.status != Order.Status.CONFIRMED:
            raise DomainError(
                f"Shipment can only be created for CONFIRMED orders. "
                f"Current status: '{order.get_status_display()}'.",
                code=ErrorCode.ORDER_NOT_CONFIRMED,
                status_code=400,
            )

        # No active original shipment must exist.
        # Exclude terminal statuses — RTO_DELIVERED and LOST mean the
        # original shipment is dead and a reshipment is allowed.
        active_shipment_exists = Shipment.objects.filter(
            order=order,
            shipment_type=Shipment.ShipmentType.ORIGINAL,
        ).exclude(
            status__in=[
                Shipment.Status.RTO_DELIVERED,
                Shipment.Status.LOST,
            ]
        ).exists()

        if active_shipment_exists:
            raise DomainError(
                "An active shipment already exists for this order. "
                "Cancel or wait for the existing shipment to complete.",
                code=ErrorCode.SHIPMENT_ALREADY_EXISTS,
                status_code=409,
            )

        if Shipment.objects.filter(tracking_number=tracking_number).exists():
            raise DomainError(
                f"Tracking number '{tracking_number}' is already in use "
                f"by another shipment.",
                code=ErrorCode.TRACKING_NUMBER_EXISTS,
                status_code=409,
            )

        # ── Atomic block ──────────────────────────────────────────────────

        with transaction.atomic():

            is_cod = (order.payment_method == Order.PaymentMethod.COD)
            cod_amount = order.total_price if is_cod else Decimal("0.00")

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

            # Initial status log — from_status is empty string
            # because there is no previous state
            ShipmentStatusLog.objects.create(
                shipment=shipment,
                from_status="",
                to_status=Shipment.Status.LABEL_CREATED,
                source=ShipmentStatusLog.Source.MANUAL,
            )

            # Transition Order: CONFIRMED → PROCESSING
            # transition_to() validates, sets processed_at, writes OrderStatusLog
            order.transition_to(
                Order.Status.PROCESSING,
                changed_by=created_by,
                note=(
                    f"Shipment created. "
                    f"AWB: {tracking_number} via "
                    f"{shipment.get_courier_display()}."
                ),
            )

            logger.info(
                "ShipmentService.create_shipment: created | "
                "order=%s tracking=%s courier=%s cod=%s",
                order.order_number,
                tracking_number,
                courier,
                is_cod,
            )

        # ── Post-atomic ───────────────────────────────────────────────────

        # Notify customer — ORDER_SHIPPED
        # Wrapped in try/except — notification failure must never
        # roll back or block the shipment creation response
        try:
            from apps.notifications.tasks import (
                send_order_shipped_notification,
            )
            send_order_shipped_notification.delay(
                order_id=order.pk,
                tracking_number=tracking_number,
                courier=courier,
            )
        except ImportError:
            logger.warning(
                "ShipmentService.create_shipment: "
                "send_order_shipped_notification task not wired yet | "
                "order=%s",
                order.order_number,
            )

        return shipment

    # ─────────────────────────────────────────────────────────────────────────
    # UPDATE STATUS
    # ─────────────────────────────────────────────────────────────────────────

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

        Creates ShipmentStatusLog for every transition — immutable audit.
        Syncs Order.status via transition_to() when required by the map.
        DELIVERED and RTO_DELIVERED trigger additional side effects.

        State machine map (see module docstring for full table):
            PICKED_UP        → Order.SHIPPED   (critical for DELIVERED path)
            DELIVERED        → Order.DELIVERED + COD SUCCESS + actual_delivery_date
            RTO_DELIVERED    → Order.CANCELLED + stock restored + COD FAILED

        Args:
            shipment:         Shipment instance to update.
            new_status:       Target Shipment.Status value.
            source:           ShipmentStatusLog.Source value.
            updated_by:       User or None (None = system or webhook).
            raw_webhook_data: Raw courier payload for webhook-sourced updates.

        Returns:
            Updated Shipment instance.

        Raises:
            DomainError 400 — new_status is same as current status.
            DomainError 400 — Order transition fails (state machine violation).
        """

        if shipment.status == new_status:
            raise DomainError(
                f"Shipment '{shipment.tracking_number}' is already "
                f"in '{new_status}' status.",
                code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
                status_code=400,
            )

        old_status = shipment.status
        order = shipment.order

        with transaction.atomic():

            # ── 1. Immutable audit log — always first ──────────────────────
            ShipmentStatusLog.objects.create(
                shipment=shipment,
                from_status=old_status,
                to_status=new_status,
                source=source,
                raw_webhook_data=raw_webhook_data,
            )

            # ── 2. Update Shipment.status ──────────────────────────────────
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

            # ── 3. DELIVERED special handling ──────────────────────────────
            if new_status == Shipment.Status.DELIVERED:
                ShipmentService._handle_delivered(
                    shipment=shipment,
                    order=order,
                    updated_by=updated_by,
                )

            # ── 4. RTO_DELIVERED special handling ──────────────────────────
            elif new_status == Shipment.Status.RTO_DELIVERED:
                ShipmentService._handle_rto_delivered(
                    order=order,
                    updated_by=updated_by,
                )

            # ── 5. General Order sync for all other mapped statuses ────────
            else:
                target_order_status = SHIPMENT_TO_ORDER_STATUS.get(new_status)
                if target_order_status is not None:
                    # Raise explicitly — silent skip hides data integrity bugs.
                    # If order cannot transition, something is wrong upstream.
                    if not order.can_transition_to(target_order_status):
                        raise DomainError(
                            f"Cannot sync order '{order.order_number}' "
                            f"to '{target_order_status}'. "
                            f"Current order status: '{order.status}'. "
                            f"This indicates an unexpected state — "
                            f"check order history.",
                            code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
                            status_code=400,
                        )

                    order.transition_to(
                        target_order_status,
                        changed_by=updated_by,
                        note=(
                            f"Auto-synced from shipment status: "
                            f"{new_status}."
                        ),
                    )

        # ── Post-atomic ───────────────────────────────────────────────────

        # Fire notification for this status change
        # Runs outside atomic — notification failure never rolls back
        # the shipment update
        ShipmentService._fire_status_notification(
            order=order,
            new_status=new_status,
            tracking_number=shipment.tracking_number,
        )
        # Product list cache invalidation — ONLY on RTO_DELIVERED
        # because that is the only status that changes product stock.
        # All other status changes do not touch Product.stock.
        if new_status == Shipment.Status.RTO_DELIVERED:
            try:
                from apps.products.services.product_service import ProductService
                ProductService.invalidate_list_cache()
            except ImportError:
                logger.warning(
                    "ShipmentService.update_status: "
                    "ProductService not available for cache invalidation | "
                    "order=%s",
                    order.order_number,
                )

        return shipment

    # ─────────────────────────────────────────────────────────────────────────
    # DELIVERED HANDLER
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _handle_delivered(
        *,
        shipment: Shipment,
        order: Order,
        updated_by,
    ) -> None:
        """
        Handle DELIVERED — parcel confirmed received by customer.

        Sets actual_delivery_date, transitions Order to DELIVERED,
        marks COD PaymentTransaction as SUCCESS.

        Called inside an existing transaction.atomic() block.
        Do not wrap in another atomic here.

        Args:
            shipment:   Shipment instance being marked delivered.
            order:      Related Order instance.
            updated_by: User or None (webhook = None).

        Raises:
            DomainError 400 — Order cannot transition to DELIVERED.
                              This means PICKED_UP was never processed
                              and order is still PROCESSING, not SHIPPED.
                              Admin must first mark the shipment PICKED_UP.
        """

        # Set actual delivery timestamp
        now = timezone.now()
        Shipment.objects.filter(pk=shipment.pk).update(
            actual_delivery_date=now
        )
        shipment.actual_delivery_date = now

        # Transition Order: SHIPPED → DELIVERED
        # This will only succeed if PICKED_UP was processed first
        # (PICKED_UP → Order.SHIPPED) because PROCESSING → DELIVERED
        # is not a valid transition in Order.VALID_TRANSITIONS.
        if not order.can_transition_to(Order.Status.DELIVERED):
            raise DomainError(
                f"Cannot mark order '{order.order_number}' as DELIVERED. "
                f"Current order status is '{order.status}'. "
                f"The shipment must be marked PICKED_UP first so the order "
                f"transitions to SHIPPED before it can reach DELIVERED.",
                code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
                status_code=400,
            )

        order.transition_to(
            Order.Status.DELIVERED,
            changed_by=updated_by,
            note=(
                f"Delivery confirmed by "
                f"{shipment.get_courier_display()}. "
                f"AWB: {shipment.tracking_number}."
            ),
        )

        # Mark COD PaymentTransaction as SUCCESS
        # Only PENDING COD transactions — do not touch online payments
        updated_count = PaymentTransaction.objects.filter(
            order=order,
            gateway=PaymentTransaction.Gateway.COD,
            status=PaymentTransaction.Status.PENDING,
        ).update(status=PaymentTransaction.Status.SUCCESS)

        if updated_count:
            logger.info(
                "ShipmentService._handle_delivered: COD marked SUCCESS | "
                "order=%s transactions_updated=%s",
                order.order_number,
                updated_count,
            )
        else:
            # Log but do not raise — order may be online payment
            # or COD transaction may already be in another state
            logger.warning(
                "ShipmentService._handle_delivered: no PENDING COD "
                "transaction found | order=%s payment_method=%s",
                order.order_number,
                order.payment_method,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # RTO DELIVERED HANDLER
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _handle_rto_delivered(
        *,
        order: Order,
        updated_by,
    ) -> None:
        """
        Handle RTO_DELIVERED — parcel returned to seller warehouse.

        Cancels Order, restores stock for all items via F() expressions,
        decrements Coupon.times_used via F(), marks COD FAILED.

        Called inside an existing transaction.atomic() block.
        Do not wrap in another atomic here.

        Stock restoration uses F() — never Python arithmetic.
        This is the same pattern used in order cancellation.

        CouponUsage is never deleted — RTO is not customer-initiated.
        Coupon.times_used is decremented via F() to reflect the
        coupon being freed without deleting the usage audit record.

        Cache invalidation for product stock is handled post-atomic
        by the caller (update_status) — not here.

        Args:
            order:      Order instance to cancel.
            updated_by: User or None (webhook = None).

        Raises:
            DomainError 400 — Order cannot transition to CANCELLED.
        """

        # Transition Order: current status → CANCELLED
        # Raises explicitly if not possible — do not silently skip
        if not order.can_transition_to(Order.Status.CANCELLED):
            raise DomainError(
                f"Cannot cancel order '{order.order_number}' on RTO. "
                f"Current order status is '{order.status}'. "
                f"Terminal orders (DELIVERED, REFUNDED) cannot be cancelled.",
                code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
                status_code=400,
            )

        order.transition_to(
            Order.Status.CANCELLED,
            changed_by=updated_by,
            note="RTO delivered — parcel returned to seller warehouse.",
        )

        # Restore stock via F() — never Python arithmetic
        # select_related("product") avoids N+1 on the log line below
        order_items = list(
            order.items.select_related("product").all()
        )

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

        # Decrement coupon times_used via F()
        # CouponUsage record is preserved — financial audit trail
        if order.coupon_id:
            from apps.coupons.models import Coupon
            Coupon.objects.filter(pk=order.coupon_id).update(
                times_used=models.F("times_used") - 1
            )
            logger.info(
                "ShipmentService._handle_rto_delivered: "
                "coupon times_used decremented | "
                "order=%s coupon_id=%s",
                order.order_number,
                order.coupon_id,
            )

        # Mark COD PaymentTransaction as FAILED
        # Only PENDING — do not touch already-resolved transactions
        PaymentTransaction.objects.filter(
            order=order,
            status=PaymentTransaction.Status.PENDING,
        ).update(status=PaymentTransaction.Status.FAILED)

        logger.info(
            "ShipmentService._handle_rto_delivered: complete | "
            "order=%s",
            order.order_number,
        )

        # Product list cache invalidation happens post-atomic
        # in update_status() after this method returns and the
        # atomic block commits. Do not call it here.

    # ─────────────────────────────────────────────────────────────────────────
    # NOTIFICATION DISPATCHER
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _fire_status_notification(
        *,
        order: Order,
        new_status: str,
        tracking_number: str,
    ) -> None:
        """
        Dispatch the appropriate Celery notification task for a
        shipment status change.

        Called post-atomic — notification failure never rolls back
        the shipment update. All task imports wrapped in try/except
        because notification tasks may not be wired for all statuses yet.

        Notification type mapping:
            OUT_FOR_DELIVERY → send_out_for_delivery_notification
            DELIVERED        → send_delivery_confirmation_notification
            RTO_DELIVERED    → send_rto_admin_alert

        Args:
            order:           Order instance for context data.
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
                "task not wired yet | order=%s status=%s",
                order.order_number,
                new_status,
            )
# # apps/logistics/services/shipment_service.py
# from __future__ import annotations

# """
# Shipment service — business logic for logistics operations.

# Responsibility:
#     All shipment creation, status transitions, and RTO handling
#     live here. Views pass validated data in. Service returns
#     Shipment instances out.
#     Zero DRF imports. Zero serializer calls. Zero HTTP concerns.

# Transaction boundaries:
#     create_shipment()    — one transaction.atomic() covers shipment
#                            creation + status log + order transition.
#     update_status()      — one transaction.atomic() covers status log
#                            + shipment update + order sync + stock restore.

# Order synchronization rule:
#     Order.transition_to() is ALWAYS used for Order status changes.
#     Direct Order.status assignment NEVER happens here.
#     This guarantees OrderStatusLog is always written.

# Dependency direction:
#     models → selectors → services → views
# """

# import logging

# from django.db import models, transaction
# from django.utils import timezone

# from apps.core.exceptions import DomainError
# from apps.core.error_codes import ErrorCode
# from apps.logistics.models import Shipment, ShipmentStatusLog
# from apps.orders.models import Order
# from apps.payments.models import PaymentTransaction
# from apps.products.services.product_service import ProductService

# logger = logging.getLogger("apps.logistics")


# # ─────────────────────────────────────────────────────────────────────────────
# # SHIPMENT STATUS → ORDER STATUS SYNCHRONIZATION MAP
# # ─────────────────────────────────────────────────────────────────────────────

# # Maps Shipment.Status values to the Order.Status they trigger.
# # None means no Order status change for that shipment event.
# SHIPMENT_TO_ORDER_STATUS: dict[str, str | None] = {
#     Shipment.Status.LABEL_CREATED:    Order.Status.PROCESSING,
#     Shipment.Status.PICKED_UP:        None,
#     Shipment.Status.IN_TRANSIT:       None,
#     Shipment.Status.OUT_FOR_DELIVERY: None,
#     Shipment.Status.DELIVERED:        Order.Status.DELIVERED,
#     Shipment.Status.RETURN_REQUESTED: None,
#     Shipment.Status.RTO_IN_TRANSIT:   None,
#     Shipment.Status.RTO_DELIVERED:    Order.Status.CANCELLED,
#     Shipment.Status.LOST:             None,
# }


# class ShipmentService:
#     """
#     Business operations for Shipment lifecycle management.

#     All methods are static — no instance state required.
#     All methods raise DomainError for business rule violations.
#     Global custom_exception_handler converts DomainError to response.
#     """

#     @staticmethod
#     def create_shipment(
#         *,
#         order: Order,
#         courier: str,
#         tracking_number: str,
#         weight_kg,
#         shipping_cost_pkr,
#         estimated_delivery_date=None,
#         created_by,
#     ) -> Shipment:
#         """
#         Create a shipment record for a CONFIRMED order.

#         Validates order is in CONFIRMED status and no active original
#         shipment already exists. Creates Shipment, ShipmentStatusLog,
#         and transitions Order to PROCESSING — all atomically.

#         Args:
#             order:                  Order instance in CONFIRMED status.
#             courier:                CourierPartner choice value.
#             tracking_number:        AWB number from courier.
#             weight_kg:              Parcel weight for courier records.
#             shipping_cost_pkr:      Cost charged by courier to seller.
#             estimated_delivery_date: Optional expected delivery date.
#             created_by:             Staff User creating this shipment.

#         Returns:
#             Created Shipment instance.

#         Raises:
#             DomainError (400) — order not in CONFIRMED status.
#             DomainError (409) — active original shipment already exists.
#             DomainError (409) — tracking number already in use.
#         """
#         # ── Pre-checks (outside atomic) ───────────────────────────────────

#         # Order must be CONFIRMED before shipment can be created
#         if order.status != Order.Status.CONFIRMED:
#             raise DomainError(
#                 f"Shipment can only be created for CONFIRMED orders. "
#                 f"Current status: '{order.get_status_display()}'.",
#                 code=ErrorCode.ORDER_NOT_CONFIRMED,
#                 status_code=400,
#             )

#         # Check no active original shipment exists
#         existing = Shipment.objects.filter(
#             order=order,
#             shipment_type=Shipment.ShipmentType.ORIGINAL,
#         ).exclude(
#             status__in=[Shipment.Status.RTO_DELIVERED, Shipment.Status.LOST]
#         ).exists()

#         if existing:
#             raise DomainError(
#                 "An active shipment already exists for this order.",
#                 code=ErrorCode.SHIPMENT_ALREADY_EXISTS,
#                 status_code=409,
#             )

#         # Check tracking number uniqueness
#         if Shipment.objects.filter(tracking_number=tracking_number).exists():
#             raise DomainError(
#                 f"Tracking number '{tracking_number}' is already in use.",
#                 code=ErrorCode.TRACKING_NUMBER_EXISTS,
#                 status_code=409,
#             )

#         # ── Atomic block ──────────────────────────────────────────────────
#         with transaction.atomic():

#             # Determine COD fields from order payment method
#             is_cod     = (order.payment_method == Order.PaymentMethod.COD)
#             cod_amount = order.total_price if is_cod else __import__(
#                 "decimal"
#             ).Decimal("0.00")

#             # Create Shipment
#             shipment = Shipment.objects.create(
#                 order=order,
#                 shipment_type=Shipment.ShipmentType.ORIGINAL,
#                 courier=courier,
#                 tracking_number=tracking_number,
#                 status=Shipment.Status.LABEL_CREATED,
#                 is_cod=is_cod,
#                 cod_amount=cod_amount,
#                 shipping_cost_pkr=shipping_cost_pkr,
#                 destination_city=order.shipping_address.city,
#                 weight_kg=weight_kg,
#                 estimated_delivery_date=estimated_delivery_date,
#             )

#             logger.info(
#                 "ShipmentService.create_shipment: created | "
#                 "order=%s tracking=%s courier=%s",
#                 order.order_number,
#                 tracking_number,
#                 courier,
#             )

#             # Create initial ShipmentStatusLog
#             ShipmentStatusLog.objects.create(
#                 shipment=shipment,
#                 from_status="",
#                 to_status=Shipment.Status.LABEL_CREATED,
#                 source=ShipmentStatusLog.Source.MANUAL,
#             )

#             # Transition Order to PROCESSING via state machine
#             order.transition_to(
#                 Order.Status.PROCESSING,
#                 changed_by=created_by,
#                 note=(
#                     f"Shipment created. "
#                     f"AWB: {tracking_number} via "
#                     f"{shipment.get_courier_display()}."
#                 ),
#             )

#         # ── Post-atomic ───────────────────────────────────────────────────
#         # Notify customer — ORDER_SHIPPED
#         try:
#             from apps.notifications.tasks import send_order_shipped_notification
#             send_order_shipped_notification.delay(
#                 order_id=order.pk,
#                 tracking_number=tracking_number,
#                 courier=courier,
#             )
#         except ImportError:
#             logger.warning(
#                 "ShipmentService.create_shipment: "
#                 "shipped notification task not available | order=%s",
#                 order.order_number,
#             )

#         return shipment

#     @staticmethod
#     def update_status(
#         *,
#         shipment: Shipment,
#         new_status: str,
#         source: str,
#         updated_by=None,
#         raw_webhook_data: dict | None = None,
#     ) -> Shipment:
#         """
#         Transition a shipment to a new status and sync Order accordingly.

#         Creates ShipmentStatusLog for every transition.
#         Syncs Order.status via transition_to() when required.
#         Handles DELIVERED and RTO_DELIVERED special cases atomically.

#         Args:
#             shipment:         Shipment instance to update.
#             new_status:       Target Shipment.Status value.
#             source:           ShipmentStatusLog.Source value.
#             updated_by:       User or None (None = system/webhook).
#             raw_webhook_data: Raw courier payload for webhook-sourced updates.

#         Returns:
#             Updated Shipment instance.

#         Raises:
#             DomainError (400) — new_status is same as current status.
#         """
#         if shipment.status == new_status:
#             raise DomainError(
#                 f"Shipment is already in '{new_status}' status.",
#                 code=ErrorCode.INVALID_SHIPMENT_TRANSITION,
#                 status_code=400,
#             )

#         old_status = shipment.status
#         order      = shipment.order

#         with transaction.atomic():

#             # Create ShipmentStatusLog first — immutable audit entry
#             ShipmentStatusLog.objects.create(
#                 shipment=shipment,
#                 from_status=old_status,
#                 to_status=new_status,
#                 source=source,
#                 raw_webhook_data=raw_webhook_data,
#             )

#             # Update Shipment status
#             Shipment.objects.filter(pk=shipment.pk).update(status=new_status)
#             shipment.status = new_status

#             logger.info(
#                 "ShipmentService.update_status: %s → %s | "
#                 "tracking=%s order=%s source=%s",
#                 old_status,
#                 new_status,
#                 shipment.tracking_number,
#                 order.order_number,
#                 source,
#             )

#             # ── DELIVERED special handling ─────────────────────────────────
#             if new_status == Shipment.Status.DELIVERED:
#                 shipment.actual_delivery_date = timezone.now()
#                 Shipment.objects.filter(pk=shipment.pk).update(
#                     actual_delivery_date=shipment.actual_delivery_date
#                 )

#                 # Transition Order to DELIVERED
#                 if order.can_transition_to(Order.Status.DELIVERED):
#                     order.transition_to(
#                         Order.Status.DELIVERED,
#                         changed_by=updated_by,
#                         note=(
#                             f"Delivered confirmed by "
#                             f"{shipment.get_courier_display()} webhook."
#                         ),
#                     )

#                 # Mark COD PaymentTransaction as SUCCESS
#                 PaymentTransaction.objects.filter(
#                     order=order,
#                     gateway=PaymentTransaction.Gateway.COD,
#                     status=PaymentTransaction.Status.PENDING,
#                 ).update(status=PaymentTransaction.Status.SUCCESS)

#                 logger.info(
#                     "ShipmentService.update_status: COD transaction "
#                     "marked SUCCESS | order=%s",
#                     order.order_number,
#                 )

#             # ── RTO_DELIVERED special handling ─────────────────────────────
#             elif new_status == Shipment.Status.RTO_DELIVERED:
#                 ShipmentService._handle_rto_delivered(
#                     order=order,
#                     updated_by=updated_by,
#                 )

#         # ── Post-atomic ───────────────────────────────────────────────────
#         # Sync Order status for non-special transitions
#         order_status = SHIPMENT_TO_ORDER_STATUS.get(new_status)
#         if order_status and new_status not in (
#             Shipment.Status.DELIVERED,
#             Shipment.Status.RTO_DELIVERED,
#         ):
#             # These are handled inside atomic above — skip here
#             pass

#         # Customer notification based on new shipment status
#         ShipmentService._fire_status_notification(
#             order=order,
#             new_status=new_status,
#             tracking_number=shipment.tracking_number,
#         )

#         # Cache invalidation — order status may have changed
#         ProductService.invalidate_list_cache()

#         return shipment

#     @staticmethod
#     def _handle_rto_delivered(*, order: Order, updated_by) -> None:
#         """
#         Handle RTO_DELIVERED — parcel returned to seller warehouse.

#         Cancels the Order, restores stock for all items via F(),
#         decrements coupon times_used if coupon was applied.
#         Called inside an existing transaction.atomic() block from
#         update_status() — do not wrap in another atomic here.

#         Args:
#             order:      Order instance to cancel.
#             updated_by: User or None (None = system/webhook).
#         """
#         # Transition Order to CANCELLED via state machine
#         if order.can_transition_to(Order.Status.CANCELLED):
#             order.transition_to(
#                 Order.Status.CANCELLED,
#                 changed_by=updated_by,
#                 note="RTO delivered — parcel returned to warehouse.",
#             )

#         # Restore stock via F() — same pattern as customer cancel
#         order_items = list(order.items.select_related("product").all())
#         for item in order_items:
#             from apps.products.models import Product
#             Product.objects.filter(pk=item.product_id).update(
#                 stock=models.F("stock") + item.quantity
#             )

#         logger.info(
#             "ShipmentService._handle_rto_delivered: stock restored | "
#             "order=%s items=%s",
#             order.order_number,
#             [(i.product_id, i.quantity) for i in order_items],
#         )

#         # Decrement coupon times_used if coupon was applied
#         # CouponUsage is a financial record — never delete it
#         if order.coupon_id:
#             from apps.coupons.models import Coupon
#             Coupon.objects.filter(pk=order.coupon_id).update(
#                 times_used=models.F("times_used") - 1
#             )
#             logger.info(
#                 "ShipmentService._handle_rto_delivered: "
#                 "coupon times_used decremented | order=%s coupon_id=%s",
#                 order.order_number,
#                 order.coupon_id,
#             )

#         # Mark COD PaymentTransaction as FAILED
#         PaymentTransaction.objects.filter(
#             order=order,
#             status=PaymentTransaction.Status.PENDING,
#         ).update(status=PaymentTransaction.Status.FAILED)

#         # Post-atomic cache invalidation (called after outer atomic commits)
#         # Cannot call here — still inside atomic. Caller handles this.
#         logger.info(
#             "ShipmentService._handle_rto_delivered: complete | order=%s",
#             order.order_number,
#         )

#     @staticmethod
#     def _fire_status_notification(
#         *,
#         order: Order,
#         new_status: str,
#         tracking_number: str,
#     ) -> None:
#         """
#         Dispatch the appropriate notification task for a shipment status change.

#         Wraps task imports in try/except — notification tasks may not
#         be wired for all status values yet.

#         Args:
#             order:           Order instance for context.
#             new_status:      New Shipment.Status value.
#             tracking_number: AWB for inclusion in notification body.
#         """
#         try:
#             if new_status == Shipment.Status.OUT_FOR_DELIVERY:
#                 from apps.notifications.tasks import (
#                     send_out_for_delivery_notification,
#                 )
#                 send_out_for_delivery_notification.delay(
#                     order_id=order.pk,
#                     tracking_number=tracking_number,
#                 )
#             elif new_status == Shipment.Status.DELIVERED:
#                 from apps.notifications.tasks import (
#                     send_delivery_confirmation_notification,
#                 )
#                 send_delivery_confirmation_notification.delay(
#                     order_id=order.pk,
#                 )
#             elif new_status == Shipment.Status.RTO_DELIVERED:
#                 from apps.notifications.tasks import send_rto_admin_alert
#                 send_rto_admin_alert.delay(order_id=order.pk)
#         except ImportError:
#             logger.warning(
#                 "ShipmentService._fire_status_notification: "
#                 "task not available | order=%s status=%s",
#                 order.order_number,
#                 new_status,
#             )