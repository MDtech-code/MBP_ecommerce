from __future__ import annotations

import logging
import time
from typing import Any
from rest_framework.request import Request
from django.conf import settings
from django.db.models import Count, Prefetch
from django.shortcuts import get_object_or_404
from django.db.models import QuerySet, Q
from rest_framework import status
from rest_framework.permissions import AllowAny

from apps.core.api.views import BaseAPIView
from apps.core.permissions import IsAdminOrReadOnly
from apps.core.cache import two_level_cache
from apps.core.pagination import get_pagination_params, build_pagination_meta
from apps.common.utils.tree import build_tree

from .constants import (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
    CATEGORIES_L1_TTL,
    CATEGORIES_L2_TTL,
    BRANDS_CACHE_KEY,
    BRANDS_L1_TTL,
    BRANDS_L2_TTL,
    BIKE_MODELS_CACHE_PREFIX,
    BIKE_MODELS_L1_TTL,
    BIKE_MODELS_L2_TTL,
    PRODUCTS_LIST_CACHE_PREFIX,
    PRODUCTS_LIST_L1_TTL,
    PRODUCTS_LIST_L2_TTL,
    PRODUCT_DETAIL_CACHE_PREFIX,
    PRODUCT_DETAIL_L1_TTL,
    PRODUCT_DETAIL_L2_TTL,
    SORT_OPTIONS,
    DEFAULT_SORT,
    
)
from .models import Category, Brand, BikeModel, Product
from .serializers import (
    CategoryFlatSerializer,
    BrandSerializer,
    BikeModelSerializer,
    ProductListSerializer,
    ProductDetailSerializer,
)

logger = logging.getLogger("apps.products")


# ─── Category Views ─────────────────────────────────────────────────────────
# CATEGORIES_FLAT_CACHE_KEY = "products_categories_flat"
# CATEGORIES_TREE_CACHE_KEY = "products_categories_tree"

# CATEGORIES_L1_TTL = 86400
# CATEGORIES_L2_TTL = 86400*7


class CategoryListAPIView(BaseAPIView):
    """
    GET /api/products/categories/
    GET /api/products/categories/?view=flat
    GET /api/products/categories/?view=tree

    Both views are powered by ONE database query.

    Query strategy:
        Always fetch all active categories in one flat query.
        For flat view  → return the list directly.
        For tree view  → pass the flat list to build_tree() in Python.

    Why one query for both:
        The previous tree approach used 4 queries (one per depth level).
        build_tree() converts flat→tree in O(n) Python — much cheaper
        than extra DB round trips, especially with cache in front.

    DB query breakdown:
        .filter(is_active=True)                    → only active
        .select_related("parent")                  → parent_name field, free
        .annotate(subcategories_count=Count(...))  → count field, zero extra queries
        .order_by("name")                          → deterministic cache payload
        Total: 1 query always.
    """

    permission_classes = [AllowAny]

    def _fetch_flat_data(self) -> list[dict[str, Any]]:
        """
        Single DB query that powers BOTH flat and tree responses.

        Why this is the only DB method:
            Tree view calls this then passes result to build_tree().
            Flat view calls this and returns directly.
            No code duplication, one query for both.

        Why list():
            DRF returns ReturnList — a custom list subclass.
            Some cache backends cannot serialize it.
            list() gives a plain Python list — always serializable.
        """
        queryset = (
            Category.objects
            .filter(is_active=True)
            .select_related("parent")
            .annotate(subcategories_count=Count("subcategories"))
            .order_by("name")
        )
        return list(CategoryFlatSerializer(queryset, many=True).data)

    def get(self, request: Request, *args: Any, **kwargs: Any):
        start = time.monotonic()

        view_type = request.query_params.get("view", "flat").lower()

        if view_type not in ("flat", "tree"):
            return self.error_response(
                message="Invalid view type. Use ?view=flat or ?view=tree.",
                status_code=400,
            )

        # ── Determine cache key per view type ─────────────────────────────
        cache_key = (
            CATEGORIES_TREE_CACHE_KEY
            if view_type == "tree"
            else CATEGORIES_FLAT_CACHE_KEY
        )

        try:
            if view_type == "flat":
                # Flat: cache and return the serialized list directly
                data, source = two_level_cache.get_or_set(
                    cache_key,
                    self._fetch_flat_data,
                    l1_timeout=CATEGORIES_L1_TTL,
                    l2_timeout=CATEGORIES_L2_TTL,
                )

            else:
                # Tree: cache the tree-shaped data
                # Why cache tree separately:
                #   build_tree() is fast (O(n) Python) but still CPU work.
                #   Caching the already-built tree means zero work on cache hit.
                #   On cache miss: fetch flat → build tree → cache tree.
                def build_tree_data() -> list[dict[str, Any]]:
                    flat = self._fetch_flat_data()
                    return build_tree(flat)

                data, source = two_level_cache.get_or_set(
                    cache_key,
                    build_tree_data,
                    l1_timeout=CATEGORIES_L1_TTL,
                    l2_timeout=CATEGORIES_L2_TTL,
                )

        except Exception as exc:
            logger.error(
                "CategoryListAPIView: failed | view=%s key=%s error=%s",
                view_type,
                cache_key,
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
            "CategoryListAPIView: OK | view=%s source=%s count=%d "
            "elapsed_ms=%s request_id=%s",
            view_type,
            source,
            count,
            elapsed_ms,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=data,
            message="Categories retrieved successfully",
            meta={
                "view": view_type,
                "source": source,
                "count": count,
                "elapsed_ms": elapsed_ms,
            },
        )


