# apps/cart/views.py
from __future__ import annotations

import logging

from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.api.views import BaseAPIView

from .models import Cart, CartItem
from .serializers import (
    AddToCartSerializer,
    CartSerializer,
    UpdateCartItemSerializer,
)

logger = logging.getLogger("apps.cart")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_cart_with_items(user) -> Cart:
    """
    Fetch the user's cart with all related data in a single query.

    Uses prefetch_related to load items → products → images
    so CartSerializer and its nested CartItemSerializer
    produce zero additional queries.

    Args:
        user: The authenticated user whose cart to fetch.

    Returns:
        Cart instance with prefetched items, products, and images.

    Raises:
        Cart.DoesNotExist: If cart is missing — indicates signal failure.
    """
    return (
        Cart.objects
        .prefetch_related(
            "items__product__images",
        )
        .get(user=user)
    )


# ─── Cart Detail ──────────────────────────────────────────────────────────────

class CartDetailAPIView(BaseAPIView):
    """
    GET /api/cart/

    Return the authenticated user's cart with all items and totals.

    Why not 404 on missing cart:
        Cart is created by signal on user creation. A missing cart
        indicates a server-side signal failure — not a client error.
        We log at ERROR and return 500 instead of 404.

    Permissions:
        IsAuthenticated.

    Success (200):
        Full cart with items, totals, and product details.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        try:
            cart = _get_cart_with_items(request.user)
        except Cart.DoesNotExist:
            logger.error(
                "Cart not found for authenticated user — "
                "post_save signal may have failed on account creation.",
                extra=log_context,
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except Exception:
            logger.exception(
                "Unexpected error fetching cart",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = CartSerializer(cart, context={"request": request})
        return self.success_response(
            data=serializer.data,
            message=_("Cart retrieved successfully."),
        )


# ─── Add To Cart ──────────────────────────────────────────────────────────────

class AddToCartAPIView(BaseAPIView):
    """
    POST /api/cart/items/

    Add a product to the cart, or increase quantity if already present.

    Upsert logic:
        - If product not in cart → create new CartItem.
        - If product already in cart → add requested quantity to existing.

    Concurrency:
        select_for_update() on CartItem prevents race conditions where
        two concurrent requests could both read quantity=2 and both
        try to write quantity=3, resulting in quantity=3 instead of 4.

    Permissions:
        IsAuthenticated.

    Success (201):
        Full updated cart returned.

    Errors:
        400 — Product unavailable, quantity exceeds stock.
        500 — Unexpected DB failure.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Add to cart validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Could not add item to cart."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Product already fetched and validated in serializer.validate()
        # No additional DB query needed here
        product = serializer.validated_data["product"]
        quantity = serializer.validated_data["quantity"]


        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            logger.error(
                "Cart not found for authenticated user — "
                "post_save signal may have failed on account creation.",
                extra=log_context,
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            with transaction.atomic():
                # cart, _cart_created= Cart.objects.get_or_create(user=request.user)

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
                        return self.error_response(
                            message=_("Could not update cart item."),
                            errors={
                                "quantity": _(
                                    "Only %(stock)d unit(s) of %(name)s in stock."
                                ) % {
                                    "stock": product.stock,
                                    "name": product.name,
                                }
                            },
                            status_code=status.HTTP_400_BAD_REQUEST,
                        )
                    # Use update() to skip full_clean() stock recheck —
                    # we already validated stock above
                    CartItem.objects.filter(pk=item.pk).update(
                        quantity=new_quantity
                    )

        except Exception:
            logger.exception(
                "Unexpected error adding item to cart",
                extra={**log_context, "product_id": product.id},
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Cart item %s",
            "created" if created else "updated",
            extra={**log_context, "product_id": product.id, "quantity": quantity},
        )

        # Re-fetch with full prefetch chain for serialization
        cart = _get_cart_with_items(request.user)
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Item added to cart successfully."),
            status_code=status.HTTP_201_CREATED,
        )


# ─── Update / Remove Cart Item ────────────────────────────────────────────────

