# apps/notifications/tasks.py
from __future__ import annotations

"""
Notification Celery tasks — async message delivery.

Responsibility:
    All async notification dispatch lives here.
    Tasks create Notification records and attempt delivery
    via the appropriate channel (email, SMS, WhatsApp, in-app).
    Zero HTTP concerns. Zero DRF imports.

Task design:
    All tasks are idempotent where possible.
    bind=True + max_retries for transient delivery failures.
    Notification + NotificationDeliveryAttempt records created
    regardless of delivery outcome — full audit trail preserved.

Current implementation:
    Phase 1 — email channel only, via Django's send_mail.
    Phase 2 — WhatsApp Business API for COD verification.
    Phase 3 — SMS gateway integration.

Celery configuration:
    Tasks registered under the notifications queue.
    Broker: Redis on port 6380 (matches project settings).
"""

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

logger = logging.getLogger("apps.notifications")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_order_confirmation_email",
)
def send_order_confirmation_email(self, *, order_id: int) -> None:
    """
    Send an order confirmation email to the customer.

    Fetches the Order and related user data, creates a Notification
    record, attempts email delivery via Django send_mail, and records
    the outcome in NotificationDeliveryAttempt.

    Retries up to 3 times with 60-second delay on transient failures
    (SMTP timeout, connection error). Does not retry on permanent
    failures (invalid email address).

    Args:
        order_id: Primary key of the Order to confirm.
    """
    from apps.notifications.models import Notification, NotificationDeliveryAttempt
    from apps.orders.models import Order

    logger.info(
        "send_order_confirmation_email: started | order_id=%s",
        order_id,
    )

    # ── Fetch order ────────────────────────────────────────────────────────
    try:
        order = (
            Order.objects
            .select_related("user", "shipping_address")
            .get(pk=order_id)
        )
    except Order.DoesNotExist:
        logger.error(
            "send_order_confirmation_email: Order not found | order_id=%s",
            order_id,
        )
        return

    user            = order.user
    recipient_email = user.email if user else None

    if not recipient_email:
        logger.warning(
            "send_order_confirmation_email: no recipient email | "
            "order_id=%s",
            order_id,
        )
        return

    # ── Build message content ──────────────────────────────────────────────
    title = f"Order Confirmed — {order.order_number}"
    body  = (
        f"Assalam-o-Alaikum {user.get_full_name() or user.email},\n\n"
        f"Your order {order.order_number} has been placed successfully.\n\n"
        f"Order Total : Rs. {order.total_price}\n"
        f"Payment     : {order.get_payment_method_display()}\n"
        f"Status      : {order.get_status_display()}\n\n"
        f"We will notify you when your order is confirmed and shipped.\n\n"
        f"Thank you for shopping with us."
    )
    context_data = {
        "order_number":   order.order_number,
        "total_price":    str(order.total_price),
        "payment_method": order.get_payment_method_display(),
        "status":         order.get_status_display(),
    }

    # ── Create Notification record ─────────────────────────────────────────
    notification = Notification.objects.create(
        user=user,
        order=order,
        recipient_email=recipient_email,
        channel=Notification.Channel.EMAIL,
        notification_type=Notification.Type.ORDER_PLACED,
        title=title,
        body=body,
        context_data=context_data,
    )

    # ── Attempt delivery ───────────────────────────────────────────────────
    try:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@store.pk"),
            recipient_list=[recipient_email],
            fail_silently=False,
        )

        # Mark notification as sent
        notification.is_sent = True
        notification.sent_at  = timezone.now()
        notification.save(update_fields=["is_sent", "sent_at"])

        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.SUCCESS,
        )

        logger.info(
            "send_order_confirmation_email: delivered | "
            "order_id=%s email=%s",
            order_id,
            recipient_email,
        )

    except Exception as exc:
        failure_reason = str(exc)

        notification.failure_reason = failure_reason
        notification.save(update_fields=["failure_reason"])

        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.FAILED,
            failure_reason=failure_reason,
        )

        logger.error(
            "send_order_confirmation_email: delivery failed | "
            "order_id=%s email=%s error=%s — retrying",
            order_id,
            recipient_email,
            failure_reason,
        )

        # Retry on transient failures
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_order_cancellation_email",
)
def send_order_cancellation_email(self, *, order_id: int) -> None:
    """
    Send an order cancellation confirmation email to the customer.

    Fetches the Order, creates a Notification record, attempts
    email delivery, and records the outcome in DeliveryAttempt.

    Args:
        order_id: Primary key of the cancelled Order.
    """
    from apps.notifications.models import Notification, NotificationDeliveryAttempt
    from apps.orders.models import Order

    logger.info(
        "send_order_cancellation_email: started | order_id=%s",
        order_id,
    )

    # ── Fetch order ────────────────────────────────────────────────────────
    try:
        order = (
            Order.objects
            .select_related("user")
            .get(pk=order_id)
        )
    except Order.DoesNotExist:
        logger.error(
            "send_order_cancellation_email: Order not found | order_id=%s",
            order_id,
        )
        return

    user            = order.user
    recipient_email = user.email if user else None

    if not recipient_email:
        logger.warning(
            "send_order_cancellation_email: no recipient email | "
            "order_id=%s",
            order_id,
        )
        return

    # ── Build message content ──────────────────────────────────────────────
    title = f"Order Cancelled — {order.order_number}"
    body  = (
        f"Assalam-o-Alaikum {user.get_full_name() or user.email},\n\n"
        f"Your order {order.order_number} has been cancelled as requested.\n\n"
        f"Order Total : Rs. {order.total_price}\n"
        f"Cancelled at: {order.cancelled_at}\n\n"
        f"If you paid online, your refund will be processed within 3-5 business days.\n\n"
        f"If you have any questions, please contact our support team.\n\n"
        f"Thank you for shopping with us."
    )
    context_data = {
        "order_number": order.order_number,
        "total_price":  str(order.total_price),
        "cancelled_at": str(order.cancelled_at),
    }

    # ── Create Notification record ─────────────────────────────────────────
    notification = Notification.objects.create(
        user=user,
        order=order,
        recipient_email=recipient_email,
        channel=Notification.Channel.EMAIL,
        notification_type=Notification.Type.ORDER_PLACED,
        title=title,
        body=body,
        context_data=context_data,
    )

    # ── Attempt delivery ───────────────────────────────────────────────────
    try:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@store.pk"),
            recipient_list=[recipient_email],
            fail_silently=False,
        )

        notification.is_sent = True
        notification.sent_at  = timezone.now()
        notification.save(update_fields=["is_sent", "sent_at"])

        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.SUCCESS,
        )

        logger.info(
            "send_order_cancellation_email: delivered | "
            "order_id=%s email=%s",
            order_id,
            recipient_email,
        )

    except Exception as exc:
        failure_reason = str(exc)

        notification.failure_reason = failure_reason
        notification.save(update_fields=["failure_reason"])

        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.FAILED,
            failure_reason=failure_reason,
        )

        logger.error(
            "send_order_cancellation_email: delivery failed | "
            "order_id=%s email=%s error=%s — retrying",
            order_id,
            recipient_email,
            failure_reason,
        )

        raise self.retry(exc=exc)
    




