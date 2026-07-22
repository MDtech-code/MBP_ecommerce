# apps/returns/urls.py
from __future__ import annotations

from django.urls import path

from apps.returns.views import (
    ReturnCreateAPIView,
    ReturnDetailAPIView,
    ReturnListAPIView,
)

app_name = "returns"

urlpatterns = [
    path(
        "",
        ReturnCreateAPIView.as_view(),
        name="return-create",
    ),
    path(
        "list/",
        ReturnListAPIView.as_view(),
        name="return-list",
    ),
    path(
        "<int:return_id>/",
        ReturnDetailAPIView.as_view(),
        name="return-detail",
    ),
]