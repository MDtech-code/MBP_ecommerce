from __future__ import annotations

import decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator

from apps.common.models import TimeStampedModel
from apps.products.models import Product


class Order(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        CONFIRMED = "confirmed", _("Confirmed")
        PROCESSING = "processing", _("Processing")
        SHIPPED = "shipped", _("Shipped")
        DELIVERED = "delivered", _("Delivered")
        CANCELLED = "cancelled", _("Cancelled")
        REFUNDED = "refunded", _("Refunded")

    class PaymentMethod(models.TextChoices):
        COD = "cash_on_delivery", _("Cash on Delivery")
        BANK_TRANSFER = "bank_transfer", _("Bank Transfer")

    class PaymentStatus(models.TextChoices):
        PENDING = "pending", _("Pending")
        PAID = "paid", _("Paid")
        FAILED = "failed", _("Failed")
        REFUNDED = "refunded", _("Refunded")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("customer"),
    )
    order_number = models.CharField(_("order number"), max_length=20, unique=True, db_index=True)
    status = models.CharField(_("order status"), max_length=20, choices=Status.choices, default=Status.PENDING)
    payment_method = models.CharField(_("payment method"), max_length=20, choices=PaymentMethod.choices)
    payment_status = models.CharField(_("payment status"), max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    
    # Financial breakdowns
    subtotal = models.DecimalField(_("subtotal"), max_digits=10, decimal_places=2)
    shipping_fee = models.DecimalField(_("shipping fee"), max_digits=10, decimal_places=2, default=0)
    total_price = models.DecimalField(_("total price"), max_digits=10, decimal_places=2)

    # Shipping Address Snapshots
    shipping_full_name = models.CharField(_("full name"), max_length=255)
    shipping_phone = models.CharField(_("phone number"), max_length=15)
    shipping_address_line1 = models.CharField(_("address line 1"), max_length=255)
    shipping_address_line2 = models.CharField(_("address line 2"), max_length=255, blank=True, default="")
    shipping_city = models.CharField(_("city"), max_length=100)
    shipping_province = models.CharField(_("province"), max_length=2)
    shipping_postal_code = models.CharField(_("postal code"), max_length=10)
    notes = models.TextField(_("customer delivery notes"), blank=True, default="")

    # Performance Timestamps
    placed_at = models.DateTimeField(_("placed at"), auto_now_add=True)
    confirmed_at = models.DateTimeField(_("confirmed at"), null=True, blank=True)
    shipped_at = models.DateTimeField(_("shipped at"), null=True, blank=True)
    delivered_at = models.DateTimeField(_("delivered at"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"), null=True, blank=True)

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ["-placed_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["placed_at"]),
        ]

    def __str__(self) -> str:
        return self.order_number


class OrderItem(TimeStampedModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("order"))
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="order_items", verbose_name=_("product"))
    
    # Snapshots to protect data against pricing shifts/deleted goods
    product_name = models.CharField(_("product name snapshot"), max_length=255)
    product_sku = models.CharField(_("SKU snapshot"), max_length=50)
    unit_price = models.DecimalField(_("unit price snapshot"), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_("quantity"))
    subtotal = models.DecimalField(_("subtotal"), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("order item")
        verbose_name_plural = _("order items")

    def __str__(self) -> str:
        return f"{self.quantity}x {self.product_name} ({self.order.order_number})"


class OrderStatusLog(models.Model):
    """Immutable historic trace tracking internal state transitions for audits."""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="status_logs", verbose_name=_("order"))
    from_status = models.CharField(_("previous status"), max_length=20)
    to_status = models.CharField(_("new status"), max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("changed by"),
    )
    note = models.TextField(_("internal trace notes"), blank=True, default="")
    created_at = models.DateTimeField(_("logged at"), auto_now_add=True)

    class Meta:
        verbose_name = _("order status log")
        verbose_name_plural = _("order status logs")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.order.order_number}: {self.from_status} -> {self.to_status}"