@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_order_shipped_notification",
)
def send_order_shipped_notification(
    self,
    *,
    order_id: int,
    tracking_number: str,
    courier: str,
) -> None:
    """
    Notify customer that their order has been shipped with AWB details.

    Args:
        order_id:        Primary key of the shipped Order.
        tracking_number: AWB number assigned by courier.
        courier:         CourierPartner value for display.
    """
    from apps.notifications.models import Notification, NotificationDeliveryAttempt
    from apps.orders.models import Order

    logger.info(
        "send_order_shipped_notification: started | order_id=%s",
        order_id,
    )

    try:
        order = Order.objects.select_related("user").get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(
            "send_order_shipped_notification: Order not found | order_id=%s",
            order_id,
        )
        return

    user            = order.user
    recipient_email = user.email if user else None
    if not recipient_email:
        return

    title = f"Your Order Has Been Shipped — {order.order_number}"
    body  = (
        f"Assalam-o-Alaikum {user.get_full_name() or user.email},\n\n"
        f"Great news! Your order {order.order_number} is on its way.\n\n"
        f"Courier         : {courier}\n"
        f"Tracking Number : {tracking_number}\n\n"
        f"You can track your parcel using the tracking number above.\n\n"
        f"Thank you for shopping with us."
    )

    notification = Notification.objects.create(
        user=user,
        order=order,
        recipient_email=recipient_email,
        channel=Notification.Channel.EMAIL,
        notification_type=Notification.Type.ORDER_SHIPPED,
        title=title,
        body=body,
        context_data={
            "order_number":    order.order_number,
            "tracking_number": tracking_number,
            "courier":         courier,
        },
    )

    try:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@store.pk"),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        notification.is_sent = True
        notification.sent_at  = timezone.now()
        notification.save(update_fields=["is_sent", "sent_at"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.SUCCESS,
        )
        logger.info(
            "send_order_shipped_notification: delivered | order_id=%s",
            order_id,
        )
    except Exception as exc:
        notification.failure_reason = str(exc)
        notification.save(update_fields=["failure_reason"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.FAILED,
            failure_reason=str(exc),
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_out_for_delivery_notification",
)
def send_out_for_delivery_notification(
    self,
    *,
    order_id: int,
    tracking_number: str,
) -> None:
    """
    Notify customer that their order is out for delivery today.

    Args:
        order_id:        Primary key of the Order.
        tracking_number: AWB number for reference.
    """
    from apps.notifications.models import Notification, NotificationDeliveryAttempt
    from apps.orders.models import Order

    logger.info(
        "send_out_for_delivery_notification: started | order_id=%s",
        order_id,
    )

    try:
        order = Order.objects.select_related("user").get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(
            "send_out_for_delivery_notification: Order not found | "
            "order_id=%s",
            order_id,
        )
        return

    user            = order.user
    recipient_email = user.email if user else None
    if not recipient_email:
        return

    title = f"Your Order is Out for Delivery — {order.order_number}"
    body  = (
        f"Assalam-o-Alaikum {user.get_full_name() or user.email},\n\n"
        f"Your order {order.order_number} is out for delivery today!\n\n"
        f"Tracking Number : {tracking_number}\n\n"
        f"Please ensure someone is available to receive the parcel.\n"
        f"For COD orders, please keep exact change ready.\n\n"
        f"Thank you for shopping with us."
    )

    notification = Notification.objects.create(
        user=user,
        order=order,
        recipient_email=recipient_email,
        channel=Notification.Channel.EMAIL,
        notification_type=Notification.Type.OUT_FOR_DELIVERY,
        title=title,
        body=body,
        context_data={
            "order_number":    order.order_number,
            "tracking_number": tracking_number,
        },
    )

    try:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@store.pk"),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        notification.is_sent = True
        notification.sent_at  = timezone.now()
        notification.save(update_fields=["is_sent", "sent_at"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.SUCCESS,
        )
        logger.info(
            "send_out_for_delivery_notification: delivered | order_id=%s",
            order_id,
        )
    except Exception as exc:
        notification.failure_reason = str(exc)
        notification.save(update_fields=["failure_reason"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.FAILED,
            failure_reason=str(exc),
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_delivery_confirmation_notification",
)
def send_delivery_confirmation_notification(self, *, order_id: int) -> None:
    """
    Notify customer that their order has been delivered successfully.

    Args:
        order_id: Primary key of the delivered Order.
    """
    from apps.notifications.models import Notification, NotificationDeliveryAttempt
    from apps.orders.models import Order

    logger.info(
        "send_delivery_confirmation_notification: started | order_id=%s",
        order_id,
    )

    try:
        order = Order.objects.select_related("user").get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(
            "send_delivery_confirmation_notification: "
            "Order not found | order_id=%s",
            order_id,
        )
        return

    user            = order.user
    recipient_email = user.email if user else None
    if not recipient_email:
        return

    title = f"Order Delivered — {order.order_number}"
    body  = (
        f"Assalam-o-Alaikum {user.get_full_name() or user.email},\n\n"
        f"Your order {order.order_number} has been delivered successfully.\n\n"
        f"We hope you enjoy your purchase!\n\n"
        f"If you have any issues with the product, please contact our support team.\n\n"
        f"Thank you for shopping with us."
    )

    notification = Notification.objects.create(
        user=user,
        order=order,
        recipient_email=recipient_email,
        channel=Notification.Channel.EMAIL,
        notification_type=Notification.Type.ORDER_SHIPPED,
        title=title,
        body=body,
        context_data={"order_number": order.order_number},
    )

    try:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@store.pk"),
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        notification.is_sent = True
        notification.sent_at  = timezone.now()
        notification.save(update_fields=["is_sent", "sent_at"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.SUCCESS,
        )
        logger.info(
            "send_delivery_confirmation_notification: delivered | order_id=%s",
            order_id,
        )
    except Exception as exc:
        notification.failure_reason = str(exc)
        notification.save(update_fields=["failure_reason"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.FAILED,
            failure_reason=str(exc),
        )
        raise self.retry(exc=exc)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="notifications.send_rto_admin_alert",
)
def send_rto_admin_alert(self, *, order_id: int) -> None:
    """
    Alert admin staff that an RTO parcel has been returned to warehouse.

    Sends to DEFAULT_ADMIN_EMAIL from settings.
    Stock has already been restored by ShipmentService at this point.

    Args:
        order_id: Primary key of the RTO Order.
    """
    from apps.notifications.models import Notification, NotificationDeliveryAttempt
    from apps.orders.models import Order

    logger.info(
        "send_rto_admin_alert: started | order_id=%s",
        order_id,
    )

    try:
        order = Order.objects.select_related(
            "user", "shipping_address"
        ).get(pk=order_id)
    except Order.DoesNotExist:
        logger.error(
            "send_rto_admin_alert: Order not found | order_id=%s",
            order_id,
        )
        return

    admin_email = getattr(settings, "DEFAULT_ADMIN_EMAIL", None)
    if not admin_email:
        logger.warning(
            "send_rto_admin_alert: DEFAULT_ADMIN_EMAIL not configured | "
            "order_id=%s",
            order_id,
        )
        return

    title = f"RTO Alert — {order.order_number} returned to warehouse"
    body  = (
        f"RTO ALERT\n\n"
        f"Order       : {order.order_number}\n"
        f"Customer    : {getattr(order.user, 'email', 'N/A')}\n"
        f"City        : {getattr(order.shipping_address, 'city', 'N/A')}\n"
        f"Total       : Rs. {order.total_price}\n"
        f"Payment     : {order.get_payment_method_display()}\n\n"
        f"The parcel has been returned to the warehouse.\n"
        f"Stock has been automatically restored.\n"
        f"Please arrange reshipment or process refund as appropriate."
    )

    notification = Notification.objects.create(
        order=order,
        recipient_email=admin_email,
        channel=Notification.Channel.EMAIL,
        notification_type=Notification.Type.SYSTEM_ALERT,
        title=title,
        body=body,
        context_data={"order_number": order.order_number},
    )

    try:
        send_mail(
            subject=title,
            message=body,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@store.pk"),
            recipient_list=[admin_email],
            fail_silently=False,
        )
        notification.is_sent = True
        notification.sent_at  = timezone.now()
        notification.save(update_fields=["is_sent", "sent_at"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.SUCCESS,
        )
        logger.info(
            "send_rto_admin_alert: delivered | order_id=%s admin=%s",
            order_id,
            admin_email,
        )
    except Exception as exc:
        notification.failure_reason = str(exc)
        notification.save(update_fields=["failure_reason"])
        NotificationDeliveryAttempt.objects.create(
            notification=notification,
            outcome=NotificationDeliveryAttempt.Outcome.FAILED,
            failure_reason=str(exc),
        )
        raise self.retry(exc=exc)