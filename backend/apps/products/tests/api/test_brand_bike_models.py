# apps/products/tests/api/test_brand_bike_model_api.py
"""
API tests for BrandListAPIView and BikeModelListAPIView.

Endpoints:
    GET /api/products/brands/
    GET /api/products/bike-models/
    GET /api/products/bike-models/?brand=<id>

What is tested:
    Brand
        Response structure   — envelope, meta fields
        Filtering            — inactive brands excluded
        Ordering             — alphabetical, deterministic
        Cache behavior       — source, hit on second request, invalidation
        Permissions          — AllowAny, POST not allowed

    BikeModel
        Response structure   — envelope, meta fields including brand_filter
        Filtering            — inactive excluded, ?brand= filter
        Invalid param        — ?brand=abc returns 400
        Cache behavior       — per-brand keys, source, invalidation
        Permissions          — AllowAny, POST not allowed

What is NOT tested here:
    - Serializer field output  → unit/test_serializers.py
    - Signal internals         → unit/test_signals.py
    - Model save logic         → unit/test_models.py

Markers:
    @pytest.mark.integration
    @pytest.mark.django_db
"""
from __future__ import annotations

import pytest

from apps.products.constants import (
    BIKE_MODELS_CACHE_PREFIX,
    BRANDS_CACHE_KEY,
)
from apps.products.models import BikeModel, Brand

from ..urls import BIKE_MODEL_LIST_URL, BRAND_LIST_URL


# ─── Shared response helpers ───────────────────────────────────────────────────

def assert_success_envelope(response, expected_status: int = 200) -> None:
    """
    Standard envelope contract for every successful response:
    {
        "success": true,
        "message": str,
        "data": list,
        "errors": null,
        "meta": dict
    }
    """
    assert response.status_code == expected_status
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["message"], str)
    assert isinstance(payload["data"], list)
    assert payload["errors"] is None
    assert isinstance(payload["meta"], dict)


def assert_base_meta(meta: dict) -> None:
    """
    Both Brand and BikeModel views include source, count, elapsed_ms.
    Asserted separately from view-specific meta fields.
    """
    assert "source" in meta
    assert "count" in meta
    assert "elapsed_ms" in meta
    assert meta["source"] in ("l1_memory", "l2_redis", "database")
    assert isinstance(meta["count"], int)
    assert isinstance(meta["elapsed_ms"], float)


