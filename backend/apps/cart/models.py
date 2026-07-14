# apps/cart/models.py
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


class CartQuerySet(models.QuerySet):
    """
    Custom QuerySet for Cart.

    Use with_items_and_products() whenever you need to access
    cart.subtotal, cart.total_price, cart.total_items, or cart.is_empty.
    Without it, each property fires N queries for N cart items.

    Fast queries that don't need price calculation (e.g. abandoned cart
    detection, existence checks) use the default queryset — no prefetch overhead.
    """

    def with_items_and_products(self) -> "CartQuerySet":
        """
        Prefetches all cart items and their products in 2 additional queries
        (one for items, one for products) regardless of cart count.

        Usage:
            # In view or service:
            cart = Cart.objects.with_items_and_products().get(user=request.user)
            total = cart.total_price  # Zero extra queries
        """
        from apps.cart.models import CartItem  # Lazy — avoids class-order dependency
        return self.prefetch_related(
            models.Prefetch(
                "items",
                queryset=CartItem.objects.select_related("product"),
            )
        )


class Cart(TimeStampedModel):
    """
    One active cart per user.

    Created automatically via post_save signal when User is created.

    FETCH PATTERN — always use with_items_and_products() when
    computing financial totals:
        cart = Cart.objects.with_items_and_products().get(user=user)

    Fast non-financial queries (existence checks, abandoned cart scan):
        Cart.objects.filter(updated_at__lt=cutoff).exists()  ← no prefetch
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name=_("user"),
    )
    coupon = models.ForeignKey(
        "coupons.Coupon",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applied_carts",
        verbose_name=_("applied coupon"),
    )
    coupon_code_input = models.CharField(
        _("coupon code input"),
        max_length=50,
        blank=True,
        default="",
        help_text=_(
            "Last coupon code entered — preserved for display "
            "even if coupon expires between sessions."
        ),
    )

    objects = CartQuerySet.as_manager()

    class Meta:
        verbose_name        = _("cart")
        verbose_name_plural = _("carts")
        indexes = [
            # Abandoned cart Celery task:
            # Cart.objects.filter(updated_at__lt=cutoff, items__isnull=False)
            models.Index(fields=["updated_at"]),
        ]

    def __str__(self) -> str:
        return f"Cart for {self.user.email}"

    # ─── Computed Totals ──────────────────────────────────────────────────────

    @property
    def total_items(self) -> int:
        """
        Sum of all item quantities.
        Uses prefetch cache when called after with_items_and_products().
        """
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self) -> Decimal:
        """
        Sum of all item line totals BEFORE coupon discount.
        Displayed as "Items Total" in cart summary.
        Uses prefetch cache when called after with_items_and_products().
        """
        return sum(
            item.subtotal for item in self.items.all()
        ) or Decimal("0.00")

    @property
    def discount_amount(self) -> Decimal:
        """
        PKR discount from applied coupon against item subtotal.

        Shipping fee is Rs.0 here — delivery city not confirmed until
        checkout. FREE_SHIPPING coupons show Rs.0 at cart stage.
        Actual shipping waiver is applied at order creation when
        shipping_fee is known.

        Returns Decimal("0.00") when no coupon is applied.
        """
        if not self.coupon:
            return Decimal("0.00")
        return self.coupon.calculate_discount(
            subtotal=self.subtotal,
            shipping_fee=Decimal("0.00"),
        )

    @property
    def total_price(self) -> Decimal:
        """
        subtotal minus coupon discount.
        Does NOT include shipping — unknown until delivery address confirmed.
        Cannot go below zero.
        """
        return max(
            self.subtotal - self.discount_amount,
            Decimal("0.00"),
        )

    @property
    def is_empty(self) -> bool:
        """
        True if cart has no items.
        Correctly uses prefetch cache when with_items_and_products() was used.
        Note: .all() uses prefetch cache; .exists() does not.
        """
        items = self.items.all()
        # If prefetch cache exists, use it (zero extra queries)
        if hasattr(items, '_result_cache') and items._result_cache is not None:
            return len(items._result_cache) == 0
        # Otherwise fire a lightweight EXISTS query
        return not items.exists()


class CartItem(TimeStampedModel):
    """
    Single product line in a cart.

    One product per cart enforced by UniqueConstraint.
    Adding the same product again → service layer increments quantity,
    never creates a duplicate row.

    clean() is a UX gatekeeper — catches obviously invalid quantities
    (zero, negative, more than total stock) before hitting the DB.
    It is NOT a concurrency lock.

    Concurrent inventory safety happens in the checkout Service Layer
    using select_for_update() + transaction.atomic().
    """

    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name=_("cart"),
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name=_("product"),
    )
    quantity = models.PositiveIntegerField(
        _("quantity"),
        default=1,
    )

    class Meta:
        verbose_name        = _("cart item")
        verbose_name_plural = _("cart items")
        ordering            = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart",
            )
        ]
        indexes = [
            models.Index(fields=["product", "cart"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.quantity} × {self.product.name} "
            f"({self.cart.user.email})"
        )

    def clean(self) -> None:
        """
        UX gatekeeper — validates data invariants and obvious thresholds.

        What this does:
            - Blocks quantity < 1 (data invariant)
            - Blocks adding out-of-stock products (obvious rejection)
            - Blocks quantity > total stock (soft UX cap)

        What this does NOT do:
            - Concurrent reservation checking (TOCTOU risk — belongs in
              Service Layer with select_for_update())
            - Payment or coupon validation (wrong layer)
        """
        if self.quantity < 1:
            raise ValidationError({
                "quantity": _("Quantity must be at least 1.")
            })

        if hasattr(self, "product") and self.product_id:
            if not self.product.is_in_stock:
                raise ValidationError({
                    "quantity": _(
                        "%(product)s is currently out of stock."
                    ) % {"product": self.product.name}
                })

            if self.quantity > self.product.stock:
                raise ValidationError({
                    "quantity": _(
                        "Only %(stock)d unit(s) of %(product)s available."
                    ) % {
                        "stock":   self.product.stock,
                        "product": self.product.name,
                    }
                })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        super().save(*args, **kwargs)
        logger.debug(
            "CartItem saved: cart=%s product=%s qty=%s",
            self.cart_id,
            self.product_id,
            self.quantity,
        )

    @property
    def subtotal(self) -> Decimal:
        """
        unit_price × quantity using product's current effective price.
        current_price returns discount_price if active, else regular price.
        Requires select_related('product') to avoid N+1.
        """
        return self.product.current_price * self.quantity
