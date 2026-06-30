from __future__ import annotations

import logging

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated

from apps.core.api.views import BaseAPIView
from apps.products.models import Product
from .models import Cart, CartItem
from .serializers import (
    CartSerializer,
    AddToCartSerializer,
    UpdateCartItemSerializer,
)

logger = logging.getLogger("apps.cart")


class CartDetailAPIView(BaseAPIView):
    """
    GET /api/cart/
    Return the authenticated user's cart with all items and totals.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_object_or_404(
            Cart.objects.prefetch_related("items__product__images"),
            user=request.user,
        )
        serializer = CartSerializer(cart, context={"request": request})
        return self.success_response(
            data=serializer.data,
            message="Cart retrieved successfully",
        )


class AddToCartAPIView(BaseAPIView):
    """
    POST /api/cart/items/
    Add a product to cart, or increase quantity if it's already present.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AddToCartSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Could not add item to cart",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        product_id = serializer.validated_data["product_id"]
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
            cart, _created = Cart.objects.get_or_create(user=request.user)
            item, created = CartItem.objects.select_for_update().get_or_create(
                cart=cart,
                product_id=product_id,
                defaults={"quantity": quantity},
            )

            if not created:
                new_quantity = item.quantity + quantity
                product = Product.objects.get(id=product_id)
                if new_quantity > product.stock:
                    return self.error_response(
                        message="Could not update cart item",
                        errors={
                            "quantity": (
                                f"Only {product.stock} unit(s) of "
                                f"{product.name} in stock."
                            )
                        },
                        status_code=status.HTTP_400_BAD_REQUEST,
                    )
                item.quantity = new_quantity
                item.save()

        logger.info(
            "Cart item %s for product_id=%s, user=%s",
            "added" if created else "updated",
            product_id, request.user.email,
        )

        cart.refresh_from_db()
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message="Item added to cart successfully",
            status_code=status.HTTP_201_CREATED,
        )


class UpdateCartItemAPIView(BaseAPIView):
    """
    PUT    /api/cart/items/<id>/   → update quantity
    DELETE /api/cart/items/<id>/   → remove item
    """
    permission_classes = [IsAuthenticated]

    def put(self, request, item_id: int):
        item = get_object_or_404(
            CartItem, id=item_id, cart__user=request.user,
        )
        serializer = UpdateCartItemSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Could not update cart item",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        quantity = serializer.validated_data["quantity"]
        if quantity > item.product.stock:
            return self.error_response(
                message="Could not update cart item",
                errors={
                    "quantity": (
                        f"Only {item.product.stock} unit(s) of "
                        f"{item.product.name} in stock."
                    )
                },
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        item.quantity = quantity
        item.save()

        logger.info(
            "Cart item updated: product=%s, quantity=%d, user=%s",
            item.product.name, quantity, request.user.email,
        )

        cart = item.cart
        cart.refresh_from_db()
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message="Cart item updated successfully",
        )

    def delete(self, request, item_id: int):
        item = get_object_or_404(
            CartItem, id=item_id, cart__user=request.user,
        )
        product_name = item.product.name
        cart = item.cart
        item.delete()

        logger.info(
            "Cart item removed: product=%s, user=%s",
            product_name, request.user.email,
        )

        cart.refresh_from_db()
        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message="Item removed from cart successfully",
        )


class ClearCartAPIView(BaseAPIView):
    """
    DELETE /api/cart/clear/
    Remove all items from the authenticated user's cart.
    """
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        cart = get_object_or_404(Cart, user=request.user)
        items_count = cart.items.count()
        cart.items.all().delete()

        logger.info(
            "Cart cleared: %d item(s) removed, user=%s",
            items_count, request.user.email,
        )

        return self.success_response(
            data=CartSerializer(cart, context={"request": request}).data,
            message="Cart cleared successfully",
        )