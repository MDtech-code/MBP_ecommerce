from __future__ import annotations

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.common.models import TimeStampedModel
from apps.products.models import Product
from apps.orders.models import OrderItem


class Review(TimeStampedModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("product"))
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("reviewer"))
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        verbose_name=_("verified purchase item"),
    )
    rating = models.SmallIntegerField(_("rating stars"), validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(_("headline"), max_length=100, blank=True, default="")
    body = models.TextField(_("review context"), blank=True, default="")
    is_approved = models.BooleanField(_("moderation approval flag"), default=True)

    class Meta:
        verbose_name = _("customer review")
        verbose_name_plural = _("customer reviews")
        unique_together = ("product", "user")
        indexes = [
            models.Index(fields=["rating"]),
        ]

    def __str__(self) -> str:
        return f"{self.rating}★ by {self.user.email} for {self.product.name}"