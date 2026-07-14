# apps/orders/models.py
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from apps.common.validators import phone_validator
from apps.products.models import Product

logger = logging.getLogger("apps.orders")


def _generate_order_number() -> str:
    date_str = timezone.now().strftime("%Y%m%d")
    unique = uuid.uuid4().hex[:8].upper()  # 16^8 = 4.3 billion — negligible risk
    return f"ORD-{date_str}-{unique}"


class Order(TimeStampedModel):
    """
    Confirmed customer purchase — frozen financial snapshot.

    CORE PRINCIPLE:
        Everything on an Order is a snapshot of values at placement time.
        Product prices change → Order prices do not.
        User changes address → OrderShippingAddress does not.
        Coupon is deleted → coupon_code_snapshot preserves the code.

    Status machine:
        Never set self.status directly.
        Always call self.transition_to(new_status) to ensure:
        - Transition validity is checked
        - Timestamps are auto-set
        - Audit log entry is created
    """

    class Status(models.TextChoices):
        PENDING    = "pending",    _("Pending")
        CONFIRMED  = "confirmed",  _("Confirmed")
        PROCESSING = "processing", _("Processing")
        SHIPPED    = "shipped",    _("Shipped")
        DELIVERED  = "delivered",  _("Delivered")
        CANCELLED  = "cancelled",  _("Cancelled")
        REFUNDED   = "refunded",   _("Refunded")

    class PaymentMethod(models.TextChoices):
        COD           = "cod",           _("Cash on Delivery")
        ONLINE        = "online",        _("Online Payment")
        BANK_TRANSFER = "bank_transfer", _("Bank Transfer")

    # Valid status transitions — adjacency list for the state machine
    VALID_TRANSITIONS: dict[str, list[str]] = {
        Status.PENDING:    [Status.CONFIRMED,  Status.CANCELLED],
        Status.CONFIRMED:  [Status.PROCESSING, Status.CANCELLED],
        Status.PROCESSING: [Status.SHIPPED,    Status.CANCELLED],
        Status.SHIPPED:    [Status.DELIVERED],
        Status.DELIVERED:  [Status.REFUNDED],
        Status.CANCELLED:  [],
        Status.REFUNDED:   [],
    }

    # ─── Core ─────────────────────────────────────────────────────────────────

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("customer"),
        help_text=_(
            "PROTECT — financial records must survive user deactivation."
        ),
    )
    order_number = models.CharField(
        _("order number"),
        max_length=30,
        unique=True,
        db_index=True,
        default=_generate_order_number,
    )
    status = models.CharField(
        _("order status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    payment_method = models.CharField(
        _("payment method"),
        max_length=20,
        choices=PaymentMethod.choices,
    )
    notes = models.TextField(
        _("customer delivery notes"),
        blank=True,
        default="",
    )

    # ─── Financial Snapshot ───────────────────────────────────────────────────

    subtotal = models.DecimalField(
        _("subtotal"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Sum of all OrderItem subtotals before discount."),
    )
    shipping_fee = models.DecimalField(
        _("shipping fee"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    discount_amount = models.DecimalField(
        _("discount amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total coupon discount applied — PKR amount."),
    )
    tax_amount = models.DecimalField(
        _("total tax amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Sum of all OrderItem tax amounts."),
    )
    total_price = models.DecimalField(
        _("total price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("subtotal - discount_amount + shipping_fee + tax_amount"),
    )

    # ─── Coupon Snapshot ──────────────────────────────────────────────────────

    coupon = models.ForeignKey(
        "coupons.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("coupon applied"),
    )
    coupon_code_snapshot = models.CharField(
        _("coupon code snapshot"),
        max_length=50,
        blank=True,
        default="",
        help_text=_(
            "Coupon code at time of order — preserved even if "
            "coupon is later deleted. Used on invoice and order history."
        ),
    )

    # ─── Status Timestamps ────────────────────────────────────────────────────

    placed_at    = models.DateTimeField(_("placed at"),             auto_now_add=True)
    confirmed_at = models.DateTimeField(_("confirmed at"),          null=True, blank=True)
    processed_at = models.DateTimeField(_("processing started at"), null=True, blank=True)
    shipped_at   = models.DateTimeField(_("shipped at"),            null=True, blank=True)
    delivered_at = models.DateTimeField(_("delivered at"),          null=True, blank=True)
    cancelled_at = models.DateTimeField(_("cancelled at"),          null=True, blank=True)
    refunded_at  = models.DateTimeField(_("refunded at"),           null=True, blank=True)

    class Meta:
        verbose_name        = _("order")
        verbose_name_plural = _("orders")
        ordering            = ["-placed_at"]
        indexes = [
            models.Index(fields=["user",   "status"]),
            models.Index(fields=["status", "placed_at"]),
            models.Index(fields=["payment_method", "status"]),
        ]

    def __str__(self) -> str:
        return self.order_number

    # ─── Status Machine ───────────────────────────────────────────────────────

    def can_transition_to(self, new_status: str) -> bool:
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def transition_to(
        self,
        new_status: str,
        changed_by=None,
        note: str = "",
    ) -> None:
        """
        The ONLY correct way to change order status.

        Teaching note: Never do order.status = "shipped" directly.
        That bypasses:
        - Transition validation (could ship a cancelled order)
        - Timestamp auto-setting (shipped_at stays None)
        - Audit log creation (no record of who shipped it and when)

        All three of those are compliance and financial audit requirements.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Cannot transition '{self.order_number}' "
                f"from '{self.status}' to '{new_status}'."
            )

        old_status = self.status

        timestamp_map = {
            self.Status.CONFIRMED:  "confirmed_at",
            self.Status.PROCESSING: "processed_at",
            self.Status.SHIPPED:    "shipped_at",
            self.Status.DELIVERED:  "delivered_at",
            self.Status.CANCELLED:  "cancelled_at",
            self.Status.REFUNDED:   "refunded_at",
        }

        self.status = new_status
        fields_to_update = ["status"]

        if new_status in timestamp_map:
            field = timestamp_map[new_status]
            setattr(self, field, timezone.now())
            fields_to_update.append(field)

        self.save(update_fields=fields_to_update)

        OrderStatusLog.objects.create(
            order=self,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            note=note,
        )

        logger.info(
            "Order %s: %s → %s (by %s)",
            self.order_number,
            old_status,
            new_status,
            getattr(changed_by, "email", "system"),
        )

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def payment_status(self) -> str:
        """
        Single source of truth — always reads from PaymentTransaction.
        Returns 'PENDING' if no transaction exists yet.
        No data duplication between Order and PaymentTransaction.
        """
        latest = self.payment_transactions.order_by("-created_at").first()
        return latest.status if latest else "PENDING"

    @property
    def is_cancellable(self) -> bool:
        """Customer can only cancel PENDING orders."""
        return self.status == self.Status.PENDING

    @property
    def is_terminal(self) -> bool:
        """Terminal orders cannot transition further."""
        return self.status in (self.Status.CANCELLED, self.Status.REFUNDED)


class OrderShippingAddress(TimeStampedModel):
    """
    Immutable snapshot of delivery address at order placement time.

    Why separate from Order:
        Keeps Order model clean and focused on financial data.
        Address fields can evolve independently.
        Makes it trivially easy to add multi-address per order later.

    Why immutable:
        If user changes their UserAddress after ordering,
        the shipment must go to the original address.
        Mutating this would reroute packages in transit.
    """

    order = models.OneToOneField(
        Order,
        on_delete=models.CASCADE,
        related_name="shipping_address",
        verbose_name=_("order"),
    )
    full_name     = models.CharField(_("full name"),    max_length=255)
    phone         = models.CharField(
        _("phone number"),
        max_length=15,
        validators=[phone_validator],
    )
    address_line1 = models.CharField(_("address line 1"), max_length=255)
    address_line2 = models.CharField(
        _("address line 2"),
        max_length=255,
        blank=True,
        default="",
    )
    city          = models.CharField(_("city"),         max_length=100)
    province      = models.CharField(_("province"),     max_length=2)
    postal_code   = models.CharField(_("postal code"),  max_length=10)
    country       = models.CharField(
        _("country"),
        max_length=100,
        default="Pakistan",
        editable=False,
    )

    class Meta:
        verbose_name        = _("order shipping address")
        verbose_name_plural = _("order shipping addresses")

    def __str__(self) -> str:
        return f"{self.full_name} — {self.address_line1}, {self.city}"

    @property
    def full_address(self) -> str:
        parts = filter(None, [
            self.address_line1,
            self.address_line2,
            self.city,
            self.province,
            self.postal_code,
            self.country,
        ])
        return ", ".join(parts)

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValueError(
                "OrderShippingAddress is immutable after creation. "
                "It is a snapshot of the address at order placement time."
            )
        super().save(*args, **kwargs)


class OrderItem(TimeStampedModel):
    """
    Single product line within a confirmed order.

    All price fields are SNAPSHOTS taken at order placement time.
    Product price changes, discounts being removed, products being
    deleted — none of these must affect past order history or invoices.

    Calculated fields (subtotal, discount_amount, tax_amount) are
    auto-derived in save() from their source fields to ensure
    internal consistency. Callers must not set these manually.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("order"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name=_("product"),
        help_text=_(
            "PROTECT — product cannot be deleted while referenced "
            "in order history."
        ),
    )

    # ─── Snapshots (immutable after creation) ────────────────────────────────
    product_name   = models.CharField(_("product name"), max_length=255)
    product_sku    = models.CharField(_("SKU"),          max_length=50)
    original_price = models.DecimalField(
        _("original price"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Product.price at order time — before any discount."),
    )
    unit_price = models.DecimalField(
        _("unit price paid"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Product.current_price at order time — after product discount."),
    )
    quantity = models.PositiveIntegerField(_("quantity"))

    # ─── Calculated on save() — do not set manually ───────────────────────────
    subtotal = models.DecimalField(
        _("subtotal"),
        max_digits=10,
        decimal_places=2,
        help_text=_("unit_price × quantity — auto-calculated."),
    )
    discount_amount = models.DecimalField(
        _("item discount amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_(
            "(original_price - unit_price) × quantity. "
            "Shows customer their per-item saving on invoice."
        ),
    )
    tax_rate_percentage = models.DecimalField(
        _("tax rate (%)"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("GST/tax rate snapshotted at order time."),
    )
    tax_amount = models.DecimalField(
        _("tax amount (PKR)"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("subtotal × tax_rate / 100 — auto-calculated."),
    )

    class Meta:
        verbose_name        = _("order item")
        verbose_name_plural = _("order items")
        ordering            = ["created_at"]
        indexes = [
            # Sales analytics: "top selling products this month"
            models.Index(fields=["product", "created_at"]),
            # Order detail: all items for an order
            models.Index(fields=["order",   "product"]),
        ]

    def __str__(self) -> str:
        return f"{self.quantity}× {self.product_name} ({self.order.order_number})"

    def save(self, *args, **kwargs) -> None:
        update_fields = kwargs.get("update_fields")
        # Recalculate if: new record OR source fields are being updated
        source_fields = {"unit_price", "quantity", "original_price", 
                         "tax_rate_percentage"}
        should_recalculate = (
            not self.pk  # New record
            or update_fields is None  # Full save
            or bool(source_fields.intersection(set(update_fields)))
        )
        if should_recalculate:
            self.subtotal = (
                self.unit_price * self.quantity
            ).quantize(Decimal("0.01"))
            self.discount_amount = (
                (self.original_price - self.unit_price) * self.quantity
            ).quantize(Decimal("0.01"))
            self.tax_amount = (
                self.subtotal * self.tax_rate_percentage / Decimal("100")
            ).quantize(Decimal("0.01"))   
            # If update_fields specified, add calculated fields to it
            if update_fields is not None:
                kwargs["update_fields"] = list(update_fields) + [
                    "subtotal", "discount_amount", "tax_amount"
                ]
        super().save(*args, **kwargs)


class OrderStatusLog(models.Model):
    """
    Immutable append-only audit trail of every order status transition.

    Why 2-year retention (not 90 days like login activity):
        FBR tax compliance in Pakistan requires financial records
        to be retained for a minimum of 6 years.
        Order status history is a financial compliance record.
        Never auto-purge this table.

    INSERT only — save() guard prevents any update.
    """

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("order"),
    )
    from_status = models.CharField(_("previous status"), max_length=20)
    to_status   = models.CharField(_("new status"),      max_length=20)
    changed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("changed by"),
        help_text=_("Null = system-initiated transition (e.g. Celery task)."),
    )
    note       = models.TextField(_("internal note"), blank=True, default="")
    created_at = models.DateTimeField(
        _("logged at"),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name        = _("order status log")
        verbose_name_plural = _("order status logs")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.order.order_number}: "
            f"{self.from_status} → {self.to_status}"
        )

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValueError(
                "OrderStatusLog records are immutable and cannot be updated."
            )
        super().save(*args, **kwargs)
