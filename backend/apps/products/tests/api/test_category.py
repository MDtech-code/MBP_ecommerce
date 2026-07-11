# apps/products/tests/api/test_category_api.py
"""
API tests for CategoryListAPIView.

Endpoint:
    GET /api/products/categories/
    GET /api/products/categories/?view=flat
    GET /api/products/categories/?view=tree

What is tested:
    Response structure   — success, message, data, meta envelope
    Flat view            — default, explicit ?view=flat
    Tree view            — ?view=tree, children nesting, depth
    Filtering            — inactive categories excluded
    Cache behavior       — source field, cache hit after first request
    Invalidation         — signal clears cache after category change
    Invalid param        — ?view=invalid returns 400
    Empty state          — no categories returns empty list
    Meta fields          — view, source, count, elapsed_ms present

What is NOT tested here:
    - Model save logic        → unit/test_models.py
    - Serializer field output → unit/test_serializers.py
    - Signal internals        → unit/test_signals.py

Markers:
    @pytest.mark.integration
    @pytest.mark.django_db
"""
from __future__ import annotations

import pytest

from apps.core.cache import two_level_cache
from apps.products.constants import (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
)
from apps.products.models import Category

from ..urls import CATEGORY_LIST_URL


# ─── Response structure helpers ────────────────────────────────────────────────

def assert_success_envelope(response) -> None:
    """
    Every successful response must match the standard envelope:
    {
        "success": true,
        "message": str,
        "data": list,
        "errors": null,
        "meta": dict
    }
    """
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert isinstance(payload["message"], str)
    assert isinstance(payload["data"], list)
    assert payload["errors"] is None
    assert isinstance(payload["meta"], dict)


def assert_meta_fields(meta: dict, view_type: str) -> None:
    """
    Meta must always contain view, source, count, elapsed_ms.

    Why elapsed_ms:
        Performance monitoring — alerting fires when p95 exceeds threshold.
        Must always be present so monitoring tools never KeyError.

    Why source:
        Tells us whether data came from L1, L2, or DB.
        Used in integration tests to verify cache is working.
    """
    assert "view" in meta
    assert "source" in meta
    assert "count" in meta
    assert "elapsed_ms" in meta
    assert meta["view"] == view_type
    assert meta["source"] in ("l1_memory", "l2_redis", "database")
    assert isinstance(meta["count"], int)
    assert isinstance(meta["elapsed_ms"], float)


