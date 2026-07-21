# apps/cart/views.py
from __future__ import annotations

"""
Cart app — View layer.

RESPONSIBILITY
──────────────
HTTP concerns only:
    - Parse request parameters
    - Validate input via serializers
    - Call service layer for mutations
    - Call selector for reads
    - Serialize results
    - Return standardized response via BaseAPIView helpers

Zero business logic. Zero transaction management.
Zero direct ORM mutations.

EXCEPTION HANDLING POLICY
──────────────────────────
We do NOT wrap normal operations in try/except.
The global custom_exception_handler handles all unhandled exceptions.

ONE LEGITIMATE EXCEPTION:
    Cart.DoesNotExist → returns 500, not 404.
    A missing cart means the post_save signal on User creation failed.
    This is a server-side defect — the client did nothing wrong.
    We catch it explicitly to return the correct status and message.
    DomainError from service propagates naturally → handler catches it.

DEPENDENCY DIRECTION
────────────────────
    selectors/cart.py  (reads)
    services/cart_service.py  (mutations)
         ↑
    views.py   ← this file
"""

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request

from apps.core.api.views import BaseAPIView

from .models import Cart
from .selectors.cart import get_cart_for_user, get_cart_with_items
from .serializers import (
    AddToCartSerializer,
    CartItemSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)
from .services.cart_service import CartService

logger = logging.getLogger("apps.cart")


# ─────────────────────────────────────────────────────────────────────────────
# CART DETAIL
# ─────────────────────────────────────────────────────────────────────────────

