# apps/wishlist/views.py
from __future__ import annotations

"""
Wishlist views — HTTP layer for the wishlist app.

Endpoints:
    GET    /api/wishlist/                WishlistListAPIView
    POST   /api/wishlist/add/            WishlistAddAPIView
    DELETE /api/wishlist/<product_id>/   WishlistRemoveAPIView

Design rules:
    - All views inherit from BaseAPIView.
    - Views call service or selector — never query models directly.
    - DomainError raised in service propagates to custom_exception_handler.
    - Paginated list uses get_pagination_params() + build_pagination_meta().
    - Ownership enforced in selectors — customers only see their own items.

Permission:
    All endpoints require IsAuthenticated.

Dependency direction:
    models → selectors → services → serializers → views
"""

import logging

from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.api.views import BaseAPIView
from apps.core.exceptions import DomainError
from apps.core.pagination import build_pagination_meta, get_pagination_params
from apps.wishlist.selectors.wishlist_selectors import (
    get_wishlist_item,
    get_wishlist_items,
)
from apps.wishlist.serializers import WishlistAddSerializer, WishlistItemSerializer
from apps.wishlist.services.wishlist_service import WishlistService

logger = logging.getLogger("apps.wishlist")


class WishlistListAPIView(BaseAPIView):
    """
    GET /api/wishlist/

    Returns a paginated list of the authenticated user's wishlist items.

    Each item includes product summary (name, price, slug, stock status)
    so the frontend can render the wishlist page without additional calls.
    Ordered by most recently added first.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        params = get_pagination_params(request)
        if not params.is_valid:
            return self.error_response(
                message="Invalid pagination parameters.",
                status_code=400,
            )

        queryset = get_wishlist_items(request.user)
        total    = queryset.count()

        offset  = (params.page - 1) * params.page_size
        page_qs = queryset[offset : offset + params.page_size]

        serializer = WishlistItemSerializer(
            page_qs,
            many=True,
            context={"request": request},
        )

        meta = build_pagination_meta(
            params.page,
            params.page_size,
            total,
        )

        logger.info(
            "WishlistListAPIView.get: listed | "
            "user=%s page=%s total=%s",
            request.user.pk,
            params.page,
            total,
        )

        return self.list_response(
            data=serializer.data,
            message="Wishlist retrieved successfully.",
            meta=meta,
        )


class WishlistAddAPIView(BaseAPIView):
    """
    POST /api/wishlist/add/

    Adds a product to the authenticated user's wishlist.

    Returns 409 if the product is already in the wishlist.
    Returns 400 if the product_id does not exist.
    Returns 201 with the created WishlistItem on success.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = WishlistAddSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Could not add item to wishlist.",
                errors=serializer.errors,
                status_code=400,
            )

        product_id: int = serializer.validated_data["product_id"]

        wishlist_item = WishlistService.add_item(
            user=request.user,
            product_id=product_id,
        )

        logger.info(
            "WishlistAddAPIView.post: item added | "
            "user=%s product_id=%s",
            request.user.pk,
            product_id,
        )

        return self.created_response(
            data=WishlistItemSerializer(
                wishlist_item,
                context={"request": request},
            ).data,
            message="Product added to wishlist.",
        )


class WishlistRemoveAPIView(BaseAPIView):
    """
    DELETE /api/wishlist/<product_id>/

    Removes a product from the authenticated user's wishlist.

    Returns 400 if the product is not in the user's wishlist.
    Ownership is enforced in the selector — a valid item belonging
    to another user returns None → 400, preventing enumeration.
    Returns 200 with confirmation message on success.
    """

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, product_id: int) -> Response:
        WishlistService.remove_item(
            user=request.user,
            product_id=product_id,
        )

        logger.info(
            "WishlistRemoveAPIView.delete: item removed | "
            "user=%s product_id=%s",
            request.user.pk,
            product_id,
        )

        return self.success_response(
            data=None,
            message="Product removed from wishlist.",
        )