from __future__ import annotations

from django.urls import path

from .views import (
    CartDetailAPIView,
    AddToCartAPIView,
    UpdateCartItemAPIView,
    ClearCartAPIView,
    CouponApplyAPIView,
    CouponRemoveAPIView,
)

app_name = "cart"

urlpatterns = [
    path("", CartDetailAPIView.as_view(), name="cart-detail"),
    path("items/", AddToCartAPIView.as_view(), name="cart-add-item"),
    path("items/<int:item_id>/", UpdateCartItemAPIView.as_view(), name="cart-update-item"),
    path("clear/", ClearCartAPIView.as_view(), name="cart-clear"),
     # Coupon
    path("coupon/", CouponApplyAPIView.as_view(), name="cart-coupon-apply"),
    path("coupon/remove/", CouponRemoveAPIView.as_view(), name="cart-coupon-remove"),
]