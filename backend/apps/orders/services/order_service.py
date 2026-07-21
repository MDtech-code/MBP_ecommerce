# apps/orders/services/order_service.py
from __future__ import annotations

"""
Order service — the transactional engine for checkout and cancellation.

Responsibility:
    All checkout and order mutation logic lives here.
    This is the most critical file in the entire codebase.
    Views pass validated data in. Service returns Order instances out.
    Zero DRF imports. Zero serializer calls. Zero HTTP concerns.

Transaction boundary:
    checkout()      — one transaction.atomic() covers steps A through L.
    cancel_order()  — one transaction.atomic() covers status transition,
                      stock restore, coupon decrement, payment update.

    Post-atomic actions (cache, email) run AFTER commit.
    External calls (email, gateway) are NEVER inside atomic blocks.

Concurrency safety:
    select_for_update() on Product rows — prevents overselling.
    select_for_update() on Coupon row  — prevents usage limit breach.
    Lock order is sorted by product ID — prevents deadlocks.
    F() expressions for all stock/counter mutations — atomic SQL UPDATE.

Dependency direction:
    models → selectors → services → views
"""

import logging
from decimal import Decimal
from typing import Any

from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.cart.models import Cart, CartItem
from apps.core.exceptions import DomainError
from apps.coupons.models import Coupon, CouponUsage
from apps.coupons.selectors.coupon import get_coupon_for_cart
from apps.orders.models import Order, OrderItem, OrderShippingAddress
from apps.payments.models import PaymentTransaction
from apps.products.models import Product
from apps.products.services.product_service import ProductService
from apps.tax.selectors.tax import get_tax_rate_for_category

logger = logging.getLogger("apps.orders")


# ─────────────────────────────────────────────────────────────────────────────
# PRIVATE HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _calculate_shipping_fee(city: str) -> Decimal:
    """
    Return flat-rate shipping fee based on city tier.

    Phase 1 implementation — simple flat rate by city name.
    Phase 2 will replace this with PostEx/TCS/Leopards API call
    via a Celery task to avoid blocking checkout on courier API latency.

    Tier 1 (Rs. 150): Lahore, Karachi, Islamabad, Rawalpindi.
    All other cities (Rs. 200).

    Args:
        city: Delivery city string from shipping address input.

    Returns:
        Decimal shipping fee in PKR.
    """
    major_cities = {"lahore", "karachi", "islamabad", "rawalpindi"}
    if city.lower().strip() in major_cities:
        return Decimal("150.00")
    return Decimal("200.00")


def _map_payment_method_to_gateway(payment_method: str) -> str:
    """
    Map Order.PaymentMethod choice to PaymentTransaction.Gateway choice.

    COD           → Gateway.COD
    ONLINE        → Gateway.SAFEPAY (Phase 2 adds per-gateway selection)
    BANK_TRANSFER → Gateway.RAAST

    Args:
        payment_method: One of Order.PaymentMethod choices.

    Returns:
        Corresponding PaymentTransaction.Gateway string value.
    """
    mapping = {
        Order.PaymentMethod.COD:           PaymentTransaction.Gateway.COD,
        Order.PaymentMethod.ONLINE:        PaymentTransaction.Gateway.SAFEPAY,
        Order.PaymentMethod.BANK_TRANSFER: PaymentTransaction.Gateway.RAAST,
    }
    return mapping.get(payment_method, PaymentTransaction.Gateway.COD)


