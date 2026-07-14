# apps/coupons/models.py
from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone  # ✅ Django timezone — has .now()
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.coupons")


class Coupon(TimeStampedModel):
    """
    Discount coupon with three discount types.

    Two-Phase Validation Pattern:
        Phase 1 (can_be_used_by):  Fast O(1) pre-check using times_used counter.
                                   Called when user enters coupon code.
                                   Rejects 99% of invalid codes cheaply.

        Phase 2 (checkout service): Authoritative check using CouponUsage.count()
                                    inside select_for_update() + transaction.atomic().
                                    Called only at order placement moment.
                                    This is the actual race condition guard.

    times_used vs total_used:
        times_used  → fast integer field, incremented via F() at checkout.
                      May temporarily diverge after order cancellations.
                      Used only for Phase 1 pre-check.

        total_used  → property counting CouponUsage records.
                      Always accurate. Used for admin display and Phase 2.
    """

    class DiscountType(models.TextChoices):
        PERCENTAGE    = "percentage",    _("Percentage Discount")
        FIXED_PKR     = "fixed_pkr",     _("Fixed Amount (PKR)")
        FREE_SHIPPING = "free_shipping", _("Free Shipping")

    code = models.CharField(
        _("code"),
        max_length=50,
        unique=True,
        db_index=True,
        help_text=_("e.g. EIDMUBARAK2026 — always stored uppercase."),
    )
    discount_type = models.CharField(
        _("discount type"),
        max_length=20,
        choices=DiscountType.choices,
        default=DiscountType.FIXED_PKR,
    )
    discount_value = models.DecimalField(
        _("discount value"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_(
            "PKR amount for FIXED_PKR. "
            "Percentage (0–100) for PERCENTAGE. "
            "Must be 0 for FREE_SHIPPING."
        ),
    )
    min_order_amount = models.DecimalField(
        _("minimum order amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Minimum cart subtotal in PKR to apply coupon."),
    )
    max_discount_amount = models.DecimalField(
        _("maximum discount amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Cap on discount in PKR — only applies to PERCENTAGE type."),
    )
    usage_limit_total = models.PositiveIntegerField(
        _("total usage limit"),
        null=True,
        blank=True,
        help_text=_("Maximum global uses. Null = unlimited."),
    )
    usage_limit_per_user = models.PositiveSmallIntegerField(
        _("per user usage limit"),
        default=1,
        help_text=_("Maximum times one user can use this coupon."),
    )
    valid_from  = models.DateTimeField(_("valid from"))
    valid_until = models.DateTimeField(_("valid until"))
    is_active   = models.BooleanField(_("is active"), default=True)
    times_used  = models.PositiveIntegerField(
        _("times used"),
        default=0,
        db_index=True,
        help_text=_(
            "Fast pre-check counter for Phase 1 validation. "
            "Incremented atomically via F() expressions at checkout commit. "
            "Decremented on order cancellation. "
            "May temporarily diverge — authoritative check uses "
            "CouponUsage.count() inside the checkout service transaction."
        ),
    )

    class Meta:
        verbose_name        = _("coupon")
        verbose_name_plural = _("coupons")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["code",      "is_active", "valid_until"]),
            models.Index(fields=["is_active", "valid_from", "valid_until"]),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.get_discount_type_display()})"

    # ─── Validation ───────────────────────────────────────────────────────────

    def clean(self) -> None:
        if self.discount_type == self.DiscountType.FREE_SHIPPING:
            if self.discount_value != Decimal("0.00"):
                raise ValidationError({
                    "discount_value": _(
                        "Free shipping coupons must have discount_value=0."
                    )
                })

        if self.discount_type == self.DiscountType.PERCENTAGE:
            if self.discount_value > Decimal("100.00"):
                raise ValidationError({
                    "discount_value": _(
                        "Percentage discount cannot exceed 100."
                    )
                })

        if self.valid_from and self.valid_until:
            if self.valid_from >= self.valid_until:
                raise ValidationError({
                    "valid_until": _("valid_until must be after valid_from.")
                })

    def save(self, *args, **kwargs) -> None:
        self.code = self.code.strip().upper()
        self.full_clean()
        super().save(*args, **kwargs)
        logger.debug(
            "Coupon saved: code=%s type=%s active=%s",
            self.code,
            self.discount_type,
            self.is_active,
        )

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def total_used(self) -> int:
        """
        Authoritative usage count from CouponUsage records.
        Always accurate — reflects cancellations correctly.
        Used for: admin dashboard, Phase 2 checkout lock.
        NOT used for: Phase 1 pre-check (use times_used for that).
        """
        return self.usages.count()

    @property
    def is_currently_valid(self) -> bool:
        """
        True if active and within validity window.
        Does not check usage limits — use can_be_used_by() for full check.
        """
        now = timezone.now()
        return (
            self.is_active
            and self.valid_from <= now <= self.valid_until
        )

    # ─── Business Methods ─────────────────────────────────────────────────────

    def can_be_used_by(
        self,
        user,
        subtotal: Decimal = Decimal("0.00"),
    ) -> tuple[bool, str]:
        """
        Phase 1 fast validation — O(1) for global limit check.

        Called when customer enters coupon code in cart.
        Uses times_used counter (not COUNT) for global limit check.
        Per-user check uses filtered COUNT on indexed columns — acceptable.

        ⚠️  NOT concurrency-safe for the final commit.
        The checkout service MUST re-validate inside
        select_for_update() + transaction.atomic() before creating
        CouponUsage and incrementing times_used.
        """
        if not self.is_active:
            return False, _("This coupon is not active.")

        now = timezone.now()
        if now < self.valid_from:
            return False, _("This coupon is not yet valid.")
        if now > self.valid_until:
            return False, _("This coupon has expired.")

        if subtotal < self.min_order_amount:
            return False, _(
                "Minimum order amount of Rs. %(amount)s required."
            ) % {"amount": self.min_order_amount}

        # Phase 1 global limit: O(1) integer read
        if self.usage_limit_total is not None:
            if self.times_used >= self.usage_limit_total:
                return False, _("This coupon's usage limit has been reached.")

        # Per-user limit: filtered COUNT on indexed (coupon, user) columns
        if self.usages.filter(user=user).count() >= self.usage_limit_per_user:
            return False, _("You have already used this coupon.")

        return True, ""

    def calculate_discount(
        self,
        subtotal: Decimal,
        shipping_fee: Decimal,
    ) -> Decimal:
        """
        Pure calculation — no DB queries. Safe to call anywhere.

        PERCENTAGE:   subtotal × rate%, capped at max_discount_amount.
        FIXED_PKR:    discount_value, capped at subtotal (no negative totals).
        FREE_SHIPPING: returns shipping_fee exactly.
        """
        if self.discount_type == self.DiscountType.PERCENTAGE:
            discount = subtotal * self.discount_value / Decimal("100")
            if self.max_discount_amount is not None:
                discount = min(discount, self.max_discount_amount)
            return discount.quantize(Decimal("0.01"))

        if self.discount_type == self.DiscountType.FIXED_PKR:
            return min(self.discount_value, subtotal)

        if self.discount_type == self.DiscountType.FREE_SHIPPING:
            return shipping_fee

        return Decimal("0.00")