# ─── Brand Views ────────────────────────────────────────────────────────────

# BRANDS_CACHE_KEY = "products_brands_list"

# # Why longer TTL than default:
# # Brands change very rarely — Honda/Yamaha/Suzuki are stable data.
# # Admin adds a new brand maybe once a month.
# # Signal invalidation keeps it fresh on writes.
# BRANDS_L1_TTL = 86400    # 1 day
# BRANDS_L2_TTL = 86400*7    # 1 weeks 

class BrandListAPIView(BaseAPIView):
    """
    GET /api/products/brands/

    Returns all active brands for filter dropdowns and brand pages.

    Query strategy:
        .filter(is_active=True)   → never expose inactive brands
        .order_by("name")         → deterministic ordering for stable cache

    Cache strategy:
        L1 TTL : 180s
        L2 TTL : 900s
        Purge  : Brand post_save / post_delete signals
    """

    permission_classes = [AllowAny]

    def _build_fresh_data(self) -> list:
        """
        Why order_by("name"):
            Without explicit ordering, DB may return different row orders
            on different requests. Two workers could cache different orderings
            for the same data — inconsistent frontend display.

        Why list():
            DRF ReturnList is not reliably serializable by all cache backends.
            list() gives a plain Python list — always safe to cache.
        """
        queryset = (
            Brand.objects
            .filter(is_active=True)
            .order_by("name")
        )
        return list(BrandSerializer(queryset, many=True).data)

    def get(self, request: Request, *args: Any, **kwargs: Any):
        start = time.monotonic()

        try:
            data, source = two_level_cache.get_or_set(
                BRANDS_CACHE_KEY,
                self._build_fresh_data,
                l1_timeout=BRANDS_L1_TTL,
                l2_timeout=BRANDS_L2_TTL,
            )
        except Exception as exc:
            logger.error(
                "BrandListAPIView: retrieval failed | key=%s error=%s",
                BRANDS_CACHE_KEY,
                exc,
                exc_info=True,
            )
            return self.error_response(
                message="Unable to retrieve brands. Please try again.",
                status_code=503,
            )

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        count = len(data) if data else 0

        logger.info(
            "BrandListAPIView: OK | source=%s count=%d elapsed_ms=%s request_id=%s",
            source,
            count,
            elapsed_ms,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=data,
            message="Brands retrieved successfully",
            meta={
                "source": source,
                "count": count,
                "elapsed_ms": elapsed_ms,
            },
        )
#! old brand view


# ─── Bike Model Views ───────────────────────────────────────────────────────

# # Why "all" suffix for unfiltered key:
# #   Cache key must be unique per filter combination.
# #   brand=1  → "products_bike_models_brand_1"
# #   no filter → "products_bike_models_brand_all"
# #   Without this, all requests share one key and wrong data is served.
# BIKE_MODELS_CACHE_PREFIX = "products_bike_models_brand"

# # Why shorter TTL than brands:
# #   Bike models are updated more often — new model years, discontinuations.
# #   Still cached aggressively because reads vastly outnumber writes.
# BIKE_MODELS_L1_TTL = 120    # 2 minutes
# BIKE_MODELS_L2_TTL = 600    # 10 minutes


