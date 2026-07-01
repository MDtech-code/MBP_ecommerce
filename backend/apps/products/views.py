from __future__ import annotations

import logging
import time
from typing import Any
from rest_framework.request import Request
from django.conf import settings
from django.db.models import Count
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet, Q
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.core.api.views import BaseAPIView
from apps.core.permissions import IsAdminOrReadOnly
from apps.core.cache import two_level_cache
from apps.core.pagination import get_pagination_params, build_pagination_meta
from .models import Category, Brand, BikeModel, Product, ProductImage
from .serializers import (
    CategorySerializer,
    BrandSerializer,
    BikeModelSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
    ProductWriteSerializer,
    ProductImageSerializer,
    ProductImageUploadSerializer,
)

logger = logging.getLogger("apps.products")


# ─── Category Views ─────────────────────────────────────────────────────────
CATEGORIES_CACHE_KEY = "products_categories_list"

# Categories change rarely — use a longer TTL than the global default.
# Invalidation via post_save/post_delete signals keeps data fresh on writes.
CATEGORIES_L1_TTL = 3600   # 1 hour   (per-process memory)
CATEGORIES_L2_TTL = 86400 * 7   # 1 week  (shared Redis)


class CategoryListAPIView(BaseAPIView):
    """
    GET /api/products/categories/

    Returns all active categories, served from a two-level cache.

    Cache strategy:
        L1 TTL : 120s  (in-process memory, per worker)
        L2 TTL : 600s  (Redis, shared across all workers)
        Write  : populated on first miss, lock prevents stampede
        Purge  : Category post_save / post_delete signals call
                 two_level_cache.delete(CATEGORIES_CACHE_KEY)

    Query optimisations:
        select_related("parent")   — avoids N+1 for the parent FK field
        prefetch_related("subcategories") — avoids N+1 if serializer renders children
        order_by("name")           — stable ordering so cached payload is deterministic
    """

    permission_classes = [AllowAny]

    def _build_fresh_data(self) -> list:
        """
        Queries the DB and serializes the result.

        Kept as a separate method so it can be:
            - passed directly to get_or_set() as a callable
            - unit-tested without going through the HTTP layer
        """
        queryset = (
            Category.objects
            .filter(is_active=True)
            .select_related("parent")
            .prefetch_related("subcategories")
            .annotate(subcategories_count=Count("subcategories"))
            .order_by("name")
        )
        return list(CategorySerializer(queryset, many=True).data)

    def get(self, request: Request, *args: Any, **kwargs: Any):
        start = time.monotonic()

        try:
            data, source = two_level_cache.get_or_set(
                CATEGORIES_CACHE_KEY,
                self._build_fresh_data,
                l1_timeout=CATEGORIES_L1_TTL,
                l2_timeout=CATEGORIES_L2_TTL,
            )
        except Exception as exc:
            logger.error(
                "CategoryListAPIView: failed to retrieve categories "
                "key=%s error=%s",
                CATEGORIES_CACHE_KEY,
                exc,
                exc_info=True,
            )
            return self.error_response(
                message="Unable to retrieve categories. Please try again.",
                status_code=503,
            )

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        count = len(data) if data else 0

        logger.info(
            "CategoryListAPIView: served | source=%s count=%d "
            "elapsed_ms=%s request_id=%s",
            source,
            count,
            elapsed_ms,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=data,
            message="Categories retrieved successfully",
            meta={
                "source": source,
                "count": count,
                "elapsed_ms": elapsed_ms,
            },
        )
# class CategoryListAPIView(BaseAPIView):
#     """
#     GET /api/products/categories/
#     List all active categories. Cached — low write frequency.
#     """
#     permission_classes = [AllowAny]

#     def get(self, request):
#         cache_key = "products_categories_list"
#         # cached_data, source = two_level_cache.get(cache_key)
#         if settings.CACHES:
#             cached_data, source = two_level_cache.get(cache_key)
#         else:
#             cached_data, source = None, None


#         if cached_data:
#             logger.debug("Categories served from %s", source)
#             return self.success_response(
#                 data=cached_data,
#                 message="Categories retrieved successfully",
#                 meta={"source": source},
#             )

#         categories = Category.objects.filter(is_active=True).select_related("parent").prefetch_related("subcategories").order_by("name")
#         serialized = list(CategorySerializer(categories, many=True).data)
#         two_level_cache.set(cache_key, serialized)