# ══════════════════════════════════════════════════════════════════════════════
# ─── Brand API Tests ───────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBrandListView:
    """
    Tests for GET /api/products/brands/

    Simple flat list — no filters, no pagination.
    One cache key for all requests.
    """

    # ── Response structure ─────────────────────────────────────────────────

    @pytest.mark.integration
    def test_returns_200_with_correct_envelope(
        self,
        api_client,
        brand,
    ) -> None:
        """
        Basic smoke test — endpoint must be reachable and return
        the standard success envelope.
        """
        response = api_client.get(BRAND_LIST_URL)
        assert_success_envelope(response)

    @pytest.mark.integration
    def test_meta_fields_present(
        self,
        api_client,
        brand,
    ) -> None:
        """
        meta must contain source, count, elapsed_ms.
        brand_filter must NOT be present — brands have no filter param.
        """
        response = api_client.get(BRAND_LIST_URL)
        meta = response.json()["meta"]

        assert_base_meta(meta)
        assert "brand_filter" not in meta

    @pytest.mark.integration
    def test_brand_item_fields(
        self,
        api_client,
        brand,
    ) -> None:
        """
        Each brand item must contain id, name, slug, logo, is_active.
        No timestamps — BrandSerializer has no TimestampFieldsMixin.
        """
        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        assert len(payload["data"]) > 0
        item = payload["data"][0]

        expected_fields = ["id", "name", "slug", "logo", "is_active"]
        for field in expected_fields:
            assert field in item, f"Missing field: {field}"

        assert "created_at" not in item
        assert "updated_at" not in item

    # ── Filtering ──────────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_returns_only_active_brands(
        self,
        api_client,
        brand,
        inactive_brand,
    ) -> None:
        """
        Inactive brands must never appear in the response.

        brand         → is_active=True  → must appear
        inactive_brand → is_active=False → must NOT appear
        """
        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert "Honda" in names
        assert "Defunct Motors" not in names

    @pytest.mark.integration
    def test_count_matches_active_brands_only(
        self,
        api_client,
        brand,
        second_brand,
        inactive_brand,
    ) -> None:
        """
        meta.count must equal number of active brands.

        Active:   brand + second_brand = 2
        Inactive: inactive_brand       = excluded
        """
        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        assert payload["meta"]["count"] == 2
        assert len(payload["data"]) == 2

    @pytest.mark.integration
    def test_empty_list_when_no_active_brands(
        self,
        api_client,
        inactive_brand,
    ) -> None:
        """
        When no active brands exist, data must be empty list — not 404.
        """
        response = api_client.get(BRAND_LIST_URL)
        assert_success_envelope(response)

        payload = response.json()
        assert payload["data"] == []
        assert payload["meta"]["count"] == 0

    # ── Ordering ───────────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_brands_ordered_alphabetically(
        self,
        api_client,
        db,
    ) -> None:
        """
        Brands must be ordered alphabetically by name.

        Why deterministic order:
            Without order_by, DB may return different row orders
            on different requests — two workers cache different orderings.
            Alphabetical order guarantees stable cache payload.
        """
        Brand.objects.create(name="Yamaha", is_active=True)
        Brand.objects.create(name="Atlas", is_active=True)
        Brand.objects.create(name="Suzuki", is_active=True)

        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert names == sorted(names)

    # ── Cache behavior ─────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_first_request_source_is_database(
        self,
        api_client,
        brand,
    ) -> None:
        """
        First request after cache clear must come from database.
        clear_all_caches autouse fixture guarantees clean state.
        """
        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()
        assert payload["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_second_request_source_is_cache(
        self,
        api_client,
        brand,
    ) -> None:
        """
        Second request must be served from cache.
        """
        api_client.get(BRAND_LIST_URL)

        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_cache_invalidated_after_brand_created(
        self,
        api_client,
        brand,
    ) -> None:
        """
        After creating a new brand, next request must hit database
        and include the new brand in response data.
        """
        # Populate cache
        api_client.get(BRAND_LIST_URL)

        # Signal fires on create → clears cache
        Brand.objects.create(name="Kawasaki", is_active=True)

        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "Kawasaki" in names

    @pytest.mark.integration
    def test_cache_invalidated_after_brand_updated(
        self,
        api_client,
        brand,
    ) -> None:
        """
        After updating a brand, stale cached data must not be served.
        """
        api_client.get(BRAND_LIST_URL)

        brand.name = "Honda Motors"
        brand.slug = ""
        brand.save()

        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "Honda Motors" in names
        assert "Honda" not in names

    @pytest.mark.integration
    def test_cache_invalidated_after_brand_deleted(
        self,
        api_client,
        brand,
        second_brand,
    ) -> None:
        """
        After deleting a brand, it must not appear in next response.
        """
        api_client.get(BRAND_LIST_URL)

        brand.delete()

        response = api_client.get(BRAND_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "Honda" not in names

    @pytest.mark.integration
    def test_deactivated_brand_removed_from_next_response(
        self,
        api_client,
        brand,
        second_brand,
    ) -> None:
        """
        Deactivating a brand must remove it from next response.

        Flow:
            1. Both brands appear in first response
            2. brand deactivated → signal clears cache
            3. Second response must not contain deactivated brand
        """
        response = api_client.get(BRAND_LIST_URL)
        names = [i["name"] for i in response.json()["data"]]
        assert "Honda" in names

        brand.is_active = False
        brand.save()

        response = api_client.get(BRAND_LIST_URL)
        names = [i["name"] for i in response.json()["data"]]
        assert "Honda" not in names
        assert "Yamaha" in names

    # ── Permissions ────────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_unauthenticated_can_read(self, api_client, brand) -> None:
        response = api_client.get(BRAND_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_customer_can_read(self, customer_client, brand) -> None:
        response = customer_client.get(BRAND_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_admin_can_read(self, admin_client, brand) -> None:
        response = admin_client.get(BRAND_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_post_not_allowed(self, api_client) -> None:
        """
        BrandListAPIView only defines get().
        POST must return 405 Method Not Allowed.
        """
        response = api_client.post(BRAND_LIST_URL, {})
        assert response.status_code == 405


# ══════════════════════════════════════════════════════════════════════════════
# ─── BikeModel API Tests ───────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBikeModelListView:
    """
    Tests for GET /api/products/bike-models/
    and GET /api/products/bike-models/?brand=<id>

    Key difference from Brand:
        BikeModel supports ?brand=<id> filter.
        Each filter value gets its own cache key.
        meta includes brand_filter field.
    """

    # ── Response structure ─────────────────────────────────────────────────

    @pytest.mark.integration
    def test_returns_200_with_correct_envelope(
        self,
        api_client,
        bike_model,
    ) -> None:
        response = api_client.get(BIKE_MODEL_LIST_URL)
        assert_success_envelope(response)

    @pytest.mark.integration
    def test_meta_fields_present(
        self,
        api_client,
        bike_model,
    ) -> None:
        """
        meta must contain source, count, elapsed_ms, AND brand_filter.

        Why brand_filter in meta:
            Frontend needs to know which filter was applied to the
            current response — for UI state (which brand is selected).
        """
        response = api_client.get(BIKE_MODEL_LIST_URL)
        meta = response.json()["meta"]

        assert_base_meta(meta)
        assert "brand_filter" in meta
        assert meta["brand_filter"] is None  # no filter applied

    @pytest.mark.integration
    def test_bike_model_item_fields(
        self,
        api_client,
        bike_model,
    ) -> None:
        """
        Each bike model item must contain all BikeModelSerializer fields.
        No timestamps.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        assert len(payload["data"]) > 0
        item = payload["data"][0]

        expected_fields = [
            "id", "brand", "brand_name", "name",
            "display_name", "slug", "year_start",
            "year_end", "is_active",
        ]
        for field in expected_fields:
            assert field in item, f"Missing field: {field}"

        assert "created_at" not in item
        assert "updated_at" not in item

    @pytest.mark.integration
    def test_brand_name_populated_from_select_related(
        self,
        api_client,
        bike_model,
    ) -> None:
        """
        brand_name must be "Honda" — populated via select_related("brand").
        If select_related is missing, brand_name would still work but
        cause N+1 queries. This confirms the field is present and correct.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        item = next(
            (i for i in payload["data"] if i["name"] == "CD70"),
            None,
        )
        assert item is not None
        assert item["brand_name"] == "Honda"
        assert item["display_name"] == "Honda CD70"

    # ── Filtering — inactive ───────────────────────────────────────────────

    @pytest.mark.integration
    def test_returns_only_active_bike_models(
        self,
        api_client,
        bike_model,
        inactive_bike_model,
    ) -> None:
        """
        Inactive bike models must never appear in response.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert "CD70" in names
        assert "Old Model" not in names

    @pytest.mark.integration
    def test_empty_list_when_no_active_bike_models(
        self,
        api_client,
        inactive_bike_model,
    ) -> None:
        """
        When no active bike models exist, data must be empty list.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL)
        assert_success_envelope(response)
        assert response.json()["data"] == []

    # ── Filtering — ?brand= param ──────────────────────────────────────────

    @pytest.mark.integration
    def test_brand_filter_returns_only_that_brands_models(
        self,
        api_client,
        bike_model,
        second_bike_model,
        brand,
    ) -> None:
        """
        ?brand=<id> must return only bike models for that brand.

        bike_model      → Honda CD70
        second_bike_model → Yamaha YBR125

        ?brand=honda_id must return only Honda CD70.
        """
        response = api_client.get(
            BIKE_MODEL_LIST_URL,
            {"brand": brand.pk},
        )
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert "CD70" in names
        assert "YBR125" not in names

    @pytest.mark.integration
    def test_brand_filter_meta_contains_brand_id(
        self,
        api_client,
        bike_model,
        brand,
    ) -> None:
        """
        When ?brand=<id> is applied, meta.brand_filter must equal that id.
        """
        response = api_client.get(
            BIKE_MODEL_LIST_URL,
            {"brand": brand.pk},
        )
        payload = response.json()
        assert payload["meta"]["brand_filter"] == brand.pk

    @pytest.mark.integration
    def test_no_brand_filter_returns_all_active_models(
        self,
        api_client,
        bike_model,
        second_bike_model,
    ) -> None:
        """
        Without ?brand= filter, all active bike models must be returned.

        bike_model      → Honda CD70
        second_bike_model → Yamaha YBR125
        Both must appear.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert "CD70" in names
        assert "YBR125" in names
        assert payload["meta"]["count"] == 2

    @pytest.mark.integration
    def test_brand_filter_nonexistent_brand_returns_empty_list(
        self,
        api_client,
        bike_model,
    ) -> None:
        """
        ?brand=99999 (nonexistent brand) must return empty list — not 404.

        Why empty list:
            The brand ID may have existed and been deleted.
            Frontend filter may send a stale brand ID.
            Empty list is the correct response — not an error.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL, {"brand": 99999})
        assert_success_envelope(response)
        assert response.json()["data"] == []

    # ── Invalid param ──────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_invalid_brand_param_returns_400(
        self,
        api_client,
    ) -> None:
        """
        ?brand=abc (non-integer) must return 400.

        Why 400:
            _validate_brand_id() cannot coerce "abc" to int.
            Returns is_valid=False → view returns error_response(400).
        """
        response = api_client.get(BIKE_MODEL_LIST_URL, {"brand": "abc"})
        assert response.status_code == 400

        payload = response.json()
        assert payload["success"] is False
        assert "message" in payload

    @pytest.mark.integration
    def test_invalid_brand_param_float_returns_400(
        self,
        api_client,
    ) -> None:
        """
        ?brand=1.5 (float string) must return 400.
        int("1.5") raises ValueError — correctly rejected.
        """
        response = api_client.get(BIKE_MODEL_LIST_URL, {"brand": "1.5"})
        assert response.status_code == 400

    # ── Cache behavior ─────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_first_request_source_is_database(
        self,
        api_client,
        bike_model,
    ) -> None:
        response = api_client.get(BIKE_MODEL_LIST_URL)
        assert response.json()["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_second_request_source_is_cache(
        self,
        api_client,
        bike_model,
    ) -> None:
        api_client.get(BIKE_MODEL_LIST_URL)

        response = api_client.get(BIKE_MODEL_LIST_URL)
        assert response.json()["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_brand_filtered_request_cached_separately(
        self,
        api_client,
        bike_model,
        brand,
    ) -> None:
        """
        ?brand=<id> cache key is separate from unfiltered cache key.

        products_bike_models_brand_all  → unfiltered
        products_bike_models_brand_<id> → brand-filtered

        Populating the unfiltered key must NOT affect the brand-filtered key.
        Brand-filtered first request must still hit database.
        """
        # Populate unfiltered cache
        api_client.get(BIKE_MODEL_LIST_URL)

        # Brand-filtered must be a database hit — its key is unpopulated
        response = api_client.get(
            BIKE_MODEL_LIST_URL,
            {"brand": brand.pk},
        )
        assert response.json()["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_brand_filtered_cache_hit_on_second_request(
        self,
        api_client,
        bike_model,
        brand,
    ) -> None:
        """
        Second brand-filtered request must hit cache.
        """
        api_client.get(BIKE_MODEL_LIST_URL, {"brand": brand.pk})

        response = api_client.get(BIKE_MODEL_LIST_URL, {"brand": brand.pk})
        assert response.json()["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_cache_invalidated_after_bike_model_created(
        self,
        api_client,
        bike_model,
        brand,
    ) -> None:
        """
        After creating a BikeModel, next request must hit database
        and include the new model.
        """
        api_client.get(BIKE_MODEL_LIST_URL)

        BikeModel.objects.create(
            brand=brand,
            name="CB125F",
            year_start=2020,
        )

        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "CB125F" in names

    @pytest.mark.integration
    def test_cache_invalidated_after_bike_model_updated(
        self,
        api_client,
        bike_model,
    ) -> None:
        """
        After updating a BikeModel, stale data must not be served.
        """
        api_client.get(BIKE_MODEL_LIST_URL)

        bike_model.year_end = 2024
        bike_model.save()

        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        item = next(
            (i for i in payload["data"] if i["name"] == "CD70"),
            None,
        )
        assert item is not None
        assert item["year_end"] == 2024

    @pytest.mark.integration
    def test_cache_invalidated_after_bike_model_deleted(
        self,
        api_client,
        bike_model,
    ) -> None:
        """
        After deleting a BikeModel, it must not appear in next response.
        """
        api_client.get(BIKE_MODEL_LIST_URL)

        bike_model.delete()

        response = api_client.get(BIKE_MODEL_LIST_URL)
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "CD70" not in names

    # ── Permissions ────────────────────────────────────────────────────────

    @pytest.mark.integration
    def test_unauthenticated_can_read(
        self,
        api_client,
        bike_model,
    ) -> None:
        response = api_client.get(BIKE_MODEL_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_customer_can_read(
        self,
        customer_client,
        bike_model,
    ) -> None:
        response = customer_client.get(BIKE_MODEL_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_admin_can_read(
        self,
        admin_client,
        bike_model,
    ) -> None:
        response = admin_client.get(BIKE_MODEL_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_post_not_allowed(self, api_client) -> None:
        """
        BikeModelListAPIView only defines get().
        POST must return 405.
        """
        response = api_client.post(BIKE_MODEL_LIST_URL, {})
        assert response.status_code == 405