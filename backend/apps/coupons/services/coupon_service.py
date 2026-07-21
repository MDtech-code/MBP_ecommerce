# apps/coupons/services/coupon_service.py
from __future__ import annotations

"""
Coupon service — business logic for coupon cart operations.

Responsibility:
    All coupon mutation logic for cart interactions lives here.
    Validates coupon eligibility via Phase 1 fast check.
    Writes coupon state to Cart model fields.
    Zero HTTP concerns. Zero DRF imports. Zero serializer calls.

Phase 1 vs Phase 2 validation:
    This service runs Phase 1 validation only — fast O(1) pre-check
    using coupon.can_be_used_by(). This is NOT concurrency-safe.
    Phase 2 re-validation happens inside select_for_update() +
    transaction.atomic() in OrderService.checkout() before any
    CouponUsage record is created.

Dependency direction:
    models → selectors → services → views
"""

import logging

from apps.coupons.models import Coupon
from apps.coupons.selectors.coupon import get_coupon_by_code
from apps.core.exceptions import DomainError

if True:  # TYPE_CHECKING block for Cart — avoids circular import
    from typing import TYPE_CHECKING
    if TYPE_CHECKING:
        from apps.cart.models import Cart

logger = logging.getLogger("apps.coupons")


class CouponService:
    """
    Business operations for coupon-cart interactions.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    Global custom_exception_handler converts DomainError to response.
    """

    @staticmethod
    def apply_to_cart(
        *,
        cart: "Cart",
        code: str,
        user,
    ) -> Coupon:
        """
        Validate and apply a coupon code to the user's cart.

        Runs Phase 1 fast validation via coupon.can_be_used_by().
        On success, sets cart.coupon and cart.coupon_code_input.

        Args:
            cart: Cart instance for the requesting user.
            code: Raw coupon code string entered by user.
            user: Authenticated user requesting the coupon.

        Returns:
            Coupon instance that was successfully applied.

        Raises:
            DomainError (400) — coupon code not found or inactive.
            DomainError (400) — Phase 1 eligibility check failed
                                (expired, limit reached, min order not met,
                                 already used by this user).

        Note:
            Phase 1 is NOT concurrency-safe. Two users can both pass
            this check simultaneously for a coupon with usage_limit_total=1.
            The authoritative race-condition guard is in OrderService.checkout()
            inside select_for_update() + transaction.atomic().
        """
        # ── 1. Fetch coupon — DoesNotExist means invalid code ─────────────
        try:
            coupon = get_coupon_by_code(code)
        except Coupon.DoesNotExist:
            logger.warning(
                "CouponService.apply_to_cart: code not found | "
                "code=%s user_id=%s cart_id=%s",
                code.strip().upper(),
                user.pk,
                cart.pk,
            )
            raise DomainError(
                "Invalid coupon code. Please check and try again.",
                code="coupon_invalid",
                status_code=400,
            )

        # ── 2. Phase 1 eligibility check ──────────────────────────────────
        is_valid, reason = coupon.can_be_used_by(
            user=user,
            subtotal=cart.subtotal,
        )

        if not is_valid:
            logger.warning(
                "CouponService.apply_to_cart: Phase 1 failed | "
                "coupon=%s user_id=%s cart_id=%s reason=%s",
                coupon.code,
                user.pk,
                cart.pk,
                reason,
            )
            raise DomainError(
                str(reason),
                code="coupon_invalid",
                status_code=400,
            )

        # ── 3. Apply coupon to cart ────────────────────────────────────────
        cart.coupon = coupon
        cart.coupon_code_input = coupon.code
        cart.save(update_fields=["coupon", "coupon_code_input"])

        logger.info(
            "CouponService.apply_to_cart: applied | "
            "coupon=%s user_id=%s cart_id=%s",
            coupon.code,
            user.pk,
            cart.pk,
        )

        return coupon

    @staticmethod
    def remove_from_cart(*, cart: "Cart") -> None:
        """
        Remove any applied coupon from the user's cart.

        Clears both the coupon FK and the coupon_code_input field.
        Caller is responsible for checking whether a coupon is actually
        applied before calling this method.

        Args:
            cart: Cart instance with coupon to remove.

        Returns:
            None

        Why both fields cleared:
            cart.coupon = None removes the FK reference.
            cart.coupon_code_input = "" clears the display field.
            Both must be reset so the cart serializer returns
            clean state — no stale code string visible to frontend.
        """
        cart.coupon = None
        cart.coupon_code_input = ""
        cart.save(update_fields=["coupon", "coupon_code_input"])

        logger.info(
            "CouponService.remove_from_cart: removed | cart_id=%s",
            cart.pk,
        )