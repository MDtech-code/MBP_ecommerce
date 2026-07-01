from __future__ import annotations

from django.urls import path

from .views import (
    CategoryListAPIView,
    BrandListAPIView,
    BikeModelListAPIView,
    ProductListAPIView,
    ProductDetailAPIView,
    ProductImageUploadAPIView,
)

app_name = "products"

urlpatterns = [
    # ─── Filters / Lookups ─────────────────────────────
    path("categories/", CategoryListAPIView.as_view(), name="category-list"),
    path("brands/", BrandListAPIView.as_view(), name="brand-list"),
    path("bike-models/", BikeModelListAPIView.as_view(), name="bike-model-list"),

    # ─── Product CRUD ──────────────────────────────────
    path("", ProductListAPIView.as_view(), name="product-list"),
    path("<slug:slug>/", ProductDetailAPIView.as_view(), name="product-detail"),

    # ─── Product Images ────────────────────────────────
    path(
        "<slug:slug>/images/",
        ProductImageUploadAPIView.as_view(),
        name="product-image-upload",
    ),
    path(
        "<slug:slug>/images/<int:image_id>/",
        ProductImageUploadAPIView.as_view(),
        name="product-image-delete",
    ),
]