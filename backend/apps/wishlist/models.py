# apps/wishlist/models.py
from __future__ import annotations
import logging

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from apps.products.models import Product

logger = logging.getLogger("apps.wishlist")




class WishlistItem(TimeStampedModel):
    """
    Single product saved to wishlist.
    One product per wishlist — unique_together enforces this.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wishlist_items",
        verbose_name=_("user"),
    )
    product = models.ForeignKey(
        "products.Product",
        on_delete=models.CASCADE,
        related_name="wishlisted_by",
        verbose_name=_("product"),
    )

    class Meta:
        verbose_name = _("wishlist item")
        verbose_name_plural = _("wishlist items")
        unique_together = [["user", "product"]]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.product.name} in {self.wishlist.user.email} wishlist"