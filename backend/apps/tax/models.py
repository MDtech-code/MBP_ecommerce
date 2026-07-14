# apps/tax/models.py
from __future__ import annotations
from decimal import Decimal
import logging

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from apps.products.models import Category

logger = logging.getLogger("apps.tax")


class TaxRate(TimeStampedModel):
    """
    GST/tax rate applicable per product category.

    Pakistan FBR compliance — different categories have different
    GST rates. Zero-rated, exempt, and standard-rated categories
    exist under Pakistani tax law.

    Applied at order creation — rate snapshotted on OrderItem.
    """

    class TaxType(models.TextChoices):
        STANDARD  = 'standard',  _('Standard Rate GST')
        ZERO_RATED = 'zero_rated', _('Zero Rated')
        EXEMPT    = 'exempt',    _('GST Exempt')

    category = models.ForeignKey(
        "products.Category",
        on_delete=models.PROTECT,
        related_name="tax_rates",
        verbose_name=_("product category"),
    )
    tax_type = models.CharField(
        _("tax type"),
        max_length=15,
        choices=TaxType.choices,
        default=TaxType.STANDARD,
    )
    rate_percentage = models.DecimalField(
        _("rate (%)"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("GST percentage. e.g. 17.00 for standard GST."),
    )
    is_active = models.BooleanField(
        _("is active"),
        default=True,
    )
    effective_from = models.DateField(
        _("effective from"),
        help_text=_("Date from which this rate is applicable."),
    )

    class Meta:
        verbose_name        = _("tax rate")
        verbose_name_plural = _("tax rates")
        ordering            = ["-effective_from"]
        indexes = [
            models.Index(fields=["category", "-effective_from"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.category.name} — "
            f"{self.rate_percentage}% ({self.get_tax_type_display()})"
        )

 