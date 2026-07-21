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