class CartDetailAPIView(BaseAPIView):
    """
    GET /api/cart/

    Return the authenticated user's cart with all items and totals.

    Why Cart.DoesNotExist → 500 not 404:
        Cart is auto-created by post_save signal on User creation.
        A missing cart means the signal failed — server-side defect.
        The client did nothing wrong. 404 would imply a bad request.
        500 + support message is the correct signal to the user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request):
        try:
            cart = get_cart_with_items(request.user)
        except Cart.DoesNotExist:
            logger.error(
                "CartDetailAPIView: cart missing for user | "
                "user_id=%s request_id=%s — signal failure suspected",
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "CartDetailAPIView: OK | user_id=%s request_id=%s",
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Cart retrieved successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ADD TO CART
# ─────────────────────────────────────────────────────────────────────────────

class AddToCartAPIView(BaseAPIView):
    """
    POST /api/cart/items/

    Add a product to the cart, or increase quantity if already present.

    Input:
        product_id : int  — must reference an AVAILABLE product
        quantity   : int  — default 1, min 1

    DomainError from CartService.add_item() propagates automatically
    to custom_exception_handler — no try/except needed here.

    Success (201): full updated cart.
    Error   (400): validation failure or stock exceeded.
    Error   (500): cart missing (signal failure).
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request):
        # ── 1. Validate input ──────────────────────────────────────────────
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "AddToCartAPIView: validation failed | "
                "user_id=%s request_id=%s errors=%s",
                request.user.pk,
                getattr(request, "id", "n/a"),
                serializer.errors,
            )
            return self.error_response(
                message=_("Could not add item to cart."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]

        # ── 2. Fetch cart (cheap — no prefetch needed before mutation) ─────
        try:
            cart = get_cart_for_user(request.user)
        except Cart.DoesNotExist:
            logger.error(
                "AddToCartAPIView: cart missing for user | "
                "user_id=%s request_id=%s — signal failure suspected",
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 3. Delegate mutation to service ───────────────────────────────
        # DomainError (stock exceeded) propagates → global handler catches
        CartService.add_item(
            cart=cart,
            product=product,
            quantity=quantity,
        )

        logger.info(
            "AddToCartAPIView: OK | user_id=%s product_id=%s qty=%s "
            "request_id=%s",
            request.user.pk,
            product.pk,
            quantity,
            getattr(request, "id", "n/a"),
        )

        # ── 4. Re-fetch with full prefetch for serialization ───────────────
        cart = get_cart_with_items(request.user)
        return self.created_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Item added to cart successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# UPDATE / REMOVE CART ITEM
# ─────────────────────────────────────────────────────────────────────────────

class UpdateCartItemAPIView(BaseAPIView):
    """
    PATCH  /api/cart/items/<item_id>/ → update quantity
    DELETE /api/cart/items/<item_id>/ → remove item

    Why PATCH not PUT:
        Only quantity is updated — partial update semantics.

    Ownership enforced via selector filter cart__user=request.user.
    DomainError from service propagates automatically.

    Success (200): full updated cart.
    Error   (400): quantity exceeds stock.
    Error   (404): item not found or not owned by user.
    """

    permission_classes = [IsAuthenticated]

    def _get_item(self, item_id: int, user):
        """
        Fetch cart item scoped to requesting user.
        Returns None if not found — caller returns 404.

        Why select_related("product", "cart"):
            service.update_item() accesses item.product.stock and name.
            cart is needed for ownership context in logs.
        """
        from .models import CartItem
        return (
            CartItem.objects
            .select_related("product", "cart")
            .filter(id=item_id, cart__user=user)
            .first()
        )

    def patch(self, request: Request, item_id: int):
        # ── 1. Ownership check ─────────────────────────────────────────────
        item = self._get_item(item_id, request.user)
        if not item:
            logger.warning(
                "UpdateCartItemAPIView.patch: item not found | "
                "item_id=%s user_id=%s request_id=%s",
                item_id,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(
                message=_("Cart item not found.")
            )

        # ── 2. Validate input ──────────────────────────────────────────────
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "UpdateCartItemAPIView.patch: validation failed | "
                "item_id=%s user_id=%s errors=%s",
                item_id,
                request.user.pk,
                serializer.errors,
            )
            return self.error_response(
                message=_("Could not update cart item."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        quantity = serializer.validated_data["quantity"]

        # ── 3. Delegate to service ─────────────────────────────────────────
        # DomainError (stock exceeded) propagates → global handler
        CartService.update_item(item=item, quantity=quantity)

        logger.info(
            "UpdateCartItemAPIView.patch: OK | "
            "item_id=%s user_id=%s new_qty=%s request_id=%s",
            item_id,
            request.user.pk,
            quantity,
            getattr(request, "id", "n/a"),
        )

        # ── 4. Re-fetch with full prefetch for serialization ───────────────
        cart = get_cart_with_items(request.user)
        message = (
            _("Item removed from cart.")
            if quantity == 0
            else _("Cart item updated successfully.")
        )
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=message,
        )

    def delete(self, request: Request, item_id: int):
        # ── 1. Ownership check ─────────────────────────────────────────────
        item = self._get_item(item_id, request.user)
        if not item:
            logger.warning(
                "UpdateCartItemAPIView.delete: item not found | "
                "item_id=%s user_id=%s request_id=%s",
                item_id,
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.not_found_response(
                message=_("Cart item not found.")
            )

        product_id = item.product_id

        # ── 2. Delete directly — no business logic needed ──────────────────
        # Why not go through service for explicit delete:
        #   DELETE endpoint has one job — remove the item.
        #   No stock check, no quantity calculation.
        #   Service.update_item(quantity=0) would work too but
        #   calling delete() directly is clearer intent for explicit DELETE.
        item.delete()

        logger.info(
            "UpdateCartItemAPIView.delete: OK | "
            "item_id=%s product_id=%s user_id=%s request_id=%s",
            item_id,
            product_id,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        # ── 3. Re-fetch for serialization ──────────────────────────────────
        cart = get_cart_with_items(request.user)
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Item removed from cart successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# CLEAR CART
# ─────────────────────────────────────────────────────────────────────────────

class ClearCartAPIView(BaseAPIView):
    """
    DELETE /api/cart/clear/

    Remove all items from the authenticated user's cart.

    Success (200): empty cart returned.
    Error   (500): cart missing (signal failure).
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request):
        # ── 1. Fetch cart (cheap — no prefetch before mutation) ────────────
        try:
            cart = get_cart_for_user(request.user)
        except Cart.DoesNotExist:
            logger.error(
                "ClearCartAPIView: cart missing for user | "
                "user_id=%s request_id=%s — signal failure suspected",
                request.user.pk,
                getattr(request, "id", "n/a"),
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # ── 2. Delegate to service ─────────────────────────────────────────
        items_count = CartService.clear_cart(cart=cart)

        logger.info(
            "ClearCartAPIView: OK | user_id=%s items_removed=%s "
            "request_id=%s",
            request.user.pk,
            items_count,
            getattr(request, "id", "n/a"),
        )

        # ── 3. Re-fetch for serialization ──────────────────────────────────
        cart = get_cart_with_items(request.user)
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Cart cleared successfully."),
        )


# # apps/cart/views.py
# from __future__ import annotations

# import logging

# from django.db import transaction
# from django.utils.translation import gettext_lazy as _
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated
# from rest_framework.request import Request
# from rest_framework.response import Response

# from apps.core.api.views import BaseAPIView

# from .models import Cart, CartItem
# from .serializers import (
#     AddToCartSerializer,
#     CartSerializer,
#     UpdateCartItemSerializer,
# )

# logger = logging.getLogger("apps.cart")


# # ─── Helpers ──────────────────────────────────────────────────────────────────

# def _get_cart_with_items(user) -> Cart:
#     """
#     Fetch the user's cart with all related data in a single query.

#     Uses prefetch_related to load items → products → images
#     so CartSerializer and its nested CartItemSerializer
#     produce zero additional queries.

#     Args:
#         user: The authenticated user whose cart to fetch.

#     Returns:
#         Cart instance with prefetched items, products, and images.

#     Raises:
#         Cart.DoesNotExist: If cart is missing — indicates signal failure.
#     """
#     return (
#         Cart.objects
#         .prefetch_related(
#             "items__product__images",
#         )
#         .get(user=user)
#     )


# # ─── Cart Detail ──────────────────────────────────────────────────────────────

# class CartDetailAPIView(BaseAPIView):
#     """
#     GET /api/cart/

#     Return the authenticated user's cart with all items and totals.

#     Why not 404 on missing cart:
#         Cart is created by signal on user creation. A missing cart
#         indicates a server-side signal failure — not a client error.
#         We log at ERROR and return 500 instead of 404.

#     Permissions:
#         IsAuthenticated.

#     Success (200):
#         Full cart with items, totals, and product details.
#     """

#     permission_classes = [IsAuthenticated]

#     def get(self, request: Request) -> Response:
#         log_context = {
#             "request_id": request.id,
#             "user_id": request.user.id,
#         }

#         try:
#             cart = _get_cart_with_items(request.user)
#         except Cart.DoesNotExist:
#             logger.error(
#                 "Cart not found for authenticated user — "
#                 "post_save signal may have failed on account creation.",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("Cart not found. Please contact support."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )
#         except Exception:
#             logger.exception(
#                 "Unexpected error fetching cart",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("An unexpected error occurred. Please try again later."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         serializer = CartSerializer(cart, context={"request": request})
#         return self.success_response(
#             data=serializer.data,
#             message=_("Cart retrieved successfully."),
#         )


# # ─── Add To Cart ──────────────────────────────────────────────────────────────

# class AddToCartAPIView(BaseAPIView):
#     """
#     POST /api/cart/items/

#     Add a product to the cart, or increase quantity if already present.

#     Upsert logic:
#         - If product not in cart → create new CartItem.
#         - If product already in cart → add requested quantity to existing.

#     Concurrency:
#         select_for_update() on CartItem prevents race conditions where
#         two concurrent requests could both read quantity=2 and both
#         try to write quantity=3, resulting in quantity=3 instead of 4.

#     Permissions:
#         IsAuthenticated.

#     Success (201):
#         Full updated cart returned.

#     Errors:
#         400 — Product unavailable, quantity exceeds stock.
#         500 — Unexpected DB failure.
#     """

#     permission_classes = [IsAuthenticated]

#     def post(self, request: Request) -> Response:
#         log_context = {
#             "request_id": request.id,
#             "user_id": request.user.id,
#         }

#         serializer = AddToCartSerializer(data=request.data)
#         if not serializer.is_valid():
#             logger.warning(
#                 "Add to cart validation failed",
#                 extra={**log_context, "errors": serializer.errors},
#             )
#             return self.error_response(
#                 message=_("Could not add item to cart."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         # Product already fetched and validated in serializer.validate()
#         # No additional DB query needed here
#         product = serializer.validated_data["product"]
#         quantity = serializer.validated_data["quantity"]


#         try:
#             cart = Cart.objects.get(user=request.user)
#         except Cart.DoesNotExist:
#             logger.error(
#                 "Cart not found for authenticated user — "
#                 "post_save signal may have failed on account creation.",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("Cart not found. Please contact support."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         try:
#             with transaction.atomic():
#                 # cart, _cart_created= Cart.objects.get_or_create(user=request.user)

#                 item, created = (
#                     CartItem.objects
#                     .select_for_update()
#                     .get_or_create(
#                         cart=cart,
#                         product=product,
#                         defaults={"quantity": quantity},
#                     )
#                 )

#                 if not created:
#                     new_quantity = item.quantity + quantity
#                     if new_quantity > product.stock:
#                         return self.error_response(
#                             message=_("Could not update cart item."),
#                             errors={
#                                 "quantity": _(
#                                     "Only %(stock)d unit(s) of %(name)s in stock."
#                                 ) % {
#                                     "stock": product.stock,
#                                     "name": product.name,
#                                 }
#                             },
#                             status_code=status.HTTP_400_BAD_REQUEST,
#                         )
#                     # Use update() to skip full_clean() stock recheck —
#                     # we already validated stock above
#                     CartItem.objects.filter(pk=item.pk).update(
#                         quantity=new_quantity
#                     )

#         except Exception:
#             logger.exception(
#                 "Unexpected error adding item to cart",
#                 extra={**log_context, "product_id": product.id},
#             )
#             return self.error_response(
#                 message=_("An unexpected error occurred. Please try again later."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         logger.info(
#             "Cart item %s",
#             "created" if created else "updated",
#             extra={**log_context, "product_id": product.id, "quantity": quantity},
#         )

#         # Re-fetch with full prefetch chain for serialization
#         cart = _get_cart_with_items(request.user)
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message=_("Item added to cart successfully."),
#             status_code=status.HTTP_201_CREATED,
#         )


# # ─── Update / Remove Cart Item ────────────────────────────────────────────────

# class UpdateCartItemAPIView(BaseAPIView):
#     """
#     PATCH  /api/cart/items/<item_id>/ → update quantity
#     DELETE /api/cart/items/<item_id>/ → remove item

#     Why PATCH not PUT:
#         Only quantity is updated — partial update semantics.

#     Ownership check:
#         cart__user=request.user in the filter ensures users can
#         only modify their own cart items — no extra permission check needed.

#     Permissions:
#         IsAuthenticated.

#     Success (200):
#         Full updated cart returned after modification.

#     Errors:
#         400 — Quantity exceeds stock.
#         404 — Item not found or not owned by requesting user.
#         500 — Unexpected DB failure.
#     """

#     permission_classes = [IsAuthenticated]

#     def _get_item(self, item_id: int, user) -> CartItem | None:
#         """
#         Fetch cart item with product pre-loaded, scoped to the requesting user.

#         Args:
#             item_id: PK of the CartItem.
#             user:    Requesting user — ownership enforced via cart__user.

#         Returns:
#             CartItem with select_related product, or None if not found.
#         """
#         return (
#             CartItem.objects
#             .select_related("product", "cart")
#             .filter(id=item_id, cart__user=user)
#             .first()
#         )

#     def patch(self, request: Request, item_id: int) -> Response:
#         log_context = {
#             "request_id": request.id,
#             "user_id": request.user.id,
#             "item_id": item_id,
#         }

#         item = self._get_item(item_id, request.user)
#         if not item:
#             logger.warning(
#                 "Cart item not found or not owned by user",
#                 extra=log_context,
#             )
#             return self.not_found_response(
#                 message=_("Cart item not found.")
#             )

#         serializer = UpdateCartItemSerializer(data=request.data)
#         if not serializer.is_valid():
#             logger.warning(
#                 "Update cart item validation failed",
#                 extra={**log_context, "errors": serializer.errors},
#             )
#             return self.error_response(
#                 message=_("Could not update cart item."),
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         quantity = serializer.validated_data["quantity"]
#           # ── quantity=0 → auto-delete the item ────────────────────────────────
#         # Handles the case where frontend sends 0 when user clicks −
#         # on an item with quantity=1. Better UX than returning a 400 error.
#         if quantity == 0:
#             try:
#                 product_id = item.product_id
#                 item.delete()
#             except Exception:
#                 logger.exception(
#                     "Unexpected error auto-deleting cart item on quantity=0",
#                     extra=log_context,
#                 )
#                 return self.error_response(
#                     message=_("An unexpected error occurred. Please try again later."),
#                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#                 )

#             logger.info(
#                 "Cart item auto-deleted — quantity set to 0",
#                 extra={**log_context, "product_id": product_id},
#             )

#             cart = _get_cart_with_items(request.user)
#             return self.success_response(
#                 data=CartSerializer(cart, context={"request": request}).data,
#                 message=_("Item removed from cart."),
#             )


#         if quantity > item.product.stock:
#             return self.error_response(
#                 message=_("Could not update cart item."),
#                 errors={
#                     "quantity": _(
#                         "Only %(stock)d unit(s) of %(name)s in stock."
#                     ) % {
#                         "stock": item.product.stock,
#                         "name": item.product.name,
#                     }
#                 },
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         try:
#             # Use update() to skip full_clean() stock recheck —
#             # we already validated stock above
#             CartItem.objects.filter(pk=item.pk).update(quantity=quantity)
#         except Exception:
#             logger.exception(
#                 "Unexpected error updating cart item",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("An unexpected error occurred. Please try again later."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         logger.info(
#             "Cart item quantity updated",
#             extra={**log_context, "product_id": item.product_id, "quantity": quantity},
#         )

#         cart = _get_cart_with_items(request.user)
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message=_("Cart item updated successfully."),
#         )


#     def delete(self, request: Request, item_id: int) -> Response:
#         log_context = {
#             "request_id": request.id,
#             "user_id": request.user.id,
#             "item_id": item_id,
#         }

#         item = self._get_item(item_id, request.user)
#         if not item:
#             logger.warning(
#                 "Cart item not found or not owned by user on delete",
#                 extra=log_context,
#             )
#             return self.not_found_response(
#                 message=_("Cart item not found.")
#             )

#         product_id = item.product_id

#         try:
#             item.delete()
#         except Exception:
#             logger.exception(
#                 "Unexpected error deleting cart item",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("An unexpected error occurred. Please try again later."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         logger.info(
#             "Cart item removed",
#             extra={**log_context, "product_id": product_id},
#         )

#         cart = _get_cart_with_items(request.user)
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message=_("Item removed from cart successfully."),
#         )


# # ─── Clear Cart ───────────────────────────────────────────────────────────────

# class ClearCartAPIView(BaseAPIView):
#     """
#     DELETE /api/cart/clear/

#     Remove all items from the authenticated user's cart.

#     Why not 404 on missing cart:
#         Same reasoning as CartDetailAPIView — missing cart is a
#         server-side signal failure, not a client error.

#     Permissions:
#         IsAuthenticated.

#     Success (200):
#         Empty cart returned.
#     """

#     permission_classes = [IsAuthenticated]

#     def delete(self, request: Request) -> Response:
#         log_context = {
#             "request_id": request.id,
#             "user_id": request.user.id,
#         }

#         try:
#             cart = Cart.objects.get(user=request.user)
#         except Cart.DoesNotExist:
#             logger.error(
#                 "Cart not found on clear — signal may have failed.",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("Cart not found. Please contact support."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         try:
#             items_count,  _deleted_map = cart.items.all().delete()
#         except Exception:
#             logger.exception(
#                 "Unexpected error clearing cart",
#                 extra=log_context,
#             )
#             return self.error_response(
#                 message=_("An unexpected error occurred. Please try again later."),
#                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             )

#         logger.info(
#             "Cart cleared",
#             extra={**log_context, "items_removed": items_count},
#         )

#         cart = _get_cart_with_items(request.user)
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message=_("Cart cleared successfully."),
#         )