# ─────────────────────────────────────────────────────────────────────────────
# ORDER SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class OrderService:
    """
    Transactional business operations for Order creation and management.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    Global custom_exception_handler converts DomainError to response.
    """

    @staticmethod
    def checkout(
        *,
        user,
        validated_data: dict[str, Any],
        cart: Cart,
    ) -> Order:
        """
        Execute the full atomic checkout operation.

        Accepts validated input data and an existing Cart instance.
        Creates Order, OrderShippingAddress, OrderItems, PaymentTransaction,
        CouponUsage (if coupon), decrements stock, clears cart.
        All inside one transaction.atomic() — full rollback on any failure.

        Post-atomic: invalidates product caches and fires confirmation
        email Celery task (stub — notifications app wires the actual task).

        Args:
            user:           Authenticated, verified User instance.
            validated_data: Output of CheckoutInputSerializer.validated_data.
                            Keys: payment_method, shipping_address, notes.
            cart:           User's Cart instance (fetched by view).

        Returns:
            Created Order instance.

        Raises:
            DomainError (400) — cart empty, product unavailable,
                                insufficient stock, coupon invalid.
            DomainError (409) — coupon already used, coupon limit reached,
                                coupon expired (Phase 2 authoritative check).
        """
        payment_method   = validated_data["payment_method"]
        shipping_address = validated_data["shipping_address"]
        notes            = validated_data.get("notes", "")

        # ── Pre-checks (outside atomic — fast rejections) ─────────────────

        # Step 1 — Cart empty check
        if cart.is_empty:
            raise DomainError(
                "Your cart is empty. Add items before checking out.",
                code="cart_empty",
                status_code=400,
            )

        # Step 2 — Fetch cart items with products
        cart_items = list(
            CartItem.objects
            .select_related("product__category")
            .filter(cart=cart)
        )

        # Step 3 — Soft product availability check
        unavailable = [
            item.product.name
            for item in cart_items
            if not item.product.is_in_stock
        ]
        if unavailable:
            raise DomainError(
                "Some items in your cart are no longer available.",
                code="product_unavailable",
                status_code=400,
                client_extra={"unavailable_products": unavailable},
            )

        # Step 4 — Phase 1 coupon pre-check
        coupon = get_coupon_for_cart(cart)
        if coupon is not None:
            cart_subtotal = sum(
                item.product.current_price * item.quantity
                for item in cart_items
            )
            is_valid, reason = coupon.can_be_used_by(
                user=user,
                subtotal=cart_subtotal,
            )
            if not is_valid:
                raise DomainError(
                    str(reason),
                    code="coupon_invalid",
                    status_code=400,
                )

        # ── Atomic transaction block ──────────────────────────────────────
        with transaction.atomic():

            # Step A — Lock Product rows (sorted by ID to prevent deadlocks)
            product_ids = sorted(item.product_id for item in cart_items)
            locked_products = (
                Product.objects
                .select_for_update()
                .filter(id__in=product_ids)
            )
            locked_products_dict = {p.pk: p for p in locked_products}

            # Step B — Lock Coupon row if coupon applied
            locked_coupon: Coupon | None = None
            if coupon is not None:
                locked_coupon = (
                    Coupon.objects
                    .select_for_update()
                    .get(pk=coupon.pk)
                )

            # Step C — Validate stock against locked values
            for cart_item in cart_items:
                product = locked_products_dict[cart_item.product_id]
                if product.stock < cart_item.quantity:
                    raise DomainError(
                        f"Only {product.stock} unit(s) of "
                        f"'{product.name}' available. "
                        f"Please update your cart.",
                        code="insufficient_stock",
                        status_code=400,
                        client_extra={
                            "product_id": product.pk,
                            "product_name": product.name,
                            "available": product.stock,
                            "requested": cart_item.quantity,
                        },
                    )

            # Step D — Phase 2 coupon validation (authoritative)
            if locked_coupon is not None:
                user_usage_count = CouponUsage.objects.filter(
                    coupon=locked_coupon,
                    user=user,
                ).count()
                if user_usage_count >= locked_coupon.usage_limit_per_user:
                    raise DomainError(
                        "You have already used this coupon.",
                        code="coupon_already_used",
                        status_code=409,
                    )

                if locked_coupon.usage_limit_total is not None:
                    total_usage = CouponUsage.objects.filter(
                        coupon=locked_coupon,
                    ).count()
                    if total_usage >= locked_coupon.usage_limit_total:
                        raise DomainError(
                            "This coupon's usage limit has been reached.",
                            code="coupon_limit_reached",
                            status_code=409,
                        )

                if not locked_coupon.is_currently_valid:
                    raise DomainError(
                        "This coupon has expired.",
                        code="coupon_expired",
                        status_code=409,
                    )

            # Step E — Calculate all financials (pure Python, zero DB reads)
            item_calculations: list[dict] = []
            for cart_item in cart_items:
                product  = locked_products_dict[cart_item.product_id]
                tax_rate = get_tax_rate_for_category(product.category_id)

                item_subtotal = (
                    product.current_price * cart_item.quantity
                ).quantize(Decimal("0.01"))

                item_discount = (
                    (product.price - product.current_price) * cart_item.quantity
                ).quantize(Decimal("0.01"))

                item_tax = (
                    item_subtotal * tax_rate / Decimal("100")
                ).quantize(Decimal("0.01"))

                item_calculations.append({
                    "product":          product,
                    "quantity":         cart_item.quantity,
                    "original_price":   product.price,
                    "unit_price":       product.current_price,
                    "tax_rate":         tax_rate,
                    "subtotal":         item_subtotal,
                    "discount_amount":  item_discount,
                    "tax_amount":       item_tax,
                })

            order_subtotal  = sum(
                c["subtotal"] for c in item_calculations
            )
            order_tax       = sum(
                c["tax_amount"] for c in item_calculations
            )
            shipping_fee    = _calculate_shipping_fee(
                city=shipping_address["city"]
            )
            discount_amount = Decimal("0.00")

            if locked_coupon is not None:
                discount_amount = locked_coupon.calculate_discount(
                    subtotal=order_subtotal,
                    shipping_fee=shipping_fee,
                )

            total_price = max(
                (order_subtotal - discount_amount + shipping_fee + order_tax)
                .quantize(Decimal("0.01")),
                Decimal("0.00"),
            )

            # Step F — Create Order
            order = Order.objects.create(
                user=user,
                payment_method=payment_method,
                notes=notes,
                subtotal=order_subtotal,
                shipping_fee=shipping_fee,
                discount_amount=discount_amount,
                tax_amount=order_tax,
                total_price=total_price,
                coupon=locked_coupon,
                coupon_code_snapshot=(
                    locked_coupon.code if locked_coupon else ""
                ),
                status=Order.Status.PENDING,
            )

            logger.info(
                "OrderService.checkout: Order created | "
                "order_number=%s user_id=%s total=%s",
                order.order_number,
                user.pk,
                total_price,
            )

            # Step G — Create OrderShippingAddress (immutable snapshot)
            OrderShippingAddress.objects.create(
                order=order,
                full_name=shipping_address["full_name"],
                phone=shipping_address["phone"],
                address_line1=shipping_address["address_line1"],
                address_line2=shipping_address.get("address_line2", ""),
                city=shipping_address["city"],
                province=shipping_address["province"],
                postal_code=shipping_address["postal_code"],
            )

            # Step H — Create OrderItems via bulk_create
            # CRITICAL: bulk_create skips save() — calculated fields
            # (subtotal, discount_amount, tax_amount) must be passed
            # explicitly. Never rely on save() auto-calculation here.
            order_items_to_create = [
                OrderItem(
                    order=order,
                    product=calc["product"],
                    product_name=calc["product"].name,
                    product_sku=calc["product"].sku,
                    original_price=calc["original_price"],
                    unit_price=calc["unit_price"],
                    quantity=calc["quantity"],
                    tax_rate_percentage=calc["tax_rate"],
                    subtotal=calc["subtotal"],
                    discount_amount=calc["discount_amount"],
                    tax_amount=calc["tax_amount"],
                )
                for calc in item_calculations
            ]
            OrderItem.objects.bulk_create(order_items_to_create)

            # Step I — Deduct stock via F() atomic SQL UPDATE
            # F() generates: UPDATE products SET stock = stock - qty WHERE id=X
            # Python arithmetic is NOT used — avoids read-modify-write gap.
            for calc in item_calculations:
                Product.objects.filter(pk=calc["product"].pk).update(
                    stock=models.F("stock") - calc["quantity"]
                )

            # Step J — Create CouponUsage + increment times_used
            if locked_coupon is not None:
                CouponUsage.objects.create(
                    coupon=locked_coupon,
                    user=user,
                    order=order,
                    discount_applied=discount_amount,
                )
                Coupon.objects.filter(pk=locked_coupon.pk).update(
                    times_used=models.F("times_used") + 1
                )

                logger.info(
                    "OrderService.checkout: CouponUsage created | "
                    "coupon=%s order=%s discount=%s",
                    locked_coupon.code,
                    order.order_number,
                    discount_amount,
                )

            # Step K — Create PaymentTransaction
            transaction_obj = PaymentTransaction.objects.create(
                order=order,
                user=user,
                gateway=_map_payment_method_to_gateway(payment_method),
                status=PaymentTransaction.Status.PENDING,
                amount_pkr=total_price,
            )

            logger.info(
                "OrderService.checkout: PaymentTransaction created | "
                "order=%s gateway=%s amount=%s",
                order.order_number,
                transaction_obj.gateway,
                total_price,
            )

            # Step L — Clear cart + reset coupon fields
            # Cart cleared INSIDE atomic so if anything above failed,
            # cart remains intact and customer can retry checkout.
            cart.items.all().delete()
            cart.coupon = None
            cart.coupon_code_input = ""
            cart.save(update_fields=["coupon", "coupon_code_input"])

            logger.info(
                "OrderService.checkout: cart cleared | "
                "cart_id=%s user_id=%s",
                cart.pk,
                user.pk,
            )

        # ── Post-atomic actions (outside transaction) ─────────────────────
        # These run after the transaction commits successfully.
        # Failure here does NOT affect the order — already committed.

        # Step M — Invalidate product caches (stock levels changed)
        affected_slugs = [calc["product"].slug for calc in item_calculations]
        ProductService.invalidate_list_cache()
        for slug in affected_slugs:
            ProductService.invalidate_detail_cache(slug)

        logger.info(
            "OrderService.checkout: product caches invalidated | "
            "slugs=%s",
            affected_slugs,
        )

        
        # Step N — Fire order confirmation email (Celery task)
        # Must NEVER be inside transaction.atomic() — if email server is down,
        # atomic would roll back the entire order.
        from apps.notifications.tasks import send_order_confirmation_email
        send_order_confirmation_email.delay(order_id=order.pk)

        logger.info(
            "OrderService.checkout: confirmation email task queued | order=%s",
            order.order_number,
        )

        # Step O — Low stock alert per affected product (post-atomic)
        # F() UPDATE in Step I does NOT trigger Django post_save signal.
        # QuerySet.update() bypasses signals. We call explicitly here.
        for calc in item_calculations:
            product = calc["product"]
            product.refresh_from_db(fields=["stock"])
            ProductService.create_low_stock_alert(product)

        return order

    @staticmethod
    def cancel_order(*, order: Order, user) -> Order:
        """
        Cancel a PENDING order and reverse all associated state changes.

        Transitions order to CANCELLED, restores product stock,
        decrements coupon times_used (without deleting CouponUsage),
        and marks any PENDING PaymentTransaction as FAILED.

        All mutations inside one transaction.atomic() — full rollback
        if any step fails.

        Args:
            order: Order instance to cancel (fetched and owned by caller).
            user:  Authenticated user requesting cancellation.

        Returns:
            Updated Order instance after cancellation.

        Raises:
            DomainError (409) — order is not in PENDING status.
                                Only PENDING orders can be customer-cancelled.
        """
        # Pre-check outside atomic — fast rejection
        if not order.is_cancellable:
            raise DomainError(
                f"This order cannot be cancelled. "
                f"Current status: '{order.get_status_display()}'.",
                code="order_not_cancellable",
                status_code=409,
            )

        with transaction.atomic():

            # Step 1 — Transition status via state machine
            # transition_to() updates status, sets cancelled_at,
            # creates OrderStatusLog — all atomically.
            order.transition_to(
                Order.Status.CANCELLED,
                changed_by=user,
                note="Customer cancellation request.",
            )

            # Step 2 — Restore stock via F() atomic SQL UPDATE
            order_items = list(order.items.select_related("product").all())
            for item in order_items:
                Product.objects.filter(pk=item.product_id).update(
                    stock=models.F("stock") + item.quantity
                )

            logger.info(
                "OrderService.cancel_order: stock restored | "
                "order=%s items=%s",
                order.order_number,
                [(i.product_id, i.quantity) for i in order_items],
            )

            # Step 3 — Decrement coupon times_used if coupon was applied
            # CouponUsage is a financial record — NEVER deleted.
            # Decrementing times_used allows future use up to the limit.
            # Deleting CouponUsage would allow reuse after cancel + reorder.
            if order.coupon_id:
                Coupon.objects.filter(pk=order.coupon_id).update(
                    times_used=models.F("times_used") - 1
                )
                logger.info(
                    "OrderService.cancel_order: coupon times_used decremented | "
                    "order=%s coupon_id=%s",
                    order.order_number,
                    order.coupon_id,
                )

            # Step 4 — Mark PENDING PaymentTransaction as FAILED
            updated = PaymentTransaction.objects.filter(
                order=order,
                status=PaymentTransaction.Status.PENDING,
            ).update(status=PaymentTransaction.Status.FAILED)

            logger.info(
                "OrderService.cancel_order: payment transactions updated | "
                "order=%s transactions_updated=%s",
                order.order_number,
                updated,
            )

        # ── Post-atomic actions ───────────────────────────────────────────

        # Invalidate product caches (stock restored)
        affected_slugs = [item.product.slug for item in order_items]
        ProductService.invalidate_list_cache()
        for slug in affected_slugs:
            ProductService.invalidate_detail_cache(slug)

        # # Fire cancellation email (Celery task)
        # try:
        #     from apps.notifications.tasks import send_order_cancellation_email
        #     send_order_cancellation_email.delay(order_id=order.pk)
        # except ImportError:
        #     logger.warning(
        #         "OrderService.cancel_order: notifications task not available | "
        #         "order=%s — email skipped",
        #         order.order_number,
        #     )
        # Fire cancellation email (Celery task)
        from apps.notifications.tasks import send_order_cancellation_email
        send_order_cancellation_email.delay(order_id=order.pk)
        
        logger.info(
            "OrderService.cancel_order: cancellation email task queued | order=%s",
            order.order_number,
        )

        # Low stock alerts post-atomic (after stock restored — clear resolved)
        for item in order_items:
            item.product.refresh_from_db(fields=["stock"])
            ProductService.create_low_stock_alert(item.product)

        logger.info(
            "OrderService.cancel_order: complete | "
            "order=%s user_id=%s",
            order.order_number,
            user.pk,
        )

        return order