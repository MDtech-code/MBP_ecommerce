# apps/notifications/models.py
from __future__ import annotations
import logging

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.common.validators import phone_validator

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.notifications")




class Notification(TimeStampedModel):
    """
    Single notification record — one per message per channel.

    Design decisions:
    - user SET_NULL — notification history preserved after account deletion.
    - Delivery tracking (attempts, failures) in NotificationDeliveryAttempt.
    - is_read=None for non-IN_APP channels — null means not applicable.
    - recipient_phone/email stored directly — user may be anonymous
      for promotional broadcasts or may delete account after sending.
    - context_data holds template variables for message rendering.
    """

    class Channel(models.TextChoices):
        WHATSAPP = 'whatsapp', _('WhatsApp Business API')
        SMS      = 'sms',      _('SMS (Local Gateway)')
        EMAIL    = 'email',    _('Email')
        IN_APP   = 'in_app',   _('In-App Push / Bell Icon')

    class Type(models.TextChoices):
        COD_VERIFICATION = 'cod_verification', _('COD Order Verification')
        ORDER_PLACED     = 'order_placed',     _('Order Placed')
        ORDER_SHIPPED    = 'order_shipped',    _('Order Shipped (AWB Attached)')
        OUT_FOR_DELIVERY = 'out_for_delivery', _('Rider Out For Delivery')
        PROMOTIONAL      = 'promotional',      _('Marketing / Discount Alert')
        SYSTEM_ALERT     = 'system_alert',     _('System / Security Alert')
        ORDER_DELIVERED  = 'order_delivered',  _('Order Delivered Successfully')   # NEW
        RTO_ALERT        = 'rto_alert',        _('RTO — Parcel Returned to Warehouse')  # NEW

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name=_("recipient user"),
        help_text=_("SET_NULL — notification history preserved after deletion."),
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        verbose_name=_("related order"),
    )
    recipient_phone = models.CharField(
        _("recipient phone"),
        max_length=15,
        null=True,
        blank=True,
        help_text=_("+923XXXXXXXXX for SMS/WhatsApp channels."),
    )
    recipient_email = models.EmailField(
        _("recipient email"),
        null=True,
        blank=True,
    )
    channel = models.CharField(
        _("channel"),
        max_length=20,
        choices=Channel.choices,
    )
    notification_type = models.CharField(
        _("notification type"),
        max_length=30,
        choices=Type.choices,
    )
    title = models.CharField(
        _("title"),
        max_length=150,
    )
    body = models.TextField(
        _("body"),
    )
    context_data = models.JSONField(
        _("context data"),
        blank=True,
        null=True,
        help_text=_(
            "Template variables for message rendering. "
            "e.g. {'order_number': 'MBP-2026-000001', 'awb': 'TCS-99'}"
        ),
    )
    is_sent = models.BooleanField(
        _("is sent"),
        default=False,
        help_text=_("True after at least one successful delivery attempt."),
    )
    sent_at = models.DateTimeField(
        _("sent at"),
        null=True,
        blank=True,
    )
    is_read = models.BooleanField(
        _("is read"),
        null=True,
        blank=True,
        default=None,
        help_text=_(
            "Only applicable for IN_APP channel. "
            "Null for SMS/Email/WhatsApp — not applicable."
        ),
    )
    failure_reason = models.TextField(
        _("failure reason"),
        blank=True,
        default="",
        help_text=_("Last failure reason — full history in NotificationDeliveryAttempt."),
    )

    class Meta:
        verbose_name        = _("notification")
        verbose_name_plural = _("notifications")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["user",              "is_read"]),
            models.Index(fields=["channel",           "is_sent", "created_at"]),
            models.Index(fields=["notification_type", "is_sent", "created_at"]),
            models.Index(fields=["is_sent",           "created_at"]),
        ]

    def __str__(self) -> str:
        recipient = self.recipient_phone or self.recipient_email or "unknown"
        return f"[{self.channel}] {self.title} → {recipient}"


class NotificationDeliveryAttempt(TimeStampedModel):
    """
    Immutable record of each delivery attempt for a notification.

    One Notification can have multiple attempts (retries after failure).
    Keeps Notification model clean — delivery history lives here.
    INSERT only — save() guard prevents updates.
    """

    class Outcome(models.TextChoices):
        SUCCESS = 'success', _('Delivered Successfully')
        FAILED  = 'failed',  _('Delivery Failed')

    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='delivery_attempts',
        verbose_name=_('notification'),
    )
    outcome = models.CharField(
        _('outcome'),
        max_length=10,
        choices=Outcome.choices,
    )
    attempted_at = models.DateTimeField(
        _('attempted at'),
        auto_now_add=True,
        db_index=True,
    )
    failure_reason = models.TextField(
        _('failure reason'),
        blank=True,
        default='',
    )
    gateway_response = models.JSONField(
        _('gateway response'),
        null=True,
        blank=True,
        help_text=_('Raw response from SMS/WhatsApp/Email gateway.'),
    )

    class Meta:
        verbose_name        = _('notification delivery attempt')
        verbose_name_plural = _('notification delivery attempts')
        ordering            = ['-attempted_at']
        indexes = [
            models.Index(fields=['notification', 'attempted_at']),
            models.Index(fields=['outcome',      'attempted_at']),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValueError(
                "NotificationDeliveryAttempt records are immutable "
                "and cannot be updated."
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.get_outcome_display()} — "
            f"notification#{self.notification_id} @ {self.attempted_at}"
        )


class WhatsAppCODVerification(TimeStampedModel):
    """
    Tracks automated WhatsApp confirmation flow for COD orders.

    Prevents RTO (Return to Origin) by confirming customer intent
    before dispatching rider. Links to originating Notification
    for full audit trail.

    Status flow:
        PENDING_REPLY → CONFIRMED (customer replies YES)
        PENDING_REPLY → CANCELLED (customer replies NO/CANCEL)
        PENDING_REPLY → TIMEOUT   (no reply within window)
    """

    class Status(models.TextChoices):
        PENDING_REPLY = 'pending_reply', _('Message Sent — Awaiting Reply')
        CONFIRMED     = 'confirmed',     _('Customer Confirmed via WhatsApp')
        CANCELLED     = 'cancelled',     _('Customer Cancelled via WhatsApp')
        TIMEOUT       = 'timeout',       _('No Response — Manual Call Required')

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="whatsapp_cod_verification",
        verbose_name=_("order"),
    )
    notification = models.OneToOneField(
        Notification,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='whatsapp_verification',
        verbose_name=_('originating notification'),
        help_text=_('The Notification record that triggered this verification flow.'),
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length=15,
        validators=[phone_validator],
    )
    meta_message_id = models.CharField(
        _("Meta message ID"),
        max_length=150,
        null=True,
        blank=True,
        help_text=_("WhatsApp Cloud API message ID for delivery tracking."),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING_REPLY,
        db_index=True,
    )
    customer_reply_text = models.CharField(
        _("customer reply text"),
        max_length=100,
        blank=True,
        default="",
    )
    verified_at = models.DateTimeField(
        _("verified at"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name        = _("WhatsApp COD verification")
        verbose_name_plural = _("WhatsApp COD verifications")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["status",      "created_at"]),
            models.Index(fields=["phone_number", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"COD verification — {self.order.order_number} "
            f"({self.get_status_display()})"
        )