class BikeModelListAPIView(BaseAPIView):
    """
    GET /api/products/bike-models/
    GET /api/products/bike-models/?brand=<id>

    Returns active bike models for the compatibility filter dropdown.

    Why brand filter:
        Frontend compatibility filter works in two steps:
            Step 1 → user selects brand  → fetch models for that brand
            Step 2 → user selects model  → fetch products for that model
        ?brand=<id> enables step 1 without returning all models for all brands.

    Cache strategy:
        Each brand filter value gets its own cache key.
        brand=None  → key: products_bike_models_brand_all
        brand=1     → key: products_bike_models_brand_1
        brand=2     → key: products_bike_models_brand_2

        Why per-brand cache keys:
            Invalidation on BikeModel change only clears affected brand key.
            Other brands' caches stay warm — no unnecessary DB hits.

        L1 TTL : 120s
        L2 TTL : 600s
        Purge  : BikeModel post_save / post_delete signals

    Query strategy:
        .filter(is_active=True)       → never expose inactive models
        .select_related("brand")      → brand_name field, zero extra queries
        .filter(brand_id=brand_id)    → optional brand filter, applied at DB
        .order_by("brand__name","name") → stable ordering for cache
    """

    permission_classes = [AllowAny]

    def _validate_brand_id(self, brand_id_param: str | None) -> tuple[int | None, bool]:
        """
        Validates and converts the brand query param.

        Returns (brand_id, is_valid).
            brand_id=None, is_valid=True  → no filter, show all brands
            brand_id=int,  is_valid=True  → valid filter
            brand_id=None, is_valid=False → invalid param, caller returns 400

        Why validate here instead of in get():
            Keeps the handler clean — one concern per method.
            Also makes this independently testable.

        Why not use DRF filters/serializers for this:
            This is a simple integer coercion, not schema validation.
            A full FilterSet would be over-engineering for one param.
        """
        if brand_id_param is None:
            return None, True
        try:
            return int(brand_id_param), True
        except (ValueError, TypeError):
            return None, False

    def _build_fresh_data(self, brand_id: int | None) -> list:
        """
        Why brand_id as parameter and not reading from request:
            This method is passed as a lambda to get_or_set().
            get_or_set() calls it with zero arguments.
            We capture brand_id via closure — clean, no request coupling.
        """
        queryset = (
            BikeModel.objects
            .filter(is_active=True)
            .select_related("brand")
            .order_by("brand__name", "name")
        )
        if brand_id is not None:
            queryset = queryset.filter(brand_id=brand_id)

        return list(BikeModelSerializer(queryset, many=True).data)

    def get(self, request: Request, *args: Any, **kwargs: Any):
        start = time.monotonic()

        # ── Validate brand query param ─────────────────────────────────────
        brand_id_param = request.query_params.get("brand")
        brand_id, is_valid = self._validate_brand_id(brand_id_param)

        if not is_valid:
            return self.error_response(
                message="Invalid brand ID. Must be a positive integer.",
                status_code=400,
            )

        # ── Build cache key per filter combination ─────────────────────────
        cache_key = f"{BIKE_MODELS_CACHE_PREFIX}_{brand_id or 'all'}"

        try:
            data, source = two_level_cache.get_or_set(
                cache_key,
                lambda: self._build_fresh_data(brand_id),
                l1_timeout=BIKE_MODELS_L1_TTL,
                l2_timeout=BIKE_MODELS_L2_TTL,
            )
        except Exception as exc:
            logger.error(
                "BikeModelListAPIView: retrieval failed | "
                "brand_id=%s key=%s error=%s",
                brand_id,
                cache_key,
                exc,
                exc_info=True,
            )
            return self.error_response(
                message="Unable to retrieve bike models. Please try again.",
                status_code=503,
            )

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        count = len(data) if data else 0

        logger.info(
            "BikeModelListAPIView: OK | brand_id=%s source=%s count=%d "
            "elapsed_ms=%s request_id=%s",
            brand_id or "all",
            source,
            count,
            elapsed_ms,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=data,
            message="Bike models retrieved successfully",
            meta={
                "source": source,
                "count": count,
                "elapsed_ms": elapsed_ms,
                "brand_filter": brand_id,
            },
        )


# ─── Product List / Filter View ─────────────────────────────────────────────

