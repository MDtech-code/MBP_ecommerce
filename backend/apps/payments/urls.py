# apps/payments/urls.py
from __future__ import annotations

from django.urls import path

from apps.payments.views import (
    EasypaisaWebhookView,
    JazzCashWebhookView,
    PaymentInitiateAPIView,
    PaymentStatusAPIView,
    SafepayWebhookView,
)

app_name = "payments"

urlpatterns = [
    path(
        "initiate/",
        PaymentInitiateAPIView.as_view(),
        name="payment-initiate",
    ),
    path(
        "status/<str:order_number>/",
        PaymentStatusAPIView.as_view(),
        name="payment-status",
    ),
    path(
        "webhooks/jazzcash/",
        JazzCashWebhookView.as_view(),
        name="webhook-jazzcash",
    ),
    path(
        "webhooks/easypaisa/",
        EasypaisaWebhookView.as_view(),
        name="webhook-easypaisa",
    ),
    path(
        "webhooks/safepay/",
        SafepayWebhookView.as_view(),
        name="webhook-safepay",
    ),
]