# ─── Flat View Tests ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryFlatView:
    """
    Tests for ?view=flat (default behavior).

    Flat view returns a simple list of category dicts —
    no nesting, no children key.
    """

    @pytest.mark.integration
    def test_default_returns_flat_view(
        self,
        api_client,
        category,
    ) -> None:
        """
        GET /api/products/categories/ without ?view param
        must default to flat view.

        Why default=flat:
            Most consumers (dropdowns, search) need flat lists.
            Tree is the exception — explicit opt-in via ?view=tree.
        """
        response = api_client.get(CATEGORY_LIST_URL)
        assert_success_envelope(response)

        payload = response.json()
        assert_meta_fields(payload["meta"], "flat")

    @pytest.mark.integration
    def test_explicit_flat_view(
        self,
        api_client,
        category,
    ) -> None:
        """
        GET /api/products/categories/?view=flat must return flat list.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        assert_success_envelope(response)

        payload = response.json()
        assert_meta_fields(payload["meta"], "flat")
        # Flat list items must NOT have children key
        for item in payload["data"]:
            assert "children" not in item

    @pytest.mark.integration
    def test_flat_returns_only_active_categories(
        self,
        api_client,
        category,
        inactive_category,
    ) -> None:
        """
        Inactive categories must never appear in flat view.

        category        → is_active=True  → must appear
        inactive_category → is_active=False → must NOT appear
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert "Engine Parts" in names
        assert "Discontinued Parts" not in names

    @pytest.mark.integration
    def test_flat_count_matches_active_categories(
        self,
        api_client,
        category,
        subcategory,
        inactive_category,
    ) -> None:
        """
        meta.count must equal the number of active categories returned.

        Active:   category + subcategory = 2
        Inactive: inactive_category      = excluded
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        assert payload["meta"]["count"] == 2
        assert len(payload["data"]) == 2

    @pytest.mark.integration
    def test_flat_item_fields(
        self,
        api_client,
        category,
    ) -> None:
        """
        Each flat item must contain all expected fields.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        assert len(payload["data"]) > 0
        item = payload["data"][0]

        expected_fields = [
            "id", "name", "slug", "parent",
            "parent_name", "is_subcategory",
            "subcategory_count", "is_active",
        ]
        for field in expected_fields:
            assert field in item, f"Missing field in flat item: {field}"

    @pytest.mark.integration
    def test_flat_root_category_fields(
        self,
        api_client,
        category,
    ) -> None:
        """
        Root category must have parent=null, parent_name=null,
        is_subcategory=false.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        root = next(
            (i for i in payload["data"] if i["name"] == "Engine Parts"),
            None,
        )
        assert root is not None
        assert root["parent"] is None
        assert root["parent_name"] is None
        assert root["is_subcategory"] is False

    @pytest.mark.integration
    def test_flat_subcategory_fields(
        self,
        api_client,
        category,
        subcategory,
    ) -> None:
        """
        Subcategory must have parent=<id>, parent_name="Engine Parts",
        is_subcategory=true.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        sub = next(
            (i for i in payload["data"] if i["name"] == "Pistons"),
            None,
        )
        assert sub is not None
        assert sub["parent"] == category.pk
        assert sub["parent_name"] == "Engine Parts"
        assert sub["is_subcategory"] is True

    @pytest.mark.integration
    def test_flat_subcategory_count_on_parent(
        self,
        api_client,
        category,
        subcategory,
    ) -> None:
        """
        Parent category must show subcategory_count=1 after child created.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        root = next(
            (i for i in payload["data"] if i["name"] == "Engine Parts"),
            None,
        )
        assert root["subcategory_count"] == 1

    @pytest.mark.integration
    def test_flat_empty_when_no_active_categories(
        self,
        api_client,
        inactive_category,
    ) -> None:
        """
        When no active categories exist, data must be an empty list —
        not null, not 404.

        Why empty list not 404:
            Empty state is valid — admin has not created categories yet.
            Frontend renders an empty dropdown, not an error page.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        assert_success_envelope(response)

        payload = response.json()
        assert payload["data"] == []
        assert payload["meta"]["count"] == 0

    @pytest.mark.integration
    def test_flat_ordered_alphabetically(
        self,
        api_client,
        db,
    ) -> None:
        """
        Flat list must be ordered alphabetically by name.

        Why deterministic order matters:
            Cache stores one payload per key.
            If DB returns different row order on different queries,
            two workers could cache different orderings — inconsistent UI.
            order_by("name") in queryset guarantees stable cache payload.
        """
        Category.objects.create(name="Tyres", is_active=True)
        Category.objects.create(name="Brakes", is_active=True)
        Category.objects.create(name="Air Filters", is_active=True)

        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        names = [item["name"] for item in payload["data"]]
        assert names == sorted(names)