#         logger.debug("Categories served from database, cached in L1+L2")
#         return self.success_response(
#             data=serialized,
#             message="Categories retrieved successfully",
#             meta={"source": "database"},
#         )


# ─── Brand Views ────────────────────────────────────────────────────────────

class BrandListAPIView(BaseAPIView):
    """
    GET /api/products/brands/
    List all active brands. Cached — low write frequency.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "products_brands_list"
        cached_data, source = two_level_cache.get(cache_key)

        if cached_data:
            logger.debug("Brands served from %s", source)
            return self.success_response(
                data=cached_data,
                message="Brands retrieved successfully",
                meta={"source": source},
            )

        brands = Brand.objects.filter(is_active=True)
        serialized = list(BrandSerializer(brands, many=True).data)
        two_level_cache.set(cache_key, serialized)

        logger.debug("Brands served from database, cached in L1+L2")
        return self.success_response(
            data=serialized,
            message="Brands retrieved successfully",
            meta={"source": "database"},
        )


# ─── Bike Model Views ───────────────────────────────────────────────────────

class BikeModelListAPIView(BaseAPIView):
    """
    GET /api/products/bike-models/
    GET /api/products/bike-models/?brand=<id>
    List bike models for the compatibility filter dropdown.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        brand_id = request.query_params.get("brand")
        cache_key = f"products_bike_models_brand_{brand_id or 'all'}"

        cached_data, source = two_level_cache.get(cache_key)
        if cached_data:
            logger.debug("Bike models served from %s", source)
            return self.success_response(
                data=cached_data,
                message="Bike models retrieved successfully",
                meta={"source": source},
            )

        queryset = BikeModel.objects.filter(is_active=True).select_related("brand")
        if brand_id:
            queryset = queryset.filter(brand_id=brand_id)

        serialized = list(BikeModelSerializer(queryset, many=True).data)
        two_level_cache.set(cache_key, serialized)

        logger.debug("Bike models served from database, cached in L1+L2")
        return self.success_response(
            data=serialized,
            message="Bike models retrieved successfully",
            meta={"source": "database"},
        )


# ─── Product List / Filter View ─────────────────────────────────────────────

class ProductListAPIView(BaseAPIView):
    """
    GET /api/products/

    Supports filtering by:
        - category (slug)
        - brand (slug)
        - bike_model (id)  ← compatibility filter, the killer feature
        - min_price / max_price
        - search (q)
        - featured (true/false)

    Cached per unique filter+page combination.
    """
    permission_classes = [AllowAny]

    def _build_queryset(self, request) -> QuerySet[Product]:
        queryset = Product.objects.select_related(
            "category", "brand"
        ).prefetch_related("images").filter(status=Product.Status.AVAILABLE)

        category_slug = request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        brand_slug = request.query_params.get("brand")
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        bike_model_id = request.query_params.get("bike_model")
        if bike_model_id:
            queryset = queryset.filter(compatible_bikes__id=bike_model_id)

        min_price = request.query_params.get("min_price")
        if min_price:
            queryset = queryset.filter(price__gte=min_price)

        max_price = request.query_params.get("max_price")
        if max_price:
            queryset = queryset.filter(price__lte=max_price)

        search_query = request.query_params.get("q")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(sku__icontains=search_query)
            )

        featured = request.query_params.get("featured")
        if featured == "true":
            queryset = queryset.filter(is_featured=True)

        return queryset.distinct()

    def _build_cache_key(self, request, page: int, page_size: int) -> str:
        """
        Build a cache key that uniquely represents this filter combination.
        Different filters get different cache entries.
        """
        params = [
            f"page_{page}",
            f"size_{page_size}",
            f"cat_{request.query_params.get('category', '')}",
            f"brand_{request.query_params.get('brand', '')}",
            f"bike_{request.query_params.get('bike_model', '')}",
            f"min_{request.query_params.get('min_price', '')}",
            f"max_{request.query_params.get('max_price', '')}",
            f"q_{request.query_params.get('q', '')}",
            f"feat_{request.query_params.get('featured', '')}",
        ]
        return "products_list_" + "_".join(params)

    def get(self, request):
        page, page_size = get_pagination_params(request)
        cache_key = self._build_cache_key(request, page, page_size)

        cached_data, source = two_level_cache.get(cache_key)
        if cached_data:
            logger.debug("Products served from %s", source)
            return self.success_response(
                data=cached_data["data"],
                message="Products retrieved successfully",
                meta=build_pagination_meta(
                    page, page_size, cached_data["total"], source=source
                ),
            )

        queryset = self._build_queryset(request)
        total = queryset.count()
        offset = (page - 1) * page_size
        products = queryset[offset:offset + page_size]

        serialized = list(
            ProductListSerializer(
                products, many=True, context={"request": request}
            ).data
        )

        two_level_cache.set(cache_key, {"data": serialized, "total": total})
        logger.debug("Products served from database, cached in L1+L2")

        return self.success_response(
            data=serialized,
            message="Products retrieved successfully",
            meta=build_pagination_meta(page, page_size, total, source="database"),
        )


