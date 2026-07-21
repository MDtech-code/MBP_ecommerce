# apps/logistics/urls.py
from __future__ import annotations

"""
Logistics app — URL routing.

Admin routes:
    GET  POST /api/logistics/shipments/
    GET       /api/logistics/shipments/<tracking_number>/
    PATCH     /api/logistics/shipments/<tracking_number>/status/

Customer route (registered in orders urls):
    GET       /api/orders/<order_number>/tracking/
"""

from django.urls import path

from .views import (
    ShipmentDetailAPIView,
    ShipmentListCreateAPIView,
    ShipmentStatusUpdateAPIView,
)

app_name = "logistics"

urlpatterns = [
    path(
        "shipments/",
        ShipmentListCreateAPIView.as_view(),
        name="shipment-list-create",
    ),
    path(
        "shipments/<str:tracking_number>/",
        ShipmentDetailAPIView.as_view(),
        name="shipment-detail",
    ),
    path(
        "shipments/<str:tracking_number>/status/",
        ShipmentStatusUpdateAPIView.as_view(),
        name="shipment-status-update",
    ),
]