# apps/wishlist/urls.py
from __future__ import annotations

from django.urls import path

from apps.wishlist.views import (
    WishlistAddAPIView,
    WishlistListAPIView,
    WishlistRemoveAPIView,
)

app_name = "wishlist"

urlpatterns = [
    path(
        "",
        WishlistListAPIView.as_view(),
        name="wishlist-list",
    ),
    path(
        "add/",
        WishlistAddAPIView.as_view(),
        name="wishlist-add",
    ),
    path(
        "<int:product_id>/",
        WishlistRemoveAPIView.as_view(),
        name="wishlist-remove",
    ),
]