# ─── Tree View Tests ───────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryTreeView:
    """
    Tests for ?view=tree.

    Tree view returns root categories at top level,
    with nested children lists at each node.
    """

    @pytest.mark.integration
    def test_tree_view_returns_success(
        self,
        api_client,
        category,
    ) -> None:
        """
        GET /api/products/categories/?view=tree must return 200.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        assert_success_envelope(response)

        payload = response.json()
        assert_meta_fields(payload["meta"], "tree")

    @pytest.mark.integration
    def test_tree_items_have_children_key(
        self,
        api_client,
        category,
    ) -> None:
        """
        Every item in tree view must have a children key.
        build_tree() adds children=[] to every node.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        payload = response.json()

        for item in payload["data"]:
            assert "children" in item, (
                f"Node {item.get('name')} missing children key"
            )

    @pytest.mark.integration
    def test_tree_root_contains_subcategory_as_child(
        self,
        api_client,
        category,
        subcategory,
    ) -> None:
        """
        Tree structure must nest subcategory inside its parent.

        Expected:
        [
            {
                "name": "Engine Parts",
                "children": [
                    {"name": "Pistons", "children": []}
                ]
            }
        ]
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        payload = response.json()

        root = next(
            (n for n in payload["data"] if n["name"] == "Engine Parts"),
            None,
        )
        assert root is not None

        child_names = [c["name"] for c in root["children"]]
        assert "Pistons" in child_names

    @pytest.mark.integration
    def test_tree_only_root_categories_at_top_level(
        self,
        api_client,
        category,
        subcategory,
    ) -> None:
        """
        Top-level data list must contain only root categories.
        Subcategories must appear only inside parent children lists —
        never at the top level.

        Why:
            build_tree() attaches non-root nodes to their parent's children.
            If subcategories leaked to top level, the tree is broken.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        payload = response.json()

        top_level_names = [n["name"] for n in payload["data"]]
        assert "Pistons" not in top_level_names
        assert "Engine Parts" in top_level_names

    @pytest.mark.integration
    def test_tree_three_level_nesting(
        self,
        api_client,
        db,
        category,
        subcategory,
    ) -> None:
        """
        Tree must support at least 3 levels of nesting.

        Engine Parts (root)
            └── Pistons (subcategory)
                    └── Piston Rings (sub-subcategory)
        """
        sub_sub = Category.objects.create(
            name="Piston Rings",
            parent=subcategory,
            is_active=True,
        )

        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        payload = response.json()

        root = next(
            (n for n in payload["data"] if n["name"] == "Engine Parts"),
            None,
        )
        assert root is not None

        pistons = next(
            (c for c in root["children"] if c["name"] == "Pistons"),
            None,
        )
        assert pistons is not None

        rings_names = [c["name"] for c in pistons["children"]]
        assert "Piston Rings" in rings_names

    @pytest.mark.integration
    def test_tree_excludes_inactive_categories(
        self,
        api_client,
        category,
        inactive_category,
    ) -> None:
        """
        Inactive categories must not appear anywhere in the tree —
        not at root level, not in any children list.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        payload = response.json()

        all_names = _collect_all_names(payload["data"])
        assert "Discontinued Parts" not in all_names

    @pytest.mark.integration
    def test_tree_empty_when_no_active_categories(
        self,
        api_client,
        inactive_category,
    ) -> None:
        """
        When no active categories exist, tree data must be empty list.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        assert_success_envelope(response)

        payload = response.json()
        assert payload["data"] == []


# ─── Invalid Param Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryInvalidParams:

    @pytest.mark.integration
    def test_invalid_view_param_returns_400(
        self,
        api_client,
    ) -> None:
        """
        ?view=invalid must return 400 with descriptive message.

        Why 400 not 200 with empty data:
            Invalid params are client errors — must be explicit.
            Silently returning flat view would hide bugs in frontend code.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "invalid"})
        assert response.status_code == 400

        payload = response.json()
        assert payload["success"] is False
        assert "message" in payload

    @pytest.mark.integration
    def test_view_param_case_insensitive(
        self,
        api_client,
        category,
    ) -> None:
        """
        ?view=FLAT and ?view=TREE must work — view_type is lowercased.

        Why:
            view_type = request.query_params.get("view", "flat").lower()
            Frontend might send uppercase — must not get 400.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "FLAT"})
        assert response.status_code == 200

        response = api_client.get(CATEGORY_LIST_URL, {"view": "TREE"})
        assert response.status_code == 200


