# apps/cart/services/cart_service.py
from __future__ import annotations

"""
Cart service — business logic for cart operations.

RESPONSIBILITY
──────────────
All cart mutation logic lives here.
Views pass validated Python data in. Service returns model instances.
Zero DRF imports. Zero serializer calls. Zero HTTP concerns.

WHY TRANSACTION AND SELECT_FOR_UPDATE LIVE HERE
────────────────────────────────────────────────
transaction.atomic() and select_for_update() are business/data integrity
concerns — not HTTP concerns. Moving them to the service layer means:
    - Celery tasks can call the same service safely
    - Management commands can call the same service safely
    - Unit tests can call service methods without HTTP request context
    - Views stay thin and readable

CONCURRENCY SAFETY
──────────────────
add_item() uses select_for_update() on CartItem.
Problem without it:
    Two concurrent POST /api/cart/items/ for the same product:
    Request A reads quantity=2
    Request B reads quantity=2
    Request A writes quantity=3
    Request B writes quantity=3  ← should be 4
select_for_update() forces Request B to wait until A commits.
Result: quantity=4. Correct.
"""

import logging
from decimal import Decimal

from django.db import transaction

from apps.cart.models import Cart, CartItem
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.cart")


class CartService:
    """
    Business operations for Cart and CartItem.

    All methods are static — no instance state needed.
    All methods operate within transaction.atomic() where mutations occur.
    All methods raise DomainError for business rule violations.
    """

    @staticmethod
    def add_item(
        *,
        cart: Cart,
        product,
        quantity: int,
    ) -> CartItem:
        """
        Add a product to the cart or increment quantity if already present.

        Upsert logic:
            Product not in cart → create new CartItem with quantity.
            Product already in cart → add requested quantity to existing.

        Args:
            cart:     Cart instance (already fetched by caller).
            product:  Product instance (already validated by serializer).
            quantity: Validated integer >= 1 (validated by serializer).

        Returns:
            CartItem — the created or updated item.

        Raises:
            DomainError (400) — combined quantity would exceed stock.

        Why product already validated by serializer:
            AddToCartSerializer.validate() confirmed product is AVAILABLE
            and quantity <= stock. We re-check combined quantity here
            because the cart may already have some of this product.
            The serializer only validated the requested quantity in isolation.
        """
        with transaction.atomic():
            item, created = (
                CartItem.objects
                .select_for_update()
                .get_or_create(
                    cart=cart,
                    product=product,
                    defaults={"quantity": quantity},
                )
            )

            if not created:
                new_quantity = item.quantity + quantity

                if new_quantity > product.stock:
                    raise DomainError(
                        f"Only {product.stock} unit(s) of "
                        f"{product.name} available. "
                        f"You already have {item.quantity} in your cart.",
                        code="cart_quantity_exceeds_stock",
                        status_code=400,
                        client_extra={
                            "available_stock": product.stock,
                            "current_cart_quantity": item.quantity,
                            "requested_quantity": quantity,
                        },
                    )

                # Use update() to skip full_clean() stock recheck —
                # combined quantity already validated above.
                CartItem.objects.filter(pk=item.pk).update(
                    quantity=new_quantity
                )
                item.quantity = new_quantity

            logger.info(
                "CartService.add_item: %s | cart_id=%s product_id=%s qty=%s",
                "created" if created else "updated",
                cart.pk,
                product.pk,
                quantity,
            )

        return item

    @staticmethod
    def update_item(
        *,
        item: CartItem,
        quantity: int,
    ) -> CartItem | None:
        """
        Update a cart item's quantity or remove it if quantity is 0.

        Args:
            item:     CartItem instance with select_related("product") loaded.
            quantity: New quantity. 0 = remove item.

        Returns:
            Updated CartItem, or None if item was deleted (quantity=0).

        Raises:
            DomainError (400) — quantity exceeds available stock.

        Why quantity=0 removes the item:
            Frontend sends 0 when user clicks minus on quantity=1.
            Cleaner UX than returning 400 — item just disappears.
            Consistent with clear cart behavior.
        """
        if quantity == 0:
            product_id = item.product_id
            item.delete()
            logger.info(
                "CartService.update_item: removed (qty=0) | "
                "item_id=%s product_id=%s",
                item.pk,
                product_id,
            )
            return None

        if quantity > item.product.stock:
            raise DomainError(
                f"Only {item.product.stock} unit(s) of "
                f"{item.product.name} available.",
                code="cart_quantity_exceeds_stock",
                status_code=400,
                client_extra={
                    "available_stock": item.product.stock,
                    "requested_quantity": quantity,
                },
            )

        # Use update() to skip full_clean() — stock validated above.
        CartItem.objects.filter(pk=item.pk).update(quantity=quantity)
        item.quantity = quantity

        logger.info(
            "CartService.update_item: updated | "
            "item_id=%s product_id=%s new_qty=%s",
            item.pk,
            item.product_id,
            quantity,
        )

        return item

    @staticmethod
    def clear_cart(*, cart: Cart) -> int:
        """
        Remove all items from the cart.

        Args:
            cart: Cart instance whose items to delete.

        Returns:
            Number of items deleted.

        Why returns count:
            View logs "items_removed" for observability.
            Caller does not need to count separately.
        """
        items_count, _ = cart.items.all().delete()

        logger.info(
            "CartService.clear_cart: cleared | cart_id=%s items_removed=%s",
            cart.pk,
            items_count,
        )

        return items_count