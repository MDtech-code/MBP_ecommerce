# apps/cart/tests/urls.py
"""
Test URL configuration for cart app.

Includes cart URLs under /api/cart/ prefix — matches production routing.
Used by @pytest.mark.urls or included in test settings.
"""
from __future__ import annotations

from django.urls import include, path

urlpatterns = [
    path("api/cart/", include("apps.cart.urls", namespace="cart")),
]