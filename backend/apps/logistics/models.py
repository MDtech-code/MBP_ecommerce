from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedModel







class CourierPartner(models.TextChoices):
    POSTEX = 'POSTEX', _('PostEx')
    TCS = 'TCS', _('TCS Courier')
    LEOPARDS = 'LEOPARDS', _('Leopards Courier')
    TRAX = 'TRAX', _('Trax Logistics')
    INSTAWORLD = 'INSTAWORLD', _('InstaWorld')
    MOVEX = 'MOVEX', _('Movex')
    SELF_DELIVERY = 'SELF_DELIVERY', _('In-House Fleet')


class Shipment(TimeStampedModel):
    class Status(models.TextChoices):
        LABEL_CREATED = 'LABEL_CREATED', _('Label Created / Booked')
        PICKED_UP = 'PICKED_UP', _('Picked Up by Courier')
        IN_TRANSIT = 'IN_TRANSIT', _('In Transit')
        OUT_FOR_DELIVERY = 'OUT_FOR_DELIVERY', _('Out for Delivery')
        DELIVERED = 'DELIVERED', _('Delivered')
        RETURN_REQUESTED = 'RETURN_REQUESTED', _('Return requested by customer/courier')
        RTO_IN_TRANSIT = 'RTO_IN_TRANSIT', _('Returned to Origin (In Transit)')
        RTO_DELIVERED = 'RTO_DELIVERED', _('Returned to Seller Warehouse')
        LOST = 'LOST', _('Lost in Transit')

    order_id = models.CharField(max_length=100, unique=True, db_index=True)
    courier = models.CharField(max_length=20, choices=CourierPartner.choices)
    tracking_number = models.CharField(max_length=100, unique=True, db_index=True, help_text=_("Airway Bill (AWB) number"))
    
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.LABEL_CREATED, db_index=True)
    
    # Financials for COD shipments
    is_cod = models.BooleanField(default=True)
    cod_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    shipping_cost_pkr = models.DecimalField(max_digits=8, decimal_places=2, help_text=_("Cost charged by courier to seller"))
    
    # Address Metadata
    destination_city = models.CharField(max_length=100, db_index=True, help_text=_("e.g., Lahore, Karachi, Rawalpindi"))
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.50'))
    
    estimated_delivery_date = models.DateField(null=True, blank=True)
    actual_delivery_date = models.DateTimeField(null=True, blank=True)
    raw_courier_response = models.JSONField(blank=True, null=True)

    class Meta:
        verbose_name = _("Shipment")
        verbose_name_plural = _("Shipments")
        indexes = [
            models.Index(fields=['courier', 'status']),
            models.Index(fields=['destination_city', 'status']),
        ]

    def __str__(self):
        return f"{self.courier} - {self.tracking_number} ({self.status})"


class CourierSettlement(TimeStampedModel):
    """
    Reconciles bank deposits from COD couriers against delivered orders.
    """
    courier = models.CharField(max_length=20, choices=CourierPartner.choices)
    settlement_reference = models.CharField(max_length=100, unique=True, help_text=_("Bank transfer ID or courier advice number"))
    total_cod_collected = models.DecimalField(max_digits=12, decimal_places=2)
    total_shipping_deducted = models.DecimalField(max_digits=10, decimal_places=2)
    net_payout_received = models.DecimalField(max_digits=12, decimal_places=2)
    payout_date = models.DateField()
    shipments_included = models.ManyToManyField(Shipment, related_name='settlements')
    is_reconciled = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Courier Settlement")
        verbose_name_plural = _("Courier Settlements")