# apps/logistics/urls.py
from __future__ import annotations
from apps.logistics.views import (
    
    # Phase 2 webhook views
    PostExWebhookView,
    TCSWebhookView,
    LeopardsWebhookView,
)
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



app_name = "logistics"

urlpatterns = [
    # ── Courier webhooks ──────────────────────────────────────────────────
    # These URLs are configured in courier dashboards.
    # No authentication — CSRF exempt — HMAC verified async in Celery.
    path(
        "webhooks/postex/",
        PostExWebhookView.as_view(),
        name="webhook-postex",
    ),
    path(
        "webhooks/tcs/",
        TCSWebhookView.as_view(),
        name="webhook-tcs",
    ),
    path(
        "webhooks/leopards/",
        LeopardsWebhookView.as_view(),
        name="webhook-leopards",
    ),
]