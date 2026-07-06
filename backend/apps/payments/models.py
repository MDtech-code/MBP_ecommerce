from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedModel


class PaymentTransaction(TimeStampedModel):
    class Gateway(models.TextChoices):
        COD = 'COD', _('Cash on Delivery')
        SAFEPAY = 'SAFEPAY', _('Safepay')
        PAYFAST = 'PAYFAST', _('PayFast')
        JAZZCASH = 'JAZZCASH', _('JazzCash Mobile Wallet / Card')
        EASYPAISA = 'EASYPAISA', _('Easypaisa')
        RAAST = 'RAAST', _('Raast Instant Transfer')
        XPAY = 'XPAY', _('XPay by PostEx')

    class Status(models.TextChoices):
        PENDING = 'PENDING', _('Pending')
        AUTHORIZED = 'AUTHORIZED', _('Authorized')
        SUCCESS = 'SUCCESS', _('Success')
        FAILED = 'FAILED', _('Failed')
        REFUNDED = 'REFUNDED', _('Refunded')
        PARTIALLY_REFUNDED = 'PARTIALLY_REFUNDED', _('Partially Refunded')

    order_id = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    gateway = models.CharField(max_length=20, choices=Gateway.choices, default=Gateway.COD)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    
    amount_pkr = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    transaction_reference = models.CharField(max_length=150, unique=True, null=True, blank=True, help_text=_("Gateway transaction ID"))
    idempotency_key = models.UUIDField(unique=True, null=True, blank=True, help_text=_("Prevents double-charging"))
    
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Payment Transaction")
        verbose_name_plural = _("Payment Transactions")
        indexes = [
            models.Index(fields=['order_id', 'status']),
            models.Index(fields=['gateway', 'status']),
        ]

    def __str__(self):
        return f"{self.gateway} - {self.amount_pkr} PKR ({self.status})"


class WebhookLog(TimeStampedModel):
    """
    Immutable audit log for all incoming payment/courier webhook payloads.
    Crucial for debugging payment failures or fake callbacks.
    """
    gateway = models.CharField(max_length=50, db_index=True)
    payload = models.JSONField(help_text=_("Raw JSON payload from gateway"))
    headers = models.JSONField(help_text=_("HTTP request headers for signature verification"))
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_verified = models.BooleanField(default=False, help_text=_("Did cryptographic HMAC signature match?"))
    processed_successfully = models.BooleanField(default=False)
    exception_trace = models.TextField(blank=True)

    class Meta:
        verbose_name = _("Webhook Log")
        verbose_name_plural = _("Webhook Logs")
        ordering = ['-created_at']