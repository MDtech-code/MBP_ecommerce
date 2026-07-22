# apps/logistics/services/shipment_service.py
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from apps.logistics.couriers.base import BaseCourierClient,BookingResponse
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
        tracking_number: str | None = None,
        weight_kg,
        shipping_cost_pkr,
        estimated_delivery_date=None,
        created_by,
    ) -> Shipment:
        """
        Create a shipment record for a CONFIRMED order.

        Phase 4 behaviour — two paths depending on courier:

        Path A — API-enabled courier (postex, tcs, leopards):
            tracking_number argument is ignored if provided.
            ShipmentService calls the courier API to book the shipment
            and receives the AWB number from the API response.
            Admin does not need to enter a tracking number manually.

        Path B — Manual courier (self_delivery or API not configured):
            tracking_number argument is required.
            Same flow as Phase 1 — admin enters AWB manually.
            Used for self_delivery and as fallback when API
            credentials are not yet set up.

        Migration path to Option B (Celery async booking):
            When volume requires async, change Path A to:
                1. Create shipment with status=PENDING_LABEL
                2. Dispatch Celery task with shipment.pk
                3. Task calls _book_via_api() and updates shipment
            The _book_via_api() helper below does not change.
            Only the orchestration here changes.

        Pre-checks (outside atomic):
            1. Order must be CONFIRMED.
            2. No active original shipment for this order.
            3. For manual path: tracking_number uniqueness checked.

        Inside atomic:
            Step A — Call courier API (Path A only)
            Step B — Create Shipment record
            Step C — Create ShipmentStatusLog
            Step D — Transition Order to PROCESSING

        Post-atomic:
            Notification task dispatched.

        Args:
            order:                   Order instance in CONFIRMED status.
            courier:                 CourierPartner choice value.
            tracking_number:         AWB for manual path. None triggers
                                     API booking on Path A.
            weight_kg:               Parcel weight.
            shipping_cost_pkr:       Courier charge to seller.
            estimated_delivery_date: Optional expected delivery date.
            created_by:              Staff User creating this shipment.

        Returns:
            Created Shipment instance with AWB from API or manual entry.

        Raises:
            DomainError 400  — order not in CONFIRMED status.
            DomainError 409  — active original shipment already exists.
            DomainError 409  — tracking number already in use (manual).
            DomainError 400  — tracking number missing for manual courier.
            InfrastructureError 503 — courier API timeout or error.
        """

        # ── Pre-check 1 — order must be CONFIRMED ─────────────────────────

        if order.status != Order.Status.CONFIRMED:
            raise DomainError(
                f"Shipment can only be created for CONFIRMED orders. "
                f"Current status: '{order.get_status_display()}'.",
                code=ErrorCode.ORDER_NOT_CONFIRMED,
                status_code=400,
            )

        # ── Pre-check 2 — no active original shipment ─────────────────────

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

        # ── Determine path: API booking or manual ─────────────────────────

        from apps.logistics.couriers.registry import get_courier_client
        courier_client = get_courier_client(courier)
        use_api = courier_client is not None

        # ── Pre-check 3 — manual path requires tracking_number ────────────

        if not use_api:
            if not tracking_number:
                raise DomainError(
                    f"A tracking number (AWB) is required for "
                    f"'{courier}' shipments. "
                    f"Enter the AWB provided by the courier.",
                    code=ErrorCode.ORDER_NOT_CONFIRMED,
                    status_code=400,
                )
            if Shipment.objects.filter(
                tracking_number=tracking_number
            ).exists():
                raise DomainError(
                    f"Tracking number '{tracking_number}' is already "
                    f"in use by another shipment.",
                    code=ErrorCode.TRACKING_NUMBER_EXISTS,
                    status_code=409,
                )

        # ── Atomic block ──────────────────────────────────────────────────

        with transaction.atomic():

            is_cod = (order.payment_method == Order.PaymentMethod.COD)
            cod_amount = order.total_price if is_cod else Decimal("0.00")

            # ── Step A — API booking (Path A only) ────────────────────────

            raw_courier_response = None

            if use_api:
                # Build courier-agnostic BookingRequest from model data
                booking_response = ShipmentService._book_via_api(
                    courier_client=courier_client,
                    order=order,
                    cod_amount=cod_amount,
                    weight_kg=weight_kg,
                    is_cod=is_cod,
                )
                # AWB comes from courier API — not from admin input
                tracking_number      = booking_response.awb_number
                raw_courier_response = booking_response.raw_response

                logger.info(
                    "ShipmentService.create_shipment: API booking success | "
                    "order=%s courier=%s awb=%s",
                    order.order_number,
                    courier,
                    tracking_number,
                )

            # ── Step B — Create Shipment ───────────────────────────────────

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
                raw_courier_response=raw_courier_response,
            )

            # ── Step C — Initial status log ────────────────────────────────

            ShipmentStatusLog.objects.create(
                shipment=shipment,
                from_status="",
                to_status=Shipment.Status.LABEL_CREATED,
                source=ShipmentStatusLog.Source.SYSTEM if use_api
                       else ShipmentStatusLog.Source.MANUAL,
            )

            # ── Step D — Transition Order: CONFIRMED → PROCESSING ──────────

            order.transition_to(
                Order.Status.PROCESSING,
                changed_by=created_by,
                note=(
                    f"Shipment created via "
                    f"{'API' if use_api else 'manual entry'}. "
                    f"AWB: {tracking_number} via "
                    f"{shipment.get_courier_display()}."
                ),
            )

            logger.info(
                "ShipmentService.create_shipment: created | "
                "order=%s tracking=%s courier=%s cod=%s path=%s",
                order.order_number,
                tracking_number,
                courier,
                is_cod,
                "api" if use_api else "manual",
            )

        # ── Post-atomic — notification ────────────────────────────────────

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
    # PRIVATE — API BOOKING HELPER
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _book_via_api(
        *,
        courier_client: "BaseCourierClient",
        order: Order,
        cod_amount: Decimal,
        weight_kg,
        is_cod: bool,
    ) -> "BookingResponse":
        """
        Build BookingRequest from Order data and call courier API.

        Separated from create_shipment() so it can be called from
        a Celery task in Option B (async) without changing the
        courier client interface or the BookingRequest structure.

        This method is called inside transaction.atomic() in
        create_shipment(). InfrastructureError raised here will
        roll back the atomic block — no partial shipment is created.

        Args:
            courier_client: Instantiated BaseCourierClient subclass.
            order:          Order instance with shipping_address loaded.
            cod_amount:     Decimal PKR amount for COD collection.
            weight_kg:      Parcel weight.
            is_cod:         True for COD orders.

        Returns:
            BookingResponse with awb_number from courier API.

        Raises:
            InfrastructureError — on any courier API failure.
        """
        from apps.logistics.couriers.base import BookingRequest

        address = order.shipping_address

        booking_request = BookingRequest(
            order_number=order.order_number,
            tracking_number="",          # courier assigns it
            recipient_name=address.full_name,
            recipient_phone=address.phone,
            address_line1=address.address_line1,
            address_line2=address.address_line2 or "",
            city=address.city,
            province=address.province,
            postal_code=address.postal_code,
            is_cod=is_cod,
            cod_amount=cod_amount,
            weight_kg=weight_kg,
            pieces=1,
            description=(
                f"Order {order.order_number} — "
                f"{order.items.count()} item(s)"
            ),
        )

        return courier_client.book_shipment(
            booking_request,
            timeout_seconds=10,
        )
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
'''
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
'''