# ── Cache config ───────────────────────────────────────────────────────────────
# PRODUCTS_LIST_CACHE_PREFIX = "products_list"
# # Why shorter TTL than categories/brands:
# #   Products change more often — stock, price, discount updates.
# #   Signal invalidation handles explicit changes.
# #   Short TTL is a safety net for anything that bypasses signals.
# PRODUCTS_LIST_L1_TTL = 60     # 1 minute
# PRODUCTS_LIST_L2_TTL = 180    # 3 minutes

# # ── Sorting config ─────────────────────────────────────────────────────────────
# SORT_OPTIONS: dict[str, str] = {
#     "featured":   "-is_featured",
#     "newest":     "-created_at",
#     "price_asc":  "price",
#     "price_desc": "-price",
#     "name_asc":   "name",
# }
# DEFAULT_SORT = "newest"


class ProductListAPIView(BaseAPIView):
    """
    GET /api/products/

    Product listing with filtering, sorting, and pagination.
    Cached per unique filter + sort + page combination.

    Filters:
        ?category=<slug>        filter by category slug
        ?brand=<slug>           filter by brand slug
        ?bike_model=<id>        compatibility filter — the killer feature
        ?min_price=<decimal>    minimum price
        ?max_price=<decimal>    maximum price
        ?q=<string>             search name, description, SKU
        ?featured=true          featured products only

    Sorting (?sort=):
        featured    → featured first  (default)
        newest      → newest first
        price_asc   → lowest price first
        price_desc  → highest price first
        name_asc    → alphabetical

    Pagination:
        ?page=<int>       page number (default: 1)
        ?page_size=<int>  items per page (default: 12, max: 48)

    Query optimisations:
        select_related("category", "brand")    → category_name, brand_name
        prefetch_related("images")             → primary_image (zero N+1)
        prefetch_related("compatible_bikes")   → primary_bike (zero N+1)
        .distinct()                            → M2M join deduplication
    """

    permission_classes = [AllowAny]

  

    def _get_price_params(
        self, request: Request
    ) -> tuple[float | None, float | None, bool]:
        """
        Returns (min_price, max_price, is_valid).

        Why validate here:
            ?min_price=abc passed to queryset.filter(price__gte="abc")
            causes a Django FieldError / DB error.
            Must catch before hitting the ORM.
        """
        min_price = request.query_params.get("min_price")
        max_price = request.query_params.get("max_price")

        try:
            min_price = float(min_price) if min_price else None
        except (ValueError, TypeError):
            return None, None, False

        try:
            max_price = float(max_price) if max_price else None
        except (ValueError, TypeError):
            return None, None, False

        if min_price is not None and max_price is not None:
            if min_price > max_price:
                return None, None, False

        return min_price, max_price, True

    def _get_bike_model_id(
        self, request: Request
    ) -> tuple[int | None, bool]:
        """Returns (bike_model_id, is_valid)."""
        param = request.query_params.get("bike_model")
        if param is None:
            return None, True
        try:
            return int(param), True
        except (ValueError, TypeError):
            return None, False

    def _get_sort_param(self, request: Request) -> tuple[str, str]:
        """
        Returns (sort_key, order_by_field).

        Why return both:
            sort_key goes into cache key and meta (what user requested).
            order_by_field goes into queryset.order_by().
        """
        sort_key = request.query_params.get("sort", DEFAULT_SORT).lower()
        if sort_key not in SORT_OPTIONS:
            sort_key = DEFAULT_SORT
        return sort_key, SORT_OPTIONS[sort_key]

    # ── Queryset builder ───────────────────────────────────────────────────

    def _build_queryset(
        self,
        request: Request,
        min_price: float | None,
        max_price: float | None,
        bike_model_id: int | None,
        order_by: str,
    ) -> QuerySet[Product]:
        """
        Builds the filtered, sorted queryset.

        Why all params passed explicitly:
            Keeps this method pure — no hidden request reads inside.
            Validated params (not raw strings) passed in — ORM is safe.

        Why .distinct():
            compatible_bikes is M2M.
            A product fitting 3 bike models appears 3 times in JOIN result.
            .distinct() collapses duplicates — critical for correct pagination.

        Why prefetch_related("compatible_bikes"):
            get_primary_bike() in serializer calls obj.compatible_bikes.all()
            Without prefetch, one query per product = N+1.
        """
        queryset = (
            Product.objects
            .filter(status=Product.Status.AVAILABLE)
            .select_related("category", "brand")
            .prefetch_related(
                                "images",
                                Prefetch(
                                    "compatible_bikes",
                                    queryset=BikeModel.objects.select_related("brand"),
                                ),
                            )
            .order_by(order_by)
        )

        category_slug = request.query_params.get("category")
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)

        brand_slug = request.query_params.get("brand")
        if brand_slug:
            queryset = queryset.filter(brand__slug=brand_slug)

        if bike_model_id is not None:
            queryset = queryset.filter(compatible_bikes__id=bike_model_id)

        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)

        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)

        search_query = request.query_params.get("q", "").strip()
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(sku__icontains=search_query)
            )

        if request.query_params.get("featured", "").lower() == "true":
            queryset = queryset.filter(is_featured=True)

        return queryset.distinct()

    # ── Cache key builder ──────────────────────────────────────────────────

    def _build_cache_key(
        self,
        request: Request,
        page: int,
        page_size: int,
        sort_key: str,
    ) -> str:
        """
        Encodes every filter + sort + page into a unique cache key.

        Why include sort in key:
            Same filters + different sort = different result order.
            Without sort in key, price_asc and price_desc share one cache entry.

        Why use raw query param strings (not validated values):
            Empty string '' for unused filters is fine — consistent.
            Validated values (None vs 0) could collide in edge cases.
        """
        parts = [
            f"p{page}",
            f"ps{page_size}",
            f"s{sort_key}",
            f"cat{request.query_params.get('category', '')}",
            f"br{request.query_params.get('brand', '')}",
            f"bk{request.query_params.get('bike_model', '')}",
            f"mn{request.query_params.get('min_price', '')}",
            f"mx{request.query_params.get('max_price', '')}",
            f"q{request.query_params.get('q', '')}",
            f"ft{request.query_params.get('featured', '')}",
        ]
        return "products_list_" + "_".join(parts)

    # ── Request handler ────────────────────────────────────────────────────

    def get(self, request: Request, *args: Any, **kwargs: Any):
        start = time.monotonic()

        # ── Validate all params upfront ────────────────────────────────────
        page, page_size, pagination_valid = get_pagination_params(request,default_page_size=12,max_page_size=48)
        if not pagination_valid:
            return self.error_response(
                message="Invalid page or page_size parameter.",
                status_code=400,
            )

        min_price, max_price, price_valid = self._get_price_params(request)
        if not price_valid:
            return self.error_response(
                message="Invalid price range. "
                        "min_price and max_price must be positive numbers "
                        "and min_price must not exceed max_price.",
                status_code=400,
            )

        bike_model_id, bike_valid = self._get_bike_model_id(request)
        if not bike_valid:
            return self.error_response(
                message="Invalid bike_model ID. Must be a positive integer.",
                status_code=400,
            )

        sort_key, order_by = self._get_sort_param(request)
        cache_key = self._build_cache_key(request, page, page_size, sort_key)

        # ── Try cache ──────────────────────────────────────────────────────
        try:
            cached, source = two_level_cache.get(cache_key)
            if source != "miss":
                elapsed_ms = round((time.monotonic() - start) * 1000, 2)
                logger.info(
                    "ProductListAPIView: OK (cached) | source=%s page=%d "
                    "elapsed_ms=%s request_id=%s",
                    source, page, elapsed_ms,
                    getattr(request, "id", "n/a"),
                )
                return self.success_response(
                    data=cached["data"],
                    message="Products retrieved successfully",
                    meta=build_pagination_meta(
                        page,
                        page_size,
                        cached["total"],
                        source=source,
                        sort=sort_key,
                        elapsed_ms=elapsed_ms,
                    ),
                )
        except Exception as exc:
            # Why continue on cache read failure:
            #   Cache error must not prevent serving data.
            #   Log and fall through to DB.
            logger.warning(
                "ProductListAPIView: cache GET failed | key=%s error=%s",
                cache_key, exc,
            )

        # ── Hit DB ─────────────────────────────────────────────────────────
        try:
            queryset = self._build_queryset(
                request, min_price, max_price, bike_model_id, order_by
            )
            total = queryset.count()
            offset = (page - 1) * page_size
            products = queryset[offset: offset + page_size]

            serialized = list(
                ProductListSerializer(
                    products,
                    many=True,
                    context={"request": request},
                ).data
            )
        except Exception as exc:
            logger.error(
                "ProductListAPIView: DB query failed | key=%s error=%s",
                cache_key, exc,
                exc_info=True,
            )
            return self.error_response(
                message="Unable to retrieve products. Please try again.",
                status_code=503,
            )

        # ── Write to cache ─────────────────────────────────────────────────
        try:
            two_level_cache.set(
                cache_key,
                {"data": serialized, "total": total},
                l1_timeout=PRODUCTS_LIST_L1_TTL,
                l2_timeout=PRODUCTS_LIST_L2_TTL,
            )
        except Exception as exc:
            # Why not return error here:
            #   Data was fetched successfully — serve it even if cache write fails.
            #   Next request will just hit DB again — not a user-facing problem.
            logger.warning(
                "ProductListAPIView: cache SET failed | key=%s error=%s",
                cache_key, exc,
            )

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

        logger.info(
            "ProductListAPIView: OK (database) | total=%d page=%d "
            "sort=%s elapsed_ms=%s request_id=%s",
            total, page, sort_key, elapsed_ms,
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=serialized,
            message="Products retrieved successfully",
            meta=build_pagination_meta(
                page,
                page_size,
                total,
                source="database",
                sort=sort_key,
                elapsed_ms=elapsed_ms,
            ),
        )

    




