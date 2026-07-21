# apps/orders/urls.py
from __future__ import annotations

"""
Order app — URL routing.

Route inventory:
    POST /api/orders/checkout/                   — CheckoutAPIView
    GET  /api/orders/                            — OrderListAPIView
    GET  /api/orders/<order_number>/             — OrderDetailAPIView
    POST /api/orders/<order_number>/cancel/      — OrderCancelAPIView
"""
from apps.logistics.views import OrderTrackingAPIView
from django.urls import path

from .views import (
    CheckoutAPIView,
    OrderCancelAPIView,
    OrderDetailAPIView,
    OrderListAPIView,
)

app_name = "orders"

urlpatterns = [
    path("checkout/", CheckoutAPIView.as_view(), name="checkout"),
    path("", OrderListAPIView.as_view(), name="order-list"),
    path("<str:order_number>/", OrderDetailAPIView.as_view(), name="order-detail"),
    path("<str:order_number>/cancel/", OrderCancelAPIView.as_view(), name="order-cancel"),
    path("<str:order_number>/tracking/", OrderTrackingAPIView.as_view(), name="order-tracking"),
]