# ─── Cache Behavior Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryCacheBehavior:
    """
    Tests verifying cache integration — source field in meta,
    cache hit on second request, invalidation after model change.

    Why test cache source:
        source="database" → first request, cache was cold
        source="l2_redis" → second request, Redis hit
        source="l1_memory" → third+ request same process, L1 hit

        If source is always "database", caching is broken — every
        request hits DB — defeats the purpose of the cache layer.
    """

    @pytest.mark.integration
    def test_first_request_source_is_database(
        self,
        api_client,
        category,
    ) -> None:
        """
        First request after cache clear must hit the database.

        Why guaranteed database:
            clear_all_caches fixture in global conftest clears
            both L1 and L2 before every test.
            No stale cache can exist at test start.
        """
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()
        assert payload["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_second_request_source_is_cache(
        self,
        api_client,
        category,
    ) -> None:
        """
        Second request must be served from cache — not database.

        Why L2 not L1:
            L1 (LocMemCache) is per-process.
            APIClient in tests may not share the same process memory
            as the cache that was populated by the first request.
            L2 (Redis) is shared — guaranteed hit on second request.
        """
        # First request — populates cache
        api_client.get(CATEGORY_LIST_URL, {"view": "flat"})

        # Second request — must hit cache
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        assert payload["meta"]["source"] in ("l1_memory", "l2_redis")

    @pytest.mark.integration
    def test_tree_and_flat_have_separate_cache_keys(
        self,
        api_client,
        category,
    ) -> None:
        """
        Flat and tree responses are cached under different keys.
        A cache hit on flat must not affect tree and vice versa.

        Why separate keys:
            CATEGORIES_FLAT_CACHE_KEY = "products_categories_flat"
            CATEGORIES_TREE_CACHE_KEY = "products_categories_tree"
            Different data shapes — cannot share one cache key.
        """
        # Prime flat cache
        api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        # Tree must still be a database hit (its key was never populated)
        response = api_client.get(CATEGORY_LIST_URL, {"view": "tree"})
        payload = response.json()
        assert payload["meta"]["source"] == "database"

    @pytest.mark.integration
    def test_cache_invalidated_after_category_created(
        self,
        api_client,
        category,
    ) -> None:
        """
        After creating a new category, next request must hit database —
        not return stale cached data.

        Flow:
            1. First request  → populates cache
            2. New category created → signal clears cache
            3. Second request → must hit database (cache was cleared)
            4. New category must appear in response data
        """
        # Step 1 — populate cache
        api_client.get(CATEGORY_LIST_URL, {"view": "flat"})

        # Step 2 — create new category (signal fires, clears cache)
        Category.objects.create(name="Clutch Parts", is_active=True)

        # Step 3 — next request must hit database
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        assert payload["meta"]["source"] == "database"

        # Step 4 — new category must be in fresh data
        names = [item["name"] for item in payload["data"]]
        assert "Clutch Parts" in names

    @pytest.mark.integration
    def test_cache_invalidated_after_category_updated(
        self,
        api_client,
        category,
    ) -> None:
        """
        After updating a category, stale data must not be served.
        """
        # Populate cache
        api_client.get(CATEGORY_LIST_URL, {"view": "flat"})

        # Update category — signal fires
        category.name = "Engine Components"
        category.slug = ""
        category.save()

        # Next request must hit database with fresh data
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "Engine Components" in names
        assert "Engine Parts" not in names

    @pytest.mark.integration
    def test_cache_invalidated_after_category_deleted(
        self,
        api_client,
        category,
        subcategory,
    ) -> None:
        """
        After deleting a category, it must not appear in next response.
        """
        # Populate cache
        api_client.get(CATEGORY_LIST_URL, {"view": "flat"})

        # Delete subcategory — signal fires
        subcategory.delete()

        # Next request must hit database
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        payload = response.json()

        assert payload["meta"]["source"] == "database"
        names = [item["name"] for item in payload["data"]]
        assert "Pistons" not in names

    @pytest.mark.integration
    def test_inactive_category_not_in_cache_after_deactivation(
        self,
        api_client,
        category,
        subcategory,
    ) -> None:
        """
        When a category is deactivated, it must not appear in
        the next response even if cache previously held it.

        Flow:
            1. subcategory is active — appears in first response
            2. subcategory deactivated — signal clears cache
            3. second response must not contain subcategory
        """
        # Step 1 — subcategory is active, appears in first response
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        names = [i["name"] for i in response.json()["data"]]
        assert "Pistons" in names

        # Step 2 — deactivate subcategory
        subcategory.is_active = False
        subcategory.save()

        # Step 3 — must not appear
        response = api_client.get(CATEGORY_LIST_URL, {"view": "flat"})
        names = [i["name"] for i in response.json()["data"]]
        assert "Pistons" not in names


# ─── Permission Tests ──────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryPermissions:
    """
    CategoryListAPIView uses AllowAny.
    All users — unauthenticated, customer, admin — must get 200.
    """

    @pytest.mark.integration
    def test_unauthenticated_can_read(
        self,
        api_client,
        category,
    ) -> None:
        response = api_client.get(CATEGORY_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_customer_can_read(
        self,
        customer_client,
        category,
    ) -> None:
        response = customer_client.get(CATEGORY_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_admin_can_read(
        self,
        admin_client,
        category,
    ) -> None:
        response = admin_client.get(CATEGORY_LIST_URL)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_post_not_allowed(
        self,
        api_client,
    ) -> None:
        """
        CategoryListAPIView only defines get().
        POST must return 405 Method Not Allowed.
        """
        response = api_client.post(CATEGORY_LIST_URL, {})
        assert response.status_code == 405


# ─── Tree helper ───────────────────────────────────────────────────────────────

def _collect_all_names(nodes: list[dict]) -> list[str]:
    """
    Recursively collect all names from a tree response.

    Used to verify inactive categories are absent at ANY depth —
    not just at the root level.
    """
    names = []
    for node in nodes:
        names.append(node.get("name", ""))
        if node.get("children"):
            names.extend(_collect_all_names(node["children"]))
    return names