# apps/products/tests/api/test_product_list_api.py
"""
API tests for ProductListAPIView.

Endpoint:
    GET /api/products/

What is tested:
    Response structure   — envelope, pagination meta fields
    Status filtering     — only AVAILABLE products returned
    Category filter      — ?category=<slug>
    Brand filter         — ?brand=<slug>
    Bike model filter    — ?bike_model=<id> compatibility filter
    Price filter         — ?min_price=, ?max_price=, range validation
    Search filter        — ?q= searches name, description, SKU
    Featured filter      — ?featured=true
    Sorting              — all 5 sort options
    Pagination           — page, page_size, meta fields, boundaries
    Cache behavior       — source, hit on second request, invalidation
    Invalid params       — price, bike_model, page, page_size
    Permissions          — AllowAny, POST not allowed
    M2M deduplication    — product with multiple bikes appears once

What is NOT tested here:
    - Serializer field output  → unit/test_serializers.py
    - Signal internals         → unit/test_signals.py
    - Model save logic         → unit/test_models.py

Markers:
    @pytest.mark.integration
    @pytest.mark.django_db
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from apps.products.models import BikeModel, Category, Product

from ..urls import PRODUCT_LIST_URL


# ─── Response helpers ──────────────────────────────────────────────────────────

def assert_success_envelope(response, expected_status: int = 200) -> None:
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["message"], str)
    assert isinstance(payload["data"], list)
    assert payload["errors"] is None
    assert isinstance(payload["meta"], dict)


def assert_pagination_meta(meta: dict) -> None:
    """
    Pagination meta must always contain these keys.
    build_pagination_meta() is responsible for populating them.
    """
    required = [
        "page", "page_size", "total", "total_pages",
        "showing_from", "showing_to",
        "has_next", "has_previous",
        "source", "sort", "elapsed_ms",
    ]
    for key in required:
        assert key in meta, f"Missing pagination meta key: {key}"


def get_product_names(response) -> list[str]:
    """Extract product names from response data for assertion readability."""
    return [item["name"] for item in response.json()["data"]]


def get_product_ids(response) -> list[int]:
    """Extract product IDs from response data."""
    return [item["id"] for item in response.json()["data"]]


# ─── Response Structure Tests ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListResponseStructure:

    @pytest.mark.integration
    def test_returns_200_with_correct_envelope(
        self,
        api_client,
        product,
    ) -> None:
        """
        Basic smoke test — endpoint reachable, envelope correct.
        """
        response = api_client.get(PRODUCT_LIST_URL)
        assert_success_envelope(response)

    @pytest.mark.integration
    def test_pagination_meta_fields_present(
        self,
        api_client,
        product,
    ) -> None:
        """
        All pagination meta fields must be present on every response.
        """
        response = api_client.get(PRODUCT_LIST_URL)
        assert_pagination_meta(response.json()["meta"])

    @pytest.mark.integration
    def test_product_item_fields(
        self,
        api_client,
        product,
    ) -> None:
        """
        Each product item must contain all ProductListSerializer fields.
        No timestamps — list serializer intentionally excludes them.
        """
        response = api_client.get(PRODUCT_LIST_URL)
        payload = response.json()

        assert len(payload["data"]) > 0
        item = payload["data"][0]

        expected_fields = [
            "id", "name", "slug", "sku",
            "category_name", "brand_name",
            "primary_image", "primary_bike",
            "price", "discount_price",
            "current_price", "has_discount",
            "discount_percentage", "is_in_stock",
            "status", "is_featured",
        ]
        for field in expected_fields:
            assert field in item, f"Missing field: {field}"

        assert "created_at" not in item
        assert "updated_at" not in item
        assert "description" not in item

    @pytest.mark.integration
    def test_empty_list_when_no_available_products(
        self,
        api_client,
        out_of_stock_product,
    ) -> None:
        """
        When no AVAILABLE products exist, data must be empty list.
        out_of_stock_product has status=OUT_OF_STOCK — excluded.
        """
        response = api_client.get(PRODUCT_LIST_URL)
        assert_success_envelope(response)

        payload = response.json()
        assert payload["data"] == []
        assert payload["meta"]["total"] == 0

    @pytest.mark.integration
    def test_post_not_allowed(self, api_client) -> None:
        response = api_client.post(PRODUCT_LIST_URL, {})
        assert response.status_code == 405


# ─── Status Filtering Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListStatusFilter:
    """
    Product list must ONLY return AVAILABLE products.
    OUT_OF_STOCK and DISCONTINUED must never appear.
    """

    @pytest.mark.integration
    def test_only_available_products_returned(
        self,
        api_client,
        product,
        out_of_stock_product,
    ) -> None:
        """
        product             → AVAILABLE    → must appear
        out_of_stock_product → OUT_OF_STOCK → must NOT appear
        """
        response = api_client.get(PRODUCT_LIST_URL)
        names = get_product_names(response)

        assert product.name in names
        assert out_of_stock_product.name not in names

    @pytest.mark.integration
    def test_discontinued_product_excluded(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
        product,
    ) -> None:
        """
        DISCONTINUED products must not appear even if stock > 0.
        """
        discontinued = Product.objects.create(
            name="Discontinued Part",
            category=category,
            brand=brand,
            sku="DISC-LIST-001",
            price=Decimal("100.00"),
            stock=50,
            status=Product.Status.DISCONTINUED,
            created_by=admin_user,
        )

        response = api_client.get(PRODUCT_LIST_URL)
        names = get_product_names(response)

        assert discontinued.name not in names
        assert product.name in names


# ─── Category Filter Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListCategoryFilter:

    @pytest.mark.integration
    def test_category_filter_returns_matching_products(
        self,
        api_client,
        product,
        category,
        db,
        brand,
        admin_user,
    ) -> None:
        """
        ?category=<slug> must return only products in that category.
        """
        other_cat = Category.objects.create(
            name="Electrical",
            is_active=True,
        )
        other_product = Product.objects.create(
            name="Headlight",
            category=other_cat,
            brand=brand,
            sku="ELEC-001",
            price=Decimal("200.00"),
            stock=5,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )

        response = api_client.get(
            PRODUCT_LIST_URL,
            {"category": category.slug},
        )
        names = get_product_names(response)

        assert product.name in names
        assert other_product.name not in names

    @pytest.mark.integration
    def test_category_filter_nonexistent_slug_returns_empty(
        self,
        api_client,
        product,
    ) -> None:
        """
        ?category=nonexistent-slug must return empty list — not 404.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"category": "nonexistent-slug"},
        )
        assert_success_envelope(response)
        assert response.json()["data"] == []