# ─── Product Detail View ────────────────────────────────────────────────────
# PRODUCT_DETAIL_CACHE_PREFIX = "product_detail"
# PRODUCT_DETAIL_L1_TTL = 60
# PRODUCT_DETAIL_L2_TTL = 300


from django.http import Http404
from django.core.exceptions import ObjectDoesNotExist
class ProductDetailAPIView(BaseAPIView):
    """
    GET /api/products/<slug>/

    Public endpoint — no authentication required.
    Returns full product data for the detail page including:
        - Full image gallery
        - Complete compatible bikes list
        - Nested category with parent (for breadcrumb)
        - Nested brand
        - Related products (same category, up to 4)
        - All computed price/discount/stock fields
    """

    permission_classes = [AllowAny]

    def _get_product_queryset(self):
        """
        Why select_related("category__parent"):
            CategoryFlatSerializer includes parent_name.
            Breadcrumb needs: Home > Bike Parts > Brake Parts > Product.
            category__parent fetches both levels in one JOIN.

        Why Prefetch for compatible_bikes with select_related("brand"):
            BikeModelSerializer accesses brand.name per bike.
            Without this = one brand query per compatible bike = N+1.
        """
        return (
            Product.objects
            .select_related("category__parent", "brand")
            .prefetch_related(
                "images",
                Prefetch(
                    "compatible_bikes",
                    queryset=BikeModel.objects.select_related("brand"),
                ),
            )
        )

    def get(
        self,
        request: Request,
        slug: str,
        *args: Any,
        **kwargs: Any,
    ):
        start = time.monotonic()
        cache_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}"

        def build_fresh_data():
            """
            Why get_object_or_404 inside build_fresh_data:
                get_or_set only calls this on cache miss.
                Http404 raised here propagates through get_or_set
                and must be caught separately from real errors.
            """
            product = get_object_or_404(
                self._get_product_queryset(), slug=slug
            )
            return dict(
                ProductDetailSerializer(
                    product,
                    context={"request": request},
                ).data
            )

        try:
            data, source = two_level_cache.get_or_set(
                cache_key,
                build_fresh_data,
                l1_timeout=PRODUCT_DETAIL_L1_TTL,
                l2_timeout=PRODUCT_DETAIL_L2_TTL,
            )
        except Http404:
        # Why separate Http404 catch BEFORE generic Exception:
        #   Http404 is a valid business outcome — product does not exist.
        #   Must return 404 not 503.
        #   If caught by generic Exception below → returns 503 (wrong).
        #   Order matters: most specific exception first.
            raise
        except Exception as exc:
            logger.error(
                "ProductDetailAPIView: GET failed | slug=%s error=%s",
                slug, exc, exc_info=True,
            )
            return self.error_response(
                message="Unable to retrieve product. Please try again.",
                status_code=503,
            )

        elapsed_ms = round((time.monotonic() - start) * 1000, 2)
        logger.info(
            "ProductDetailAPIView: GET OK | slug=%s source=%s "
            "elapsed_ms=%s request_id=%s",
            slug, source, elapsed_ms, getattr(request, "id", "n/a"),
        )

        return self.success_response(
            data=data,
            message="Product retrieved successfully",
            meta={
                "source": source,
                "elapsed_ms": elapsed_ms,
            },
        )