class UpdateCartItemAPIView(BaseAPIView):
    """
    PATCH  /api/cart/items/<item_id>/ → update quantity
    DELETE /api/cart/items/<item_id>/ → remove item

    Why PATCH not PUT:
        Only quantity is updated — partial update semantics.

    Ownership check:
        cart__user=request.user in the filter ensures users can
        only modify their own cart items — no extra permission check needed.

    Permissions:
        IsAuthenticated.

    Success (200):
        Full updated cart returned after modification.

    Errors:
        400 — Quantity exceeds stock.
        404 — Item not found or not owned by requesting user.
        500 — Unexpected DB failure.
    """

    permission_classes = [IsAuthenticated]

    def _get_item(self, item_id: int, user) -> CartItem | None:
        """
        Fetch cart item with product pre-loaded, scoped to the requesting user.

        Args:
            item_id: PK of the CartItem.
            user:    Requesting user — ownership enforced via cart__user.

        Returns:
            CartItem with select_related product, or None if not found.
        """
        return (
            CartItem.objects
            .select_related("product", "cart")
            .filter(id=item_id, cart__user=user)
            .first()
        )

    def patch(self, request: Request, item_id: int) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
            "item_id": item_id,
        }

        item = self._get_item(item_id, request.user)
        if not item:
            logger.warning(
                "Cart item not found or not owned by user",
                extra=log_context,
            )
            return self.not_found_response(
                message=_("Cart item not found.")
            )

        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(
                "Update cart item validation failed",
                extra={**log_context, "errors": serializer.errors},
            )
            return self.error_response(
                message=_("Could not update cart item."),
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        quantity = serializer.validated_data["quantity"]
          # ── quantity=0 → auto-delete the item ────────────────────────────────
        # Handles the case where frontend sends 0 when user clicks −
        # on an item with quantity=1. Better UX than returning a 400 error.
        if quantity == 0:
            try:
                product_id = item.product_id
                item.delete()
            except Exception:
                logger.exception(
                    "Unexpected error auto-deleting cart item on quantity=0",
                    extra=log_context,
                )
                return self.error_response(
                    message=_("An unexpected error occurred. Please try again later."),
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            logger.info(
                "Cart item auto-deleted — quantity set to 0",
                extra={**log_context, "product_id": product_id},
            )

            cart = _get_cart_with_items(request.user)
            return self.success_response(
                data=CartSerializer(cart, context={"request": request}).data,
                message=_("Item removed from cart."),
            )


        if quantity > item.product.stock:
            return self.error_response(
                message=_("Could not update cart item."),
                errors={
                    "quantity": _(
                        "Only %(stock)d unit(s) of %(name)s in stock."
                    ) % {
                        "stock": item.product.stock,
                        "name": item.product.name,
                    }
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Use update() to skip full_clean() stock recheck —
            # we already validated stock above
            CartItem.objects.filter(pk=item.pk).update(quantity=quantity)
        except Exception:
            logger.exception(
                "Unexpected error updating cart item",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Cart item quantity updated",
            extra={**log_context, "product_id": item.product_id, "quantity": quantity},
        )

        cart = _get_cart_with_items(request.user)
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Cart item updated successfully."),
        )


    def delete(self, request: Request, item_id: int) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
            "item_id": item_id,
        }

        item = self._get_item(item_id, request.user)
        if not item:
            logger.warning(
                "Cart item not found or not owned by user on delete",
                extra=log_context,
            )
            return self.not_found_response(
                message=_("Cart item not found.")
            )

        product_id = item.product_id

        try:
            item.delete()
        except Exception:
            logger.exception(
                "Unexpected error deleting cart item",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Cart item removed",
            extra={**log_context, "product_id": product_id},
        )

        cart = _get_cart_with_items(request.user)
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Item removed from cart successfully."),
        )


# ─── Clear Cart ───────────────────────────────────────────────────────────────

class ClearCartAPIView(BaseAPIView):
    """
    DELETE /api/cart/clear/

    Remove all items from the authenticated user's cart.

    Why not 404 on missing cart:
        Same reasoning as CartDetailAPIView — missing cart is a
        server-side signal failure, not a client error.

    Permissions:
        IsAuthenticated.

    Success (200):
        Empty cart returned.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request) -> Response:
        log_context = {
            "request_id": request.id,
            "user_id": request.user.id,
        }

        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            logger.error(
                "Cart not found on clear — signal may have failed.",
                extra=log_context,
            )
            return self.error_response(
                message=_("Cart not found. Please contact support."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            items_count,  _deleted_map = cart.items.all().delete()
        except Exception:
            logger.exception(
                "Unexpected error clearing cart",
                extra=log_context,
            )
            return self.error_response(
                message=_("An unexpected error occurred. Please try again later."),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        logger.info(
            "Cart cleared",
            extra={**log_context, "items_removed": items_count},
        )

        cart = _get_cart_with_items(request.user)
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message=_("Cart cleared successfully."),
        )
# from __future__ import annotations

# import logging

# from django.db import transaction
# from django.shortcuts import get_object_or_404
# from rest_framework import status
# from rest_framework.permissions import IsAuthenticated

# from apps.core.api.views import BaseAPIView
# from apps.products.models import Product
# from .models import Cart, CartItem
# from .serializers import (
#     CartSerializer,
#     AddToCartSerializer,
#     UpdateCartItemSerializer,
# )

# logger = logging.getLogger("apps.cart")


# class CartDetailAPIView(BaseAPIView):
#     """
#     GET /api/cart/
#     Return the authenticated user's cart with all items and totals.
#     """
#     permission_classes = [IsAuthenticated]

#     def get(self, request):
#         cart = get_object_or_404(
#             Cart.objects.prefetch_related("items__product__images"),
#             user=request.user,
#         )
#         serializer = CartSerializer(cart, context={"request": request})
#         return self.success_response(
#             data=serializer.data,
#             message="Cart retrieved successfully",
#         )


# class AddToCartAPIView(BaseAPIView):
#     """
#     POST /api/cart/items/
#     Add a product to cart, or increase quantity if it's already present.
#     """
#     permission_classes = [IsAuthenticated]

#     def post(self, request):
#         serializer = AddToCartSerializer(data=request.data)
#         if not serializer.is_valid():
#             return self.error_response(
#                 message="Could not add item to cart",
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         product_id = serializer.validated_data["product_id"]
#         quantity = serializer.validated_data["quantity"]

#         with transaction.atomic():
#             cart, _created = Cart.objects.get_or_create(user=request.user)
#             item, created = CartItem.objects.select_for_update().get_or_create(
#                 cart=cart,
#                 product_id=product_id,
#                 defaults={"quantity": quantity},
#             )

#             if not created:
#                 new_quantity = item.quantity + quantity
#                 product = Product.objects.get(id=product_id)
#                 if new_quantity > product.stock:
#                     return self.error_response(
#                         message="Could not update cart item",
#                         errors={
#                             "quantity": (
#                                 f"Only {product.stock} unit(s) of "
#                                 f"{product.name} in stock."
#                             )
#                         },
#                         status_code=status.HTTP_400_BAD_REQUEST,
#                     )
#                 item.quantity = new_quantity
#                 item.save()

#         logger.info(
#             "Cart item %s for product_id=%s, user=%s",
#             "added" if created else "updated",
#             product_id, request.user.email,
#         )

#         cart.refresh_from_db()
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message="Item added to cart successfully",
#             status_code=status.HTTP_201_CREATED,
#         )


# class UpdateCartItemAPIView(BaseAPIView):
#     """
#     PUT    /api/cart/items/<id>/   → update quantity
#     DELETE /api/cart/items/<id>/   → remove item
#     """
#     permission_classes = [IsAuthenticated]

#     def put(self, request, item_id: int):
#         item = get_object_or_404(
#             CartItem, id=item_id, cart__user=request.user,
#         )
#         serializer = UpdateCartItemSerializer(data=request.data)
#         if not serializer.is_valid():
#             return self.error_response(
#                 message="Could not update cart item",
#                 errors=serializer.errors,
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         quantity = serializer.validated_data["quantity"]
#         if quantity > item.product.stock:
#             return self.error_response(
#                 message="Could not update cart item",
#                 errors={
#                     "quantity": (
#                         f"Only {item.product.stock} unit(s) of "
#                         f"{item.product.name} in stock."
#                     )
#                 },
#                 status_code=status.HTTP_400_BAD_REQUEST,
#             )

#         item.quantity = quantity
#         item.save()

#         logger.info(
#             "Cart item updated: product=%s, quantity=%d, user=%s",
#             item.product.name, quantity, request.user.email,
#         )

#         cart = item.cart
#         cart.refresh_from_db()
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message="Cart item updated successfully",
#         )

#     def delete(self, request, item_id: int):
#         item = get_object_or_404(
#             CartItem, id=item_id, cart__user=request.user,
#         )
#         product_name = item.product.name
#         cart = item.cart
#         item.delete()

#         logger.info(
#             "Cart item removed: product=%s, user=%s",
#             product_name, request.user.email,
#         )

#         cart.refresh_from_db()
#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message="Item removed from cart successfully",
#         )


# class ClearCartAPIView(BaseAPIView):
#     """
#     DELETE /api/cart/clear/
#     Remove all items from the authenticated user's cart.
#     """
#     permission_classes = [IsAuthenticated]

#     def delete(self, request):
#         cart = get_object_or_404(Cart, user=request.user)
#         items_count = cart.items.count()
#         cart.items.all().delete()

#         logger.info(
#             "Cart cleared: %d item(s) removed, user=%s",
#             items_count, request.user.email,
#         )

#         return self.success_response(
#             data=CartSerializer(cart, context={"request": request}).data,
#             message="Cart cleared successfully",
#         )