# ─── Product Detail View ────────────────────────────────────────────────────

class ProductDetailAPIView(BaseAPIView):
    """
    GET    /api/products/<slug>/   → public detail view
    PUT    /api/products/<slug>/   → admin only, update
    DELETE /api/products/<slug>/   → admin only, delete
    """
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request, slug: str):
        cache_key = f"product_detail_{slug}"
        cached_data, source = two_level_cache.get(cache_key)

        if cached_data:
            logger.debug("Product detail served from %s", source)
            return self.success_response(
                data=cached_data,
                message="Product retrieved successfully",
                meta={"source": source},
            )

        product = get_object_or_404(
            Product.objects.select_related("category", "brand")
            .prefetch_related("images", "compatible_bikes"),
            slug=slug,
        )
        serialized = ProductDetailSerializer(
            product, context={"request": request}
        ).data
        two_level_cache.set(cache_key, serialized)

        logger.debug("Product detail served from database, cached in L1+L2")
        return self.success_response(
            data=serialized,
            message="Product retrieved successfully",
            meta={"source": "database"},
        )

    def put(self, request, slug: str):
        product = get_object_or_404(Product, slug=slug)
        serializer = ProductWriteSerializer(
            product, data=request.data, partial=True, context={"request": request}
        )
        if not serializer.is_valid():
            return self.error_response(
                message="Product update failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        serializer.save()
        logger.info("Product updated: %s (sku=%s)", product.name, product.sku)
        return self.success_response(
            data=ProductDetailSerializer(
                product, context={"request": request}
            ).data,
            message="Product updated successfully",
        )

    def delete(self, request, slug: str):
        product = get_object_or_404(Product, slug=slug)
        name = product.name
        product.delete()
        logger.info("Product deleted: %s", name)
        return self.success_response(
            message="Product deleted successfully",
        )


# ─── Product Create View ────────────────────────────────────────────────────

class ProductCreateAPIView(BaseAPIView):
    """
    POST /api/products/
    Admin only — create new product.
    """
    permission_classes = [IsAdminOrReadOnly]

    def post(self, request):
        serializer = ProductWriteSerializer(
            data=request.data, context={"request": request}
        )
        if not serializer.is_valid():
            return self.error_response(
                message="Product creation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        product = serializer.save()
        return self.created_response(
            data=ProductDetailSerializer(
                product, context={"request": request}
            ).data,
            message="Product created successfully",
        )


# ─── Product Image Upload View ──────────────────────────────────────────────

class ProductImageUploadAPIView(BaseAPIView):
    """
    POST   /api/products/<slug>/images/             → admin only, add image
    DELETE /api/products/<slug>/images/<image_id>/   → admin only, remove image
    """
    permission_classes = [IsAdminOrReadOnly]

    def post(self, request, slug: str):
        product = get_object_or_404(Product, slug=slug)
        serializer = ProductImageUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return self.error_response(
                message="Image upload failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        image = ProductImage.objects.create(
            product=product,
            image=serializer.validated_data["image"],
            is_primary=serializer.validated_data["is_primary"],
        )

        logger.info("Image uploaded for product: %s", product.name)
        return self.created_response(
            data=ProductImageSerializer(
                image, context={"request": request}
            ).data,
            message="Image uploaded successfully",
        )

    def delete(self, request, slug: str, image_id: int):
        image = get_object_or_404(ProductImage, id=image_id, product__slug=slug)
        image.delete()
        logger.info("Image deleted from product: %s", slug)
        return self.success_response(
            message="Image deleted successfully",
        )