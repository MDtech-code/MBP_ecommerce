from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedModel












class Notification(TimeStampedModel):
    class Channel(models.TextChoices):
        WHATSAPP = 'WHATSAPP', _('WhatsApp Business API')
        SMS = 'SMS', _('SMS (Local Gateway)')
        EMAIL = 'EMAIL', _('Email')
        IN_APP = 'IN_APP', _('In-App Push / Bell Icon')

    class Type(models.TextChoices):
        COD_VERIFICATION = 'COD_VERIFICATION', _('COD Order Verification')
        ORDER_PLACED = 'ORDER_PLACED', _('Order Placed')
        ORDER_SHIPPED = 'ORDER_SHIPPED', _('Order Shipped (AWB Attached)')
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', _('Rider Out For Delivery')
        PROMOTIONAL = 'PROMOTIONAL', _('Marketing / Discount Alert')
        SYSTEM_ALERT = 'SYSTEM_ALERT', _('System / Security Alert')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    recipient_phone = models.CharField(max_length=15, null=True, blank=True, help_text=_("+923XXXXXXXXX for SMS/WhatsApp"))
    recipient_email = models.EmailField(null=True, blank=True)
    
    channel = models.CharField(max_length=15, choices=Channel.choices)
    notification_type = models.CharField(max_length=25, choices=Type.choices)
    
    title = models.CharField(max_length=150)
    body = models.TextField()
    context_data = models.JSONField(blank=True, null=True, help_text=_("Dynamic variables e.g., {'order_id': '123', 'awb': 'TCS-99'}"))
    
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    is_read = models.BooleanField(default=False, help_text=_("For IN_APP notifications"))
    failure_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['channel', 'is_sent', 'created_at']),
        ]

    def __str__(self):
        return f"[{self.channel}] {self.title} -> {self.recipient_phone or self.recipient_email}"


class WhatsAppCODVerification(TimeStampedModel):
    """
    Tracks automated WhatsApp flows to verify COD orders and prevent RTOs.
    """
    class Status(models.TextChoices):
        PENDING_REPLY = 'PENDING_REPLY', _('Message Sent - Awaiting Reply')
        CONFIRMED = 'CONFIRMED', _('Customer Confirmed via WhatsApp')
        CANCELLED = 'CANCELLED', _('Customer Cancelled via WhatsApp')
        TIMEOUT = 'TIMEOUT', _('No Response (Manual Call Required)')

    order_id = models.CharField(max_length=100, unique=True, db_index=True)
    phone_number = models.CharField(max_length=15)
    meta_message_id = models.CharField(max_length=150, null=True, blank=True, help_text=_("WhatsApp API Message ID"))
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING_REPLY, db_index=True)
    customer_reply_text = models.CharField(max_length=100, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = _("WhatsApp COD Verification")
        verbose_name_plural = _("WhatsApp COD Verifications")