# ─── Brand Filter Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListBrandFilter:

    @pytest.mark.integration
    def test_brand_filter_returns_matching_products(
        self,
        api_client,
        product,
        universal_product,
        brand,
    ) -> None:
        """
        ?brand=<slug> must return only products for that brand.

        product          → brand=Honda → must appear
        universal_product → brand=None  → must NOT appear
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"brand": brand.slug},
        )
        names = get_product_names(response)

        assert product.name in names
        assert universal_product.name not in names

    @pytest.mark.integration
    def test_brand_filter_nonexistent_slug_returns_empty(
        self,
        api_client,
        product,
    ) -> None:
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"brand": "nonexistent-brand"},
        )
        assert response.json()["data"] == []


# ─── Bike Model Compatibility Filter Tests ─────────────────────────────────────

@pytest.mark.django_db
class TestProductListBikeModelFilter:
    """
    ?bike_model=<id> is the killer feature — "fits my bike" filter.

    Products with compatible_bikes containing that bike ID must appear.
    Products with no compatible_bikes (universal) must NOT appear.
    Products compatible with OTHER bikes must NOT appear.
    """

    @pytest.mark.integration
    def test_bike_model_filter_returns_compatible_products(
        self,
        api_client,
        compatible_product,
        bike_model,
    ) -> None:
        """
        compatible_product has bike_model in compatible_bikes.
        Must appear when ?bike_model=<id> applied.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"bike_model": bike_model.pk},
        )
        names = get_product_names(response)
        assert compatible_product.name in names

    @pytest.mark.integration
    def test_bike_model_filter_excludes_incompatible_products(
        self,
        api_client,
        product,
        compatible_product,
        bike_model,
    ) -> None:
        """
        product has no compatible_bikes assigned.
        Must NOT appear when ?bike_model=<id> applied.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"bike_model": bike_model.pk},
        )
        names = get_product_names(response)
        assert product.name not in names

    @pytest.mark.integration
    def test_bike_model_filter_excludes_different_bike_products(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
        bike_model,
        second_bike_model,
    ) -> None:
        """
        Product compatible with second_bike_model must NOT appear
        when filtering by bike_model.
        """
        other_compatible = Product.objects.create(
            name="YBR125 Part",
            category=category,
            brand=brand,
            sku="YBR-COMPAT-001",
            price=Decimal("400.00"),
            stock=10,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )
        other_compatible.compatible_bikes.add(second_bike_model)

        response = api_client.get(
            PRODUCT_LIST_URL,
            {"bike_model": bike_model.pk},
        )
        names = get_product_names(response)
        assert "YBR125 Part" not in names

    @pytest.mark.integration
    def test_bike_model_filter_no_duplicate_products(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
        bike_model,
        second_bike_model,
    ) -> None:
        """
        Product compatible with multiple bikes must appear ONCE.

        Why .distinct() is critical:
            M2M JOIN produces one row per compatible bike.
            Without .distinct(), a product fitting 2 bikes appears twice.
            Pagination total would be wrong — 2 instead of 1.
        """
        multi_compat = Product.objects.create(
            name="Multi Bike Part",
            category=category,
            brand=brand,
            sku="MULTI-COMPAT-001",
            price=Decimal("500.00"),
            stock=10,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )
        multi_compat.compatible_bikes.add(bike_model)
        multi_compat.compatible_bikes.add(second_bike_model)

        response = api_client.get(PRODUCT_LIST_URL)
        ids = get_product_ids(response)

        assert ids.count(multi_compat.pk) == 1

    @pytest.mark.integration
    def test_invalid_bike_model_param_returns_400(
        self,
        api_client,
    ) -> None:
        """
        ?bike_model=abc must return 400.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"bike_model": "abc"},
        )
        assert response.status_code == 400
        assert response.json()["success"] is False

    @pytest.mark.integration
    def test_nonexistent_bike_model_returns_empty(
        self,
        api_client,
        product,
    ) -> None:
        """
        ?bike_model=99999 (nonexistent) must return empty list — not 404.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"bike_model": 99999},
        )
        assert response.json()["data"] == []


# ─── Price Filter Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListPriceFilter:

    @pytest.mark.integration
    def test_min_price_filter(
        self,
        api_client,
        product,
        discounted_product,
    ) -> None:
        """
        ?min_price=600 must exclude products priced below 600.

        product          → price=850 → must appear
        discounted_product → price=500 → must NOT appear
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"min_price": "600"},
        )
        names = get_product_names(response)

        assert product.name in names
        assert discounted_product.name not in names

    @pytest.mark.integration
    def test_max_price_filter(
        self,
        api_client,
        product,
        discounted_product,
    ) -> None:
        """
        ?max_price=600 must exclude products priced above 600.

        product          → price=850 → must NOT appear
        discounted_product → price=500 → must appear
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"max_price": "600"},
        )
        names = get_product_names(response)

        assert discounted_product.name in names
        assert product.name not in names

    @pytest.mark.integration
    def test_price_range_filter(
        self,
        api_client,
        product,
        discounted_product,
        featured_product,
    ) -> None:
        """
        ?min_price=400&max_price=600 must return only products in range.

        product          → price=850  → excluded (above max)
        discounted_product → price=500  → included
        featured_product → price=150  → excluded (below min)
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"min_price": "400", "max_price": "600"},
        )
        names = get_product_names(response)

        assert discounted_product.name in names
        assert product.name not in names
        assert featured_product.name not in names

    @pytest.mark.integration
    def test_min_price_exceeds_max_price_returns_400(
        self,
        api_client,
    ) -> None:
        """
        ?min_price=1000&max_price=500 must return 400.
        min > max is logically invalid — view rejects it.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"min_price": "1000", "max_price": "500"},
        )
        assert response.status_code == 400
        assert response.json()["success"] is False

    @pytest.mark.integration
    def test_invalid_min_price_returns_400(self, api_client) -> None:
        """
        ?min_price=abc must return 400.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"min_price": "abc"},
        )
        assert response.status_code == 400

    @pytest.mark.integration
    def test_invalid_max_price_returns_400(self, api_client) -> None:
        """
        ?max_price=xyz must return 400.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"max_price": "xyz"},
        )
        assert response.status_code == 400


# ─── Search Filter Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListSearchFilter:
    """
    ?q= searches across name, description, and SKU fields.
    Case-insensitive (icontains).
    """

    @pytest.mark.integration
    def test_search_by_name(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        ?q=brake must return products with "brake" in name.
        product name = "Honda CD70 Brake Shoe Set"
        """
        response = api_client.get(PRODUCT_LIST_URL, {"q": "brake"})
        names = get_product_names(response)

        assert product.name in names
        assert featured_product.name not in names

    @pytest.mark.integration
    def test_search_by_sku(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        ?q=TEST-SKU-001 must match by SKU.
        product SKU = "TEST-SKU-001"
        """
        response = api_client.get(PRODUCT_LIST_URL, {"q": "TEST-SKU-001"})
        names = get_product_names(response)

        assert product.name in names
        assert featured_product.name not in names

    @pytest.mark.integration
    def test_search_by_description(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        ?q= must search description field too.
        """
        described = Product.objects.create(
            name="Generic Part",
            category=category,
            brand=brand,
            sku="DESC-SEARCH-001",
            price=Decimal("200.00"),
            stock=10,
            description="High performance camshaft component",
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )

        response = api_client.get(PRODUCT_LIST_URL, {"q": "camshaft"})
        names = get_product_names(response)
        assert described.name in names

    @pytest.mark.integration
    def test_search_case_insensitive(
        self,
        api_client,
        product,
    ) -> None:
        """
        ?q=BRAKE must match "Brake" — icontains is case-insensitive.
        """
        response = api_client.get(PRODUCT_LIST_URL, {"q": "BRAKE"})
        names = get_product_names(response)
        assert product.name in names

    @pytest.mark.integration
    def test_search_no_match_returns_empty(
        self,
        api_client,
        product,
    ) -> None:
        """
        ?q=zzznomatch must return empty list — not 404.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"q": "zzznomatch"},
        )
        assert response.json()["data"] == []

    @pytest.mark.integration
    def test_empty_search_returns_all_products(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        ?q= (empty string) must return all products — no filtering applied.

        Why:
            search_query = request.query_params.get("q", "").strip()
            Empty string is falsy → filter not applied → all returned.
        """
        response = api_client.get(PRODUCT_LIST_URL, {"q": ""})
        names = get_product_names(response)

        assert product.name in names
        assert featured_product.name in names


# ─── Featured Filter Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListFeaturedFilter:

    @pytest.mark.integration
    def test_featured_filter_returns_only_featured(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        ?featured=true must return only is_featured=True products.

        product          → is_featured=False → must NOT appear
        featured_product → is_featured=True  → must appear
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"featured": "true"},
        )
        names = get_product_names(response)

        assert featured_product.name in names
        assert product.name not in names

    @pytest.mark.integration
    def test_featured_filter_case_insensitive(
        self,
        api_client,
        featured_product,
    ) -> None:
        """
        ?featured=TRUE must work — lowercased before comparison.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"featured": "TRUE"},
        )
        names = get_product_names(response)
        assert featured_product.name in names

    @pytest.mark.integration
    def test_non_true_featured_param_returns_all(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        ?featured=false must NOT filter — only "true" activates filter.

        Why:
            view checks: .lower() == "true"
            Anything else → no filter applied → all products returned.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"featured": "false"},
        )
        names = get_product_names(response)

        assert product.name in names
        assert featured_product.name in names


# ─── Sorting Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListSorting:
    """
    Tests for all 5 sort options.

    SORT_OPTIONS = {
        "featured":   "-is_featured",
        "newest":     "-created_at",
        "price_asc":  "price",
        "price_desc": "-price",
        "name_asc":   "name",
    }
    """

    @pytest.mark.integration
    def test_default_sort_is_newest(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        Without ?sort= param, default is "newest" (-created_at).
        meta.sort must reflect the active sort.
        """
        response = api_client.get(PRODUCT_LIST_URL)
        meta = response.json()["meta"]
        assert meta["sort"] == "newest"

    @pytest.mark.integration
    def test_sort_price_asc(
        self,
        api_client,
        product,
        discounted_product,
        featured_product,
    ) -> None:
        """
        ?sort=price_asc must return products ordered lowest price first.

        featured_product → price=150
        discounted_product → price=500
        product          → price=850
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"sort": "price_asc"},
        )
        payload = response.json()
        prices = [Decimal(item["price"]) for item in payload["data"]]

        assert prices == sorted(prices)
        assert payload["meta"]["sort"] == "price_asc"

    @pytest.mark.integration
    def test_sort_price_desc(
        self,
        api_client,
        product,
        discounted_product,
        featured_product,
    ) -> None:
        """
        ?sort=price_desc must return products ordered highest price first.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"sort": "price_desc"},
        )
        payload = response.json()
        prices = [Decimal(item["price"]) for item in payload["data"]]

        assert prices == sorted(prices, reverse=True)
        assert payload["meta"]["sort"] == "price_desc"

    @pytest.mark.integration
    def test_sort_name_asc(
        self,
        api_client,
        product,
        discounted_product,
        featured_product,
    ) -> None:
        """
        ?sort=name_asc must return products alphabetically by name.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"sort": "name_asc"},
        )
        payload = response.json()
        names = [item["name"] for item in payload["data"]]

        assert names == sorted(names)
        assert payload["meta"]["sort"] == "name_asc"

    @pytest.mark.integration
    def test_invalid_sort_falls_back_to_default(
        self,
        api_client,
        product,
    ) -> None:
        """
        ?sort=invalid must silently fall back to DEFAULT_SORT="newest".

        Why silent fallback not 400:
            Sort is a UI preference — bad sort param should not
            break the page. Falling back to default is better UX.
        """
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"sort": "invalid_sort"},
        )
        assert response.status_code == 200
        assert response.json()["meta"]["sort"] == "newest"

    @pytest.mark.integration
    def test_different_sorts_have_separate_cache_keys(
        self,
        api_client,
        product,
        discounted_product,
    ) -> None:
        """
        price_asc and price_desc must have separate cache keys.
        Populating price_asc cache must not affect price_desc.

        Why:
            Cache key includes sort: f"s{sort_key}"
            products_list_p1_ps12_sprice_asc_...
            products_list_p1_ps12_sprice_desc_...
            Different keys → different cached payloads.
        """
        # Populate price_asc cache
        api_client.get(PRODUCT_LIST_URL, {"sort": "price_asc"})

        # price_desc must still be a database hit
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"sort": "price_desc"},
        )
        assert response.json()["meta"]["source"] == "database"


# ─── Pagination Tests ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListPagination:

    @pytest.mark.integration
    def test_default_page_size_is_12(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        Without ?page_size=, default is 12.
        meta.page_size must be 12.
        """
        for i in range(15):
            Product.objects.create(
                name=f"Product {i:02d}",
                category=category,
                brand=brand,
                sku=f"PAGE-SKU-{i:03d}",
                price=Decimal("100.00"),
                stock=10,
                status=Product.Status.AVAILABLE,
                created_by=admin_user,
            )

        response = api_client.get(PRODUCT_LIST_URL)
        payload = response.json()

        assert payload["meta"]["page_size"] == 12
        assert len(payload["data"]) == 12

    @pytest.mark.integration
    def test_custom_page_size(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        ?page_size=5 must return at most 5 items.
        """
        for i in range(10):
            Product.objects.create(
                name=f"Paged Product {i:02d}",
                category=category,
                brand=brand,
                sku=f"PGSZ-SKU-{i:03d}",
                price=Decimal("100.00"),
                stock=10,
                status=Product.Status.AVAILABLE,
                created_by=admin_user,
            )

        response = api_client.get(PRODUCT_LIST_URL, {"page_size": "5"})
        payload = response.json()

        assert payload["meta"]["page_size"] == 5
        assert len(payload["data"]) == 5

    @pytest.mark.integration
    def test_page_size_capped_at_48(
        self,
        api_client,
        product,
    ) -> None:
        """
        ?page_size=100 must be silently capped at 48.

        Why:
            max_page_size=48 in get_pagination_params().
            Unlimited page_size = DB abuse risk.
        """
        response = api_client.get(PRODUCT_LIST_URL, {"page_size": "100"})
        assert response.json()["meta"]["page_size"] == 48

    @pytest.mark.integration
    def test_second_page_returns_different_products(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        Page 2 must return the next set of products, not the same as page 1.
        """
        for i in range(15):
            Product.objects.create(
                name=f"Pageable Product {i:02d}",
                category=category,
                brand=brand,
                sku=f"PG2-SKU-{i:03d}",
                price=Decimal("100.00"),
                stock=10,
                status=Product.Status.AVAILABLE,
                created_by=admin_user,
            )

        page1 = api_client.get(
            PRODUCT_LIST_URL,
            {"page": "1", "page_size": "10"},
        )
        page2 = api_client.get(
            PRODUCT_LIST_URL,
            {"page": "2", "page_size": "10"},
        )

        ids_page1 = set(get_product_ids(page1))
        ids_page2 = set(get_product_ids(page2))

        assert len(ids_page1.intersection(ids_page2)) == 0

    @pytest.mark.integration
    def test_pagination_meta_correct_values(
        self,
        api_client,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        Pagination meta must compute correct values.

        15 products, page_size=10:
            total=15, total_pages=2
            page=1: showing_from=1, showing_to=10, has_next=True
        """
        for i in range(15):
            Product.objects.create(
                name=f"Meta Product {i:02d}",
                category=category,
                brand=brand,
                sku=f"META-SKU-{i:03d}",
                price=Decimal("100.00"),
                stock=10,
                status=Product.Status.AVAILABLE,
                created_by=admin_user,
            )

        response = api_client.get(
            PRODUCT_LIST_URL,
            {"page": "1", "page_size": "10"},
        )
        meta = response.json()["meta"]

        assert meta["total"] == 15
        assert meta["total_pages"] == 2
        assert meta["page"] == 1
        assert meta["showing_from"] == 1
        assert meta["showing_to"] == 10
        assert meta["has_next"] is True
        assert meta["has_previous"] is False

    @pytest.mark.integration
    def test_invalid_page_param_returns_400(self, api_client) -> None:
        """
        ?page=abc must return 400.
        """
        response = api_client.get(PRODUCT_LIST_URL, {"page": "abc"})
        assert response.status_code == 400

    @pytest.mark.integration
    def test_invalid_page_size_param_returns_400(self, api_client) -> None:
        """
        ?page_size=abc must return 400.
        """
        response = api_client.get(PRODUCT_LIST_URL, {"page_size": "abc"})
        assert response.status_code == 400


# ─── Cache Behavior Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListCacheBehavior:

    @pytest.mark.integration
    def test_first_request_source_is_database(
        self,
        api_client,
        product,
    ) -> None:
        response = api_client.get(PRODUCT_LIST_URL)
        assert response.json()["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_second_request_source_is_cache(
        self,
        api_client,
        product,
    ) -> None:
        api_client.get(PRODUCT_LIST_URL)
        response = api_client.get(PRODUCT_LIST_URL)
        assert response.json()["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_different_filters_have_separate_cache_keys(
        self,
        api_client,
        product,
        category,
        db,
        brand,
        admin_user,
    ) -> None:
        """
        ?category=engine-parts and no filter must have separate cache keys.
        Populating one must not serve stale data for the other.
        """
        # Populate unfiltered cache
        api_client.get(PRODUCT_LIST_URL)

        # Category-filtered must be database hit
        response = api_client.get(
            PRODUCT_LIST_URL,
            {"category": category.slug},
        )
        assert response.json()["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_cache_invalidated_after_product_created(
        self,
        api_client,
        product,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        After creating a product, next request must hit database
        and include the new product.
        """
        api_client.get(PRODUCT_LIST_URL)

        new_product = Product.objects.create(
            name="Newly Added Part",
            category=category,
            brand=brand,
            sku="NEW-PART-001",
            price=Decimal("300.00"),
            stock=5,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )

        response = api_client.get(PRODUCT_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = get_product_names(response)
        assert new_product.name in names

    @pytest.mark.integration
    def test_cache_invalidated_after_product_updated(
        self,
        api_client,
        product,
    ) -> None:
        """
        After updating a product's price, stale cache must not be served.
        """
        api_client.get(PRODUCT_LIST_URL)

        product.price = Decimal("9999.00")
        product.save()

        response = api_client.get(PRODUCT_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        item = next(
            (i for i in payload["data"] if i["id"] == product.pk),
            None,
        )
        assert item is not None
        assert Decimal(item["price"]) == Decimal("9999.00")

    @pytest.mark.integration
    def test_cache_invalidated_after_product_deleted(
        self,
        api_client,
        product,
        featured_product,
    ) -> None:
        """
        After deleting a product, it must not appear in next response.
        """
        api_client.get(PRODUCT_LIST_URL)

        product_name = product.name
        product.delete()

        response = api_client.get(PRODUCT_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = get_product_names(response)
        assert product_name not in names


# ─── Permission Tests ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductListPermissions:
    """
    ProductListAPIView uses AllowAny.
    All users must be able to read.
    """

    @pytest.mark.integration
    def test_unauthenticated_can_read(self, api_client, product) -> None:
        response = api_client.get(PRODUCT_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_customer_can_read(self, customer_client, product) -> None:
        response = customer_client.get(PRODUCT_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_admin_can_read(self, admin_client, product) -> None:
        response = admin_client.get(PRODUCT_LIST_URL)
        assert response.status_code == 200