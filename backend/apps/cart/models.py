from __future__ import annotations

import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from apps.products.models import Product

logger = logging.getLogger("apps.cart")


class Cart(TimeStampedModel):
    """
    One cart per user. Created automatically via signal
    when a User account is created (mirrors UserProfile pattern).
    """

    user: models.OneToOneField = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name=_("user"),
    )

    class Meta:
        verbose_name = _("cart")
        verbose_name_plural = _("carts")

    def __str__(self) -> str:
        return f"Cart for {self.user.email}"

    @property
    def total_items(self) -> int:
        """Sum of all item quantities in the cart."""
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self) -> float:
        """Sum of (current_price * quantity) for every item in the cart."""
        return sum(item.subtotal for item in self.items.all())

    @property
    def is_empty(self) -> bool:
        return not self.items.exists()


class CartItem(TimeStampedModel):
    """
    A single product line in a cart, with quantity.
    One product can only appear once per cart — adding it again
    increases quantity instead of creating a duplicate row.
    """

    cart: models.ForeignKey = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("cart"),
    )
    product: models.ForeignKey = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("product"),
    )
    quantity: models.PositiveIntegerField = models.PositiveIntegerField(
        _("quantity"),
        default=1,
    )

    class Meta:
        verbose_name = _("cart item")
        verbose_name_plural = _("cart items")
        unique_together = [["cart", "product"]]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.product.name} ({self.cart.user.email})"

    def clean(self) -> None:
        """
        Validate quantity does not exceed available stock.
        Called explicitly in save() since CartItem is rarely
        created via Django admin forms that auto-call full_clean().
        """
        if self.quantity > self.product.stock:
            raise ValidationError({
                "quantity": _(
                    "Only %(stock)d unit(s) of %(product)s in stock."
                ) % {"stock": self.product.stock, "product": self.product.name}
            })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
        logger.debug(
            "Cart item saved: %s x %s for %s",
            self.quantity, self.product.name, self.cart.user.email,
        )

    @property
    def subtotal(self) -> float:
        """Quantity multiplied by product's current effective price."""
        return float(self.product.current_price) * self.quantity