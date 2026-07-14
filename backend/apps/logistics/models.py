# apps/logistics/models.py
from __future__ import annotations
from decimal import Decimal
import logging

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.logistics")


class CourierPartner(models.TextChoices):
    POSTEX        = 'postex',        _('PostEx')
    TCS           = 'tcs',           _('TCS Courier')
    LEOPARDS      = 'leopards',      _('Leopards Courier')
    TRAX          = 'trax',          _('Trax Logistics')
    INSTAWORLD    = 'instaworld',    _('InstaWorld')
    MOVEX         = 'movex',         _('Movex')
    SELF_DELIVERY = 'self_delivery', _('In-House Fleet')


class Shipment(TimeStampedModel):
    """
    Physical dispatch record for an order.

    Design decisions:
    - order OneToOne — one order has exactly one active shipment.
    - Status transitions logged in ShipmentStatusLog — full audit trail.
    - destination_city denormalized from OrderShippingAddress for
      courier API calls — set once at creation, never updated.
    - raw_courier_response preserved for debugging API issues.
    - PROTECT on order — shipment is physical record, never cascade delete.
    """

    class Status(models.TextChoices):
        LABEL_CREATED    = 'label_created',    _('Label Created / Booked')
        PICKED_UP        = 'picked_up',        _('Picked Up by Courier')
        IN_TRANSIT       = 'in_transit',       _('In Transit')
        OUT_FOR_DELIVERY = 'out_for_delivery', _('Out for Delivery')
        DELIVERED        = 'delivered',        _('Delivered')
        RETURN_REQUESTED = 'return_requested', _('Return Requested')
        RTO_IN_TRANSIT   = 'rto_in_transit',   _('Returned to Origin (In Transit)')
        RTO_DELIVERED    = 'rto_delivered',    _('Returned to Seller Warehouse')
        LOST             = 'lost',             _('Lost in Transit')
    class ShipmentType(models.TextChoices):
        ORIGINAL = 'original', _('Original Dispatch')
        RESHIPMENT = 'reshipment', _('Replacement / Reshipment')
        RETURN = 'return', _('Reverse Return Pickup')

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="shipments",
        verbose_name=_("order"),
    )
    shipment_type = models.CharField(
        _("shipment type"),
        max_length=15,
        choices=ShipmentType.choices,
        default=ShipmentType.ORIGINAL,
    )
    courier = models.CharField(
        _("courier partner"),
        max_length=20,
        choices=CourierPartner.choices,
    )
    tracking_number = models.CharField(
        _("tracking number (AWB)"),
        max_length=100,
        unique=True,
        db_index=True,
        help_text=_("Airway Bill number assigned by courier."),
    )
    status = models.CharField(
        _("status"),
        max_length=30,
        choices=Status.choices,
        default=Status.LABEL_CREATED,
        db_index=True,
    )
    is_cod = models.BooleanField(
        _("is COD"),
        default=True,
    )
    cod_amount = models.DecimalField(
        _("COD amount (PKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Amount courier collects from customer on delivery."),
    )
    shipping_cost_pkr = models.DecimalField(
        _("shipping cost (PKR)"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Cost charged by courier to seller."),
    )
    destination_city = models.CharField(
        _("destination city"),
        max_length=100,
        db_index=True,
        help_text=_(
            "Denormalized from OrderShippingAddress for courier API routing. "
            "Set at shipment creation — never updated after."
        ),
    )
    weight_kg = models.DecimalField(
        _("weight (kg)"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.50"),
    )
    estimated_delivery_date = models.DateField(
        _("estimated delivery date"),
        null=True,
        blank=True,
    )
    actual_delivery_date = models.DateTimeField(
        _("actual delivery date"),
        null=True,
        blank=True,
    )
    raw_courier_response = models.JSONField(
        _("raw courier response"),
        blank=True,
        null=True,
        help_text=_("Raw API response from courier at label creation."),
    )

    class Meta:
        verbose_name        = _("shipment")
        verbose_name_plural = _("shipments")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["courier",          "status"]),
            models.Index(fields=["destination_city", "status"]),
            models.Index(fields=["status",           "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_courier_display()} — "
            f"{self.tracking_number} ({self.get_status_display()})"
        )


class ShipmentStatusLog(models.Model):
    """
    Immutable audit trail of every shipment status change.
    Mirrors OrderStatusLog pattern — INSERT only.
    """

    class Source(models.TextChoices):
        WEBHOOK = 'webhook', _('Courier Webhook')
        MANUAL  = 'manual',  _('Manual Admin Update')
        SYSTEM  = 'system',  _('System Automated')

    shipment = models.ForeignKey(
        Shipment,
        on_delete=models.CASCADE,
        related_name='status_logs',
        verbose_name=_('shipment'),
    )
    from_status = models.CharField(_('previous status'), max_length=30)
    to_status   = models.CharField(_('new status'),      max_length=30)
    source = models.CharField(
        _('update source'),
        max_length=10,
        choices=Source.choices,
        default=Source.WEBHOOK,
    )
    raw_webhook_data = models.JSONField(
        _('raw webhook data'),
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(
        _('logged at'),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name        = _('shipment status log')
        verbose_name_plural = _('shipment status logs')
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['shipment', 'created_at']),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValueError(
                "ShipmentStatusLog records are immutable and cannot be updated."
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.shipment.tracking_number}: "
            f"{self.from_status} → {self.to_status}"
        )


class CourierSettlement(TimeStampedModel):
    """
    Reconciles COD bank deposits from couriers against delivered orders.
    Finance team marks is_reconciled after verifying bank statement.
    """

    courier = models.CharField(
        _("courier partner"),
        max_length=20,
        choices=CourierPartner.choices,
    )
    settlement_reference = models.CharField(
        _("settlement reference"),
        max_length=100,
        unique=True,
        help_text=_("Bank transfer ID or courier remittance advice number."),
    )
    total_cod_collected = models.DecimalField(
        _("total COD collected (PKR)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    total_shipping_deducted = models.DecimalField(
        _("total shipping deducted (PKR)"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    net_payout_received = models.DecimalField(
        _("net payout received (PKR)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    payout_date = models.DateField(_("payout date"))
    shipments_included = models.ManyToManyField(
        Shipment,
        related_name='settlements',
        verbose_name=_("shipments included"),
    )
    is_reconciled = models.BooleanField(
        _("is reconciled"),
        default=False,
        help_text=_("True after finance team verifies against bank statement."),
    )

    class Meta:
        verbose_name        = _("courier settlement")
        verbose_name_plural = _("courier settlements")
        ordering            = ["-payout_date"]
        indexes = [
            models.Index(fields=["courier",       "payout_date"]),
            models.Index(fields=["is_reconciled", "payout_date"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_courier_display()} settlement — "
            f"{self.payout_date} (Rs. {self.net_payout_received})"
        )
