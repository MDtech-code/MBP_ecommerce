from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedModel


class Coupon(TimeStampedModel):
    class DiscountType(models.TextChoices):
        PERCENTAGE = 'PERCENTAGE', _('Percentage Discount')
        FIXED_PKR = 'FIXED_PKR', _('Fixed Amount (PKR)')
        FREE_SHIPPING = 'FREE_SHIPPING', _('Free Shipping')

    code = models.CharField(max_length=50, unique=True, db_index=True, help_text=_("e.g., EIDMUBARAK2026"))
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices, default=DiscountType.FIXED_PKR)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.00'))])
    
    min_order_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'),
        help_text=_("Minimum cart value in PKR required to apply coupon")
    )
    max_discount_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text=_("Maximum discount cap in PKR for percentage coupons")
    )
    
    usage_limit_total = models.PositiveIntegerField(null=True, blank=True, help_text=_("Total times this coupon can be used globally"))
    usage_limit_per_user = models.PositiveSmallIntegerField(default=1)
    total_used = models.PositiveIntegerField(default=0)
    
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = _("Coupon")
        verbose_name_plural = _("Coupons")
        indexes = [
            models.Index(fields=['code', 'is_active', 'valid_until']),
        ]

    def __str__(self):
        return f"{self.code} ({self.get_discount_type_display()})"


class CouponUsage(TimeStampedModel):
    """
    Tracks who used which coupon and on which order to enforce limits.
    """
    coupon = models.ForeignKey(Coupon, on_delete=models.PROTECT, related_name='usages')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=15, db_index=True, help_text=_("Track guest checkouts by PK phone number (+923000000000)"))
    order_id = models.CharField(max_length=100, unique=True, help_text=_("Reference to the Order model UUID/ID"))
    discount_applied = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _("Coupon Usage")
        verbose_name_plural = _("Coupon Usages")
        unique_together = ('coupon', 'user', 'order_id')