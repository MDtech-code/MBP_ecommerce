from __future__ import annotations

import logging
from decimal import Decimal
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from apps.products.models import Product

logger = logging.getLogger("apps.cart")


class Cart(TimeStampedModel):
    """
    One cart per user.

    Created automatically via post_save signal when a User is created.
    Properties (total_items, total_price, is_empty) are computed from
    prefetched items — callers must prefetch_related("items__product")
    to avoid N+1 queries.
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
        """
        Sum of all item quantities.

        Uses prefetch cache if items are prefetched — no extra query.
        Requires prefetch_related('items') on the queryset.
        """
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self) -> Decimal:
        """
        Sum of (current_price * quantity) for every item.

        Uses prefetch cache if items and products are prefetched.
        Requires prefetch_related('items__product') on the queryset.
        Returns Decimal for precision — never float for monetary values.
        """
        return sum(
            item.subtotal for item in self.items.all()
        ) or Decimal("0.00")

    @property
    def is_empty(self) -> bool:
        """
        True if cart has no items.

        Uses prefetch cache if items are prefetched.
        Avoids a separate .exists() query when items are already loaded.
        """
        return len(self.items.all()) == 0

  


class CartItem(TimeStampedModel):
    """
    A single product line in a cart with quantity.

    One product can only appear once per cart (unique_together).
    Adding the same product again increases quantity instead of
    creating a duplicate row — enforced at the view layer.

    Stock validation runs on every save() via full_clean().
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

        Called explicitly via full_clean() in save() because CartItem
        is rarely created through Django admin forms that auto-call
        full_clean(). This ensures validation runs on every save path.
        """
        if self.quantity > self.product.stock:
            raise ValidationError({
                "quantity": _(
                    "Only %(stock)d unit(s) of %(product)s in stock."
                ) % {
                    "stock": self.product.stock,
                    "product": self.product.name,
                }
            })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
        logger.debug(
            "Cart item saved",
            extra={
                "cart_id": self.cart_id,
                "product_id": self.product_id,
                "quantity": self.quantity,
            },
        )

    @property
    def subtotal(self) -> Decimal:
        """
        Quantity multiplied by product's current effective price.

        Returns Decimal — never float for monetary values.
        Accesses product.current_price — requires select_related('product')
        on the queryset to avoid per-item N+1 queries.
        """
        return Decimal(str(self.product.current_price)) * self.quantity
    