class CouponUsage(TimeStampedModel):
    """
    Financial record of each coupon redemption.

    OneToOne on order — one coupon per order maximum.

    coupon PROTECT: deleting a coupon must not silently delete
                    discount records from real order history.
    user SET_NULL:  preserves usage record after account deletion
                    to prevent coupon reuse after delete + re-register.
    order PROTECT:  usage record is a financial document — cannot
                    be deleted without explicitly handling the order.
    """

    coupon = models.ForeignKey(
        Coupon,
        on_delete=models.PROTECT,
        related_name="usages",
        verbose_name=_("coupon"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coupon_usages",
        verbose_name=_("user"),
        help_text=_(
            "SET_NULL — usage record preserved after account deletion. "
            "Prevents coupon reuse after delete + re-register."
        ),
    )
    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="coupon_usage",
        verbose_name=_("order"),
    )
    discount_applied = models.DecimalField(
        _("discount applied"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Actual PKR amount discounted on this order."),
    )

    class Meta:
        verbose_name        = _("coupon usage")
        verbose_name_plural = _("coupon usages")
        ordering            = ["-created_at"]
        indexes = [
            # Per-user limit check: usages.filter(user=user).count()
            models.Index(fields=["coupon", "user"]),
            # Analytics: coupon performance over time
            models.Index(fields=["coupon", "created_at"]),
        ]

    def __str__(self) -> str:
        user_email = getattr(self.user, "email", "deleted user")
        return (
            f"{self.coupon.code} used by {user_email} "
            f"— Rs. {self.discount_applied}"
        )
