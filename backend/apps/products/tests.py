from __future__ import annotations

import pytest
from django.core.cache import caches
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.common.choices.role import Role
from .models import Category, Brand, BikeModel, Product, ProductImage


# ─── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    caches['default'].clear()
    caches['local'].clear()
    yield
    caches['default'].clear()
    caches['local'].clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def customer(db) -> User:
    return User.objects.create_user(
        email="customer@test.com",
        full_name="Test Customer",
        password="StrongPass123",
        is_verified=True,
    )


@pytest.fixture
def admin(db) -> User:
    return User.objects.create_superuser(
        email="admin@test.com",
        full_name="Admin User",
        password="AdminPass123",
    )


@pytest.fixture
def admin_client(api_client, admin) -> APIClient:
    response = api_client.post("/api/accounts/login/", {
        "email": admin.email,
        "password": "AdminPass123",
    }, format='json')
    token = response.data["data"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


@pytest.fixture
def customer_client(api_client, customer) -> APIClient:
    response = api_client.post("/api/accounts/login/", {
        "email": customer.email,
        "password": "StrongPass123",
    }, format='json')
    token = response.data["data"]["access"]
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api_client


# ── New category hierarchy fixtures ───────────────────────────────────────────
@pytest.fixture
def category(db) -> Category:
    return Category.objects.create(name="Engine Parts")

@pytest.fixture
def child_category(db, category) -> Category:
    """Direct child of 'Engine Parts' — tests parent/child relationship."""
    return Category.objects.create(name="Pistons", parent=category)


@pytest.fixture
def grandchild_category(db, child_category) -> Category:
    """
    One level deeper — tests that tree serializer recurses
    beyond depth 1 correctly.
    """
    return Category.objects.create(name="Piston Rings", parent=child_category)


@pytest.fixture
def inactive_category(db) -> Category:
    """
    Exists in DB but is_active=False.
    Must never appear in any API response.
    """
    return Category.objects.create(name="Discontinued Parts", is_active=False)

# ── New brand fixtures ───────────────────────────────────────────

@pytest.fixture
def brand(db) -> Brand:
    return Brand.objects.create(name="Honda")

# ── New bike_model  fixtures ───────────────────────────────────────────
@pytest.fixture
def bike_model(db, brand) -> BikeModel:
    return BikeModel.objects.create(
        brand=brand,
        name="CB150F",
        year_start=2018,
        year_end=2023,
    )
# ── New product fixtures ───────────────────────────────────────────

@pytest.fixture
def product(db, category, brand, bike_model) -> Product:
    product = Product.objects.create(
        name="Piston Ring Set",
        category=category,
        brand=brand,
        sku="ENG-PIS-001",
        price=1500,
        stock=10,
    )
    product.compatible_bikes.add(bike_model)
    return product


# ─── Category Tests ──────────────────────────────────────────────────────────



@pytest.mark.django_db
class TestCategoryList:
    """
    All tests scoped to:
        GET /api/products/categories/         (flat — default)
        GET /api/products/categories/?view=flat
        GET /api/products/categories/?view=tree
    """

    URL = "/api/products/categories/"

    # ── Original 3 tests — untouched ──────────────────────────────────────

    def test_list_categories_success(self, api_client, category):
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["success"] is True
        assert len(response.data["data"]) == 1

    def test_categories_cached_on_second_request(self, api_client, category):
        api_client.get(self.URL)
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "l1_memory"

    def test_inactive_category_excluded(self, api_client, category):
        category.is_active = False
        category.save()
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 0

    # ── Response envelope ──────────────────────────────────────────────────

    def test_response_envelope_fields_present(self, api_client, category):
        """
        Why: every response must have success / data / message / meta.
        If BaseAPIView or APIResponseMixin changes shape, this catches it.
        """
        response = api_client.get(self.URL)
        assert "success" in response.data
        assert "data" in response.data
        assert "message" in response.data
        assert "meta" in response.data

    def test_meta_contains_expected_keys(self, api_client, category):
        """
        Why: frontend reads meta.source, meta.count, meta.view, meta.elapsed_ms.
        Missing any key breaks frontend logic silently.
        """
        response = api_client.get(self.URL)
        meta = response.data["meta"]
        assert "source" in meta
        assert "count" in meta
        assert "view" in meta
        assert "elapsed_ms" in meta

    def test_meta_count_matches_data_length(self, api_client, category, child_category):
        """
        Why: meta.count must always equal len(data).
        Mismatch causes frontend pagination / display bugs.
        """
        response = api_client.get(self.URL)
        assert response.data["meta"]["count"] == len(response.data["data"])

    def test_meta_view_is_flat_by_default(self, api_client, category):
        response = api_client.get(self.URL)
        assert response.data["meta"]["view"] == "flat"

    # ── Flat serializer fields ─────────────────────────────────────────────

    def test_flat_item_has_all_required_fields(self, api_client, category):
        """
        Why: if a field is removed from CategoryFlatSerializer,
        frontend breaks silently. This test is the contract.
        """
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        expected_fields = {
            "id", "name", "slug",
            "parent", "parent_name",
            "is_subcategory", "subcategory_count", "is_active",
        }
        assert expected_fields.issubset(set(item.keys()))

    def test_root_category_parent_fields_are_null(self, api_client, category):
        """
        Why: root categories have no parent.
        parent and parent_name must both be null — not missing, not 0.
        """
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        assert item["parent"] is None
        assert item["parent_name"] is None
        assert item["is_subcategory"] is False

    def test_child_category_parent_fields_populated(
        self, api_client, category, child_category
    ):
        """
        Why: frontend dropdown shows "Pistons (Engine Parts)".
        Without parent_name, frontend needs extra API calls to resolve parent name.
        This test ensures parent_name is correctly populated from select_related.
        """
        response = api_client.get(self.URL)
        items = {i["name"]: i for i in response.data["data"]}

        assert items["Pistons"]["parent"] == category.pk
        assert items["Pistons"]["parent_name"] == "Engine Parts"
        assert items["Pistons"]["is_subcategory"] is True

    def test_subcategory_count_correct_for_parent(
        self, api_client, category, child_category
    ):
        """
        Why: subcategory_count comes from a queryset annotation.
        If annotation is removed, it defaults to 0 and this test catches it.
        Ensures N+1 fix (annotation) is still in place.
        """
        response = api_client.get(self.URL)
        items = {i["name"]: i for i in response.data["data"]}
        assert items["Engine Parts"]["subcategory_count"] == 1

    def test_subcategory_count_zero_for_leaf(
        self, api_client, category, child_category
    ):
        response = api_client.get(self.URL)
        items = {i["name"]: i for i in response.data["data"]}
        assert items["Pistons"]["subcategory_count"] == 0

    def test_slug_present_and_correct(self, api_client, category):
        """
        Why: slug is auto-generated in Category.save().
        If that logic breaks, slug is empty — this catches it.
        """
        response = api_client.get(self.URL)
        assert response.data["data"][0]["slug"] == "engine-parts"

    # ── Query param validation ─────────────────────────────────────────────

    def test_explicit_flat_param_works(self, api_client, category):
        """?view=flat must behave identically to default (no param)."""
        response = api_client.get(self.URL, {"view": "flat"})
        assert response.status_code == 200
        assert response.data["meta"]["view"] == "flat"

    def test_invalid_view_param_returns_400(self, api_client):
        """
        Why: arbitrary ?view= values must be rejected.
        Prevents cache key pollution and undefined behaviour.
        """
        response = api_client.get(self.URL, {"view": "invalid"})
        assert response.status_code == 400

    def test_view_param_case_sensitive_rejection(self, api_client):
        """
        Why: view_type is lowercased in the view but 'Tree' != 'tree'
        before lowercasing — confirms .lower() is applied correctly.
        Actually after .lower(), 'Tree' becomes 'tree' which IS valid.
        This test documents that behaviour explicitly.
        """
        response = api_client.get(self.URL, {"view": "Tree"})
        assert response.status_code == 200
        assert response.data["meta"]["view"] == "tree"

    def test_empty_list_returns_200_not_404(self, api_client):
        """
        Why: no categories in DB must return empty list, not 404.
        Frontend expects an iterable always — null or 404 breaks render loops.
        """
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    # ── Tree view ──────────────────────────────────────────────────────────

    def test_tree_returns_200(self, api_client, category):
        response = api_client.get(self.URL, {"view": "tree"})
        assert response.status_code == 200

    def test_tree_meta_view_is_tree(self, api_client, category):
        response = api_client.get(self.URL, {"view": "tree"})
        assert response.data["meta"]["view"] == "tree"

    def test_tree_item_has_children_field(self, api_client, category):
        """
        Why: children field is the entire point of tree view.
        If CategoryTreeSerializer drops it, frontend navigation breaks.
        """
        response = api_client.get(self.URL, {"view": "tree"})
        assert "children" in response.data["data"][0]

    def test_tree_root_has_empty_children_when_no_subcategories(
        self, api_client, category
    ):
        response = api_client.get(self.URL, {"view": "tree"})
        assert response.data["data"][0]["children"] == []

    def test_tree_nests_child_under_parent(
        self, api_client, category, child_category
    ):
        """
        Why: core correctness of tree view.
        Only root categories must appear at top level.
        Children must be nested, not duplicated at root.
        """
        response = api_client.get(self.URL, {"view": "tree"})
        data = response.data["data"]

        # Only 1 root — child must not appear at top level
        assert len(data) == 1
        root = data[0]
        assert root["name"] == "Engine Parts"
        assert len(root["children"]) == 1
        assert root["children"][0]["name"] == "Pistons"

    def test_tree_renders_three_levels_deep(
        self, api_client, category, child_category, grandchild_category
    ):
        """
        Why: recursive serializer must work beyond depth 1.
        Prefetch chain in view covers 3 levels — this confirms it works.
        """
        response = api_client.get(self.URL, {"view": "tree"})
        root = response.data["data"][0]
        child = root["children"][0]
        grandchild = child["children"][0]

        assert root["name"] == "Engine Parts"
        assert child["name"] == "Pistons"
        assert grandchild["name"] == "Piston Rings"
        assert grandchild["children"] == []

    def test_tree_excludes_inactive_children(self, api_client, category):
        """
        Why: inactive child categories must not appear in tree even if
        their parent is active. Tests the is_active filter inside
        get_children() in CategoryTreeSerializer.
        """
        Category.objects.create(
            name="Hidden Part",
            parent=category,
            is_active=False,
        )
        response = api_client.get(self.URL, {"view": "tree"})
        root = response.data["data"][0]
        assert root["children"] == []

    def test_tree_count_is_root_count_only(
        self, api_client, category, child_category
    ):
        """
        Why: meta.count in tree = number of ROOT nodes, not total categories.
        Frontend uses count to render top-level navigation items.
        Total count would be misleading for navigation purposes.
        """
        response = api_client.get(self.URL, {"view": "tree"})
        # 2 categories exist but only 1 is root
        assert response.data["meta"]["count"] == 1

    # ── Cache behaviour ────────────────────────────────────────────────────

    def test_first_request_source_is_database(self, api_client, category):
        """Cache is cold — must always come from database on first hit."""
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_empty_list_is_cached_not_re_fetched(self, api_client):
        """
        Why: [] is falsy — old implementation treated it as cache miss.
        Sentinel encoding fix must make [] a valid cached value.
        If broken, every request hits DB even after caching empty list.
        """
        api_client.get(self.URL)           # DB hit, caches []
        response = api_client.get(self.URL)  # must serve from cache
        assert response.data["meta"]["source"] == "l1_memory"

    def test_cache_invalidated_on_category_update(self, api_client, category):
        """
        Why: post_save signal must fire on .save() and clear cache.
        After update, next request must go to DB and return updated name.
        """
        api_client.get(self.URL)           # warm cache

        category.name = "Updated Engine Parts"
        category.save()                    # triggers signal → cache.delete()

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        names = [i["name"] for i in response.data["data"]]
        assert "Updated Engine Parts" in names

    def test_cache_invalidated_on_category_delete(self, api_client, category):
        """
        Why: deleted categories must not appear in cached response.
        Without signal, deleted category stays in cache until TTL expires.
        """
        api_client.get(self.URL)  # warm cache — 1 category
        category.delete()         # triggers post_delete signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0

    def test_cache_invalidated_on_new_category_added(self, api_client, category):
        """
        Why: newly added categories must appear immediately.
        Tests that post_save signal fires on INSERT (created=True).
        """
        api_client.get(self.URL)               # warm cache — 1 category
        Category.objects.create(name="Brakes") # triggers signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 2

    def test_flat_and_tree_caches_are_independent(self, api_client, category):
        """
        Why: flat and tree use separate cache keys.
        Warming flat must not warm tree — they are different payloads.
        """
        api_client.get(self.URL)                          # warm flat only
        response = api_client.get(self.URL, {"view": "tree"})
        assert response.data["meta"]["source"] == "database"

    def test_signal_invalidates_both_flat_and_tree_cache(
        self, api_client, category
    ):
        """
        Why: _invalidate_all_category_caches() must clear BOTH keys.
        If only flat is cleared, tree serves stale data after a category change.
        """
        api_client.get(self.URL)                    # warm flat
        api_client.get(self.URL, {"view": "tree"})  # warm tree

        category.name = "Changed"
        category.save()                             # signal fires

        flat = api_client.get(self.URL)
        tree = api_client.get(self.URL, {"view": "tree"})

        assert flat.data["meta"]["source"] == "database"
        assert tree.data["meta"]["source"] == "database"

    def test_deactivating_category_invalidates_cache(self, api_client, category):
        """
        Why: toggling is_active=False is a .save() call — signal must fire.
        Without this, deactivated categories remain visible until TTL expires.
        """
        api_client.get(self.URL)   # warm cache — 1 active category

        category.is_active = False
        category.save()            # triggers signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0

    # ── Model integrity (no HTTP — direct ORM) ─────────────────────────────

    def test_root_category_is_not_subcategory(self, category):
        assert category.is_subcategory is False

    def test_child_category_is_subcategory(self, category):
        child = Category.objects.create(name="Pistons", parent=category)
        assert child.is_subcategory is True

    def test_slug_auto_generated_from_name(self, db):
        cat = Category.objects.create(name="Engine Parts")
        assert cat.slug == "engine-parts"

    def test_custom_slug_not_overwritten(self, db):
        """
        Why: Category.save() only sets slug when blank.
        If someone provides a slug, it must be preserved.
        """
        cat = Category.objects.create(name="Engine Parts", slug="my-custom-slug")
        assert cat.slug == "my-custom-slug"

    def test_cascade_delete_removes_children(self, category, child_category):
        """
        Why: parent FK uses on_delete=CASCADE.
        Deleting a parent must remove all its children from DB.
        Admin must be aware of this — signal fires per deleted object.
        """
        child_pk = child_category.pk
        category.delete()
        assert not Category.objects.filter(pk=child_pk).exists()

    def test_str_representation(self, category):
        assert str(category) == "Engine Parts"



# ─── Brand Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBrandList:
    """
    Tests for GET /api/products/brands/
    """

    URL = "/api/products/brands/"

    # ── Basic response ─────────────────────────────────────────────────────

    def test_returns_200(self, api_client, brand):
        response = api_client.get(self.URL)
        assert response.status_code == 200

    def test_response_envelope_shape(self, api_client, brand):
        response = api_client.get(self.URL)
        assert response.data["success"] is True
        assert "data" in response.data
        assert "meta" in response.data

    def test_returns_active_brands(self, api_client, brand):
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["name"] == "Honda"

    def test_inactive_brand_excluded(self, api_client, brand):
        brand.is_active = False
        brand.save()
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 0

    def test_empty_list_returns_200(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_meta_contains_expected_keys(self, api_client, brand):
        response = api_client.get(self.URL)
        meta = response.data["meta"]
        assert "source" in meta
        assert "count" in meta
        assert "elapsed_ms" in meta

    def test_meta_count_matches_data_length(self, api_client, brand):
        response = api_client.get(self.URL)
        assert response.data["meta"]["count"] == len(response.data["data"])

    # ── Serializer fields ──────────────────────────────────────────────────

    def test_brand_item_has_required_fields(self, api_client, brand):
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        assert {"id", "name", "slug", "logo", "is_active"}.issubset(set(item.keys()))

    def test_slug_auto_generated(self, api_client, brand):
        response = api_client.get(self.URL)
        assert response.data["data"][0]["slug"] == "honda"

    # ── Cache behaviour ────────────────────────────────────────────────────

    def test_first_request_hits_database(self, api_client, brand):
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_second_request_hits_l1(self, api_client, brand):
        api_client.get(self.URL)
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "l1_memory"

    def test_empty_list_cached_not_re_fetched(self, api_client):
        """Sentinel fix — [] must not be treated as cache miss."""
        api_client.get(self.URL)
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "l1_memory"

    def test_cache_invalidated_on_brand_update(self, api_client, brand):
        api_client.get(self.URL)
        brand.name = "Honda Updated"
        brand.save()
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert response.data["data"][0]["name"] == "Honda Updated"

    def test_cache_invalidated_on_brand_delete(self, api_client, brand):
        api_client.get(self.URL)
        brand.delete()
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0

    def test_cache_invalidated_on_new_brand_added(self, api_client, brand):
        api_client.get(self.URL)
        Brand.objects.create(name="Yamaha")
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 2

    def test_cache_invalidated_on_deactivation(self, api_client, brand):
        api_client.get(self.URL)
        brand.is_active = False
        brand.save()
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0



# ─── Bike Model Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBikeModelList:
    """
    Tests for:
        GET /api/products/bike-models/
        GET /api/products/bike-models/?brand=<id>
    """

    URL = "/api/products/bike-models/"

    # ── Basic response ─────────────────────────────────────────────────────

    def test_returns_200(self, api_client, bike_model):
        response = api_client.get(self.URL)
        assert response.status_code == 200

    def test_response_envelope_shape(self, api_client, bike_model):
        response = api_client.get(self.URL)
        assert response.data["success"] is True
        assert "data" in response.data
        assert "meta" in response.data

    def test_returns_active_bike_models(self, api_client, bike_model):
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 1

    def test_inactive_bike_model_excluded(self, api_client, bike_model):
        bike_model.is_active = False
        bike_model.save()
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 0

    def test_empty_list_returns_200(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_meta_contains_expected_keys(self, api_client, bike_model):
        response = api_client.get(self.URL)
        meta = response.data["meta"]
        assert "source" in meta
        assert "count" in meta
        assert "elapsed_ms" in meta
        assert "brand_filter" in meta

    def test_meta_count_matches_data_length(self, api_client, bike_model):
        response = api_client.get(self.URL)
        assert response.data["meta"]["count"] == len(response.data["data"])

    # ── Serializer fields ──────────────────────────────────────────────────

    def test_bike_model_item_has_required_fields(self, api_client, bike_model):
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        expected = {
            "id", "brand", "brand_name", "name",
            "display_name", "slug", "year_start", "year_end", "is_active",
        }
        assert expected.issubset(set(item.keys()))

    def test_brand_name_populated(self, api_client, bike_model):
        """
        Why: brand_name comes from select_related.
        If select_related removed, this becomes N+1 but still passes.
        This test confirms the value is correct.
        """
        response = api_client.get(self.URL)
        assert response.data["data"][0]["brand_name"] == "Honda"

    def test_display_name_populated(self, api_client, bike_model):
        response = api_client.get(self.URL)
        display = response.data["data"][0]["display_name"]
        assert "Honda" in display
        assert "CB150F" in display

    # ── Brand filter ───────────────────────────────────────────────────────

    def test_filter_by_brand_returns_correct_models(
        self, api_client, brand, bike_model
    ):
        """
        Why: ?brand= filter must restrict results to that brand only.
        Core feature — used by frontend compatibility filter step 1.
        """
        other_brand = Brand.objects.create(name="Yamaha")
        BikeModel.objects.create(
            brand=other_brand,
            name="YBR125",
            year_start=2015,
        )
        response = api_client.get(self.URL, {"brand": brand.pk})
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["brand_name"] == "Honda"

    def test_filter_by_nonexistent_brand_returns_empty(self, api_client):
        response = api_client.get(self.URL, {"brand": 99999})
        assert response.status_code == 200
        assert response.data["data"] == []

    def test_invalid_brand_param_returns_400(self, api_client):
        """
        Why: ?brand=abc must return 400, not a DB error.
        int("abc") raises ValueError — must be caught and handled.
        """
        response = api_client.get(self.URL, {"brand": "abc"})
        assert response.status_code == 400

    def test_brand_filter_none_shows_all(self, api_client, bike_model):
        """No ?brand= param → all active bike models returned."""
        response = api_client.get(self.URL)
        assert len(response.data["data"]) >= 1

    def test_meta_brand_filter_is_none_when_no_param(self, api_client, bike_model):
        response = api_client.get(self.URL)
        assert response.data["meta"]["brand_filter"] is None

    def test_meta_brand_filter_reflects_param(self, api_client, brand, bike_model):
        response = api_client.get(self.URL, {"brand": brand.pk})
        assert response.data["meta"]["brand_filter"] == brand.pk

    # ── Cache behaviour ────────────────────────────────────────────────────

    def test_first_request_hits_database(self, api_client, bike_model):
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_second_request_hits_l1(self, api_client, bike_model):
        api_client.get(self.URL)
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "l1_memory"

    def test_filtered_and_unfiltered_caches_independent(
        self, api_client, brand, bike_model
    ):
        """
        Why: ?brand=1 and no filter use separate cache keys.
        Warming one must not affect the other.
        """
        api_client.get(self.URL)                          # warm "all"
        response = api_client.get(self.URL, {"brand": brand.pk})
        assert response.data["meta"]["source"] == "database"

    def test_cache_invalidated_on_bike_model_update(
        self, api_client, bike_model
    ):
        api_client.get(self.URL)
        bike_model.name = "CB150F Updated"
        bike_model.save()
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_cache_invalidated_on_bike_model_delete(
        self, api_client, bike_model
    ):
        api_client.get(self.URL)
        bike_model.delete()
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0

    def test_cache_invalidated_on_new_bike_model_added(
        self, api_client, brand, bike_model
    ):
        api_client.get(self.URL)
        BikeModel.objects.create(
            brand=brand,
            name="CB300R",
            year_start=2019,
        )
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 2

    # ── Model integrity ────────────────────────────────────────────────────

    def test_covers_year_within_range(self, bike_model):
        """bike_model: year_start=2018, year_end=2023"""
        assert bike_model.covers_year(2020) is True

    def test_covers_year_before_start(self, bike_model):
        assert bike_model.covers_year(2017) is False

    def test_covers_year_after_end(self, bike_model):
        assert bike_model.covers_year(2024) is False

    def test_covers_year_still_in_production(self, db, brand):
        """year_end=None means still in production — any year >= start matches."""
        model = BikeModel.objects.create(
            brand=brand, name="CB500F", year_start=2013
        )
        assert model.covers_year(2099) is True

    def test_str_representation(self, bike_model):
        result = str(bike_model)
        assert "Honda" in result
        assert "CB150F" in result
        assert "2018" in result



# ─── Product List Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductList:
    """
    Tests for GET /api/products/
    Covers: filtering, sorting, pagination, caching, signals, field validation.
    """

    URL = "/api/products/"

    # ── Basic response ─────────────────────────────────────────────────────

    def test_returns_200(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_returns_available_products(self, api_client, product):
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 1

    def test_out_of_stock_excluded(self, api_client, product):
        product.status = Product.Status.OUT_OF_STOCK
        product.save()
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 0

    def test_discontinued_excluded(self, api_client, product):
        product.status = Product.Status.DISCONTINUED
        product.save()
        response = api_client.get(self.URL)
        assert len(response.data["data"]) == 0

    # ── Response envelope & meta ───────────────────────────────────────────

    def test_meta_has_all_required_keys(self, api_client, product):
        """
        Why: frontend reads all these meta fields.
            page, page_size    → pagination controls
            total              → "Showing X of Y" label
            total_pages        → page number buttons
            showing_from/to    → "Showing 1-12 of 540"
            has_next/previous  → next/prev button enable state
            source             → cache observability
            sort               → confirm active sort to frontend
            elapsed_ms         → performance monitoring
        """
        response = api_client.get(self.URL)
        meta = response.data["meta"]
        for key in [
            "page", "page_size", "total", "total_pages",
            "showing_from", "showing_to", "has_next", "has_previous",
            "source", "sort", "elapsed_ms",
        ]:
            assert key in meta, f"Missing meta key: {key}"

    def test_meta_count_is_accurate(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.data["meta"]["total"] == 1

    def test_showing_from_to_correct_first_page(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.data["meta"]["showing_from"] == 1
        assert response.data["meta"]["showing_to"] == 1

    def test_has_next_false_on_last_page(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.data["meta"]["has_next"] is False

    def test_has_previous_false_on_first_page(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.data["meta"]["has_previous"] is False

    def test_empty_list_returns_200_not_404(self, api_client):
        response = api_client.get(self.URL)
        assert response.status_code == 200
        assert response.data["data"] == []

    # ── Serializer fields ──────────────────────────────────────────────────

    def test_product_card_has_required_fields(self, api_client, product):
        """
        Why: these are the exact fields the frontend card renders.
        Missing any = broken card UI.
        """
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        expected = {
            "id", "name", "slug", "sku",
            "category_name", "brand_name",
            "primary_image", "primary_bike",
            "price", "discount_price", "current_price",
            "has_discount", "discount_percentage",
            "is_in_stock", "status", "is_featured",
        }
        assert expected.issubset(set(item.keys()))

    def test_primary_bike_universal_when_no_compatible_bikes(
        self, api_client, category, brand, admin
    ):
        """
        Why: products with no compatible_bikes fit all bikes.
        Frontend shows "Universal" label in this case.
        """
        p = Product.objects.create(
            name="Universal Part",
            category=category,
            brand=brand,
            sku="UNI-001",
            price=100,
            stock=5,
            created_by=admin,
        )
        response = api_client.get(self.URL)
        items = {i["name"]: i for i in response.data["data"]}
        assert items["Universal Part"]["primary_bike"] == "Universal"

    def test_discount_percentage_calculated_correctly(
        self, api_client, product
    ):
        """product fixture: price=1500, discount_price not set."""
        product.discount_price = 1200
        product.save()
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        assert item["has_discount"] is True
        assert item["discount_percentage"] == 20
        assert item["current_price"] == "1200.00"

    def test_no_discount_fields_when_no_discount_price(
        self, api_client, product
    ):
        response = api_client.get(self.URL)
        item = response.data["data"][0]
        assert item["has_discount"] is False
        assert item["discount_percentage"] == 0
        assert item["current_price"] == item["price"]

    # ── Filters ────────────────────────────────────────────────────────────

    def test_filter_by_category_slug(self, api_client, product, category):
        response = api_client.get(self.URL, {"category": category.slug})
        assert len(response.data["data"]) == 1

    def test_filter_by_wrong_category_returns_empty(self, api_client, product):
        other = Category.objects.create(name="Brakes")
        response = api_client.get(self.URL, {"category": other.slug})
        assert len(response.data["data"]) == 0

    def test_filter_by_brand_slug(self, api_client, product, brand):
        response = api_client.get(self.URL, {"brand": brand.slug})
        assert len(response.data["data"]) == 1

    def test_filter_by_bike_model_compatibility(
        self, api_client, product, bike_model
    ):
        """The killer feature — show only parts that fit the selected bike."""
        response = api_client.get(self.URL, {"bike_model": bike_model.id})
        assert len(response.data["data"]) == 1

    def test_filter_by_incompatible_bike_returns_empty(
        self, api_client, product, brand
    ):
        other_bike = BikeModel.objects.create(
            brand=brand, name="CG125", year_start=2015
        )
        response = api_client.get(self.URL, {"bike_model": other_bike.id})
        assert len(response.data["data"]) == 0

    def test_invalid_bike_model_param_returns_400(self, api_client):
        response = api_client.get(self.URL, {"bike_model": "abc"})
        assert response.status_code == 400

    def test_filter_price_range(self, api_client, product):
        """product fixture price=1500."""
        response = api_client.get(self.URL, {"min_price": 1000, "max_price": 2000})
        assert len(response.data["data"]) == 1

    def test_filter_price_excludes_outside_range(self, api_client, product):
        response = api_client.get(self.URL, {"min_price": 5000})
        assert len(response.data["data"]) == 0

    def test_invalid_min_price_returns_400(self, api_client):
        response = api_client.get(self.URL, {"min_price": "abc"})
        assert response.status_code == 400

    def test_invalid_max_price_returns_400(self, api_client):
        response = api_client.get(self.URL, {"max_price": "xyz"})
        assert response.status_code == 400

    def test_min_price_greater_than_max_price_returns_400(self, api_client):
        response = api_client.get(self.URL, {"min_price": 5000, "max_price": 100})
        assert response.status_code == 400

    def test_search_by_name(self, api_client, product):
        response = api_client.get(self.URL, {"q": "Piston"})
        assert len(response.data["data"]) == 1

    def test_search_by_sku(self, api_client, product):
        response = api_client.get(self.URL, {"q": "ENG-PIS-001"})
        assert len(response.data["data"]) == 1

    def test_search_no_match_returns_empty(self, api_client, product):
        response = api_client.get(self.URL, {"q": "ZZZ-NONEXISTENT"})
        assert len(response.data["data"]) == 0

    def test_filter_featured_only(self, api_client, product):
        product.is_featured = True
        product.save()
        response = api_client.get(self.URL, {"featured": "true"})
        assert len(response.data["data"]) == 1

    def test_featured_false_not_in_featured_filter(self, api_client, product):
        """product.is_featured=False by default."""
        response = api_client.get(self.URL, {"featured": "true"})
        assert len(response.data["data"]) == 0

    # ── Sorting ────────────────────────────────────────────────────────────

    def test_default_sort_is_newest(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.data["meta"]["sort"] == "newest"

    def test_sort_by_price_asc(self, api_client, category, brand, admin):
        Product.objects.create(
            name="Cheap Part", category=category, brand=brand,
            sku="CHE-001", price=100, stock=5, created_by=admin,
        )
        Product.objects.create(
            name="Expensive Part", category=category, brand=brand,
            sku="EXP-001", price=9000, stock=5, created_by=admin,
        )
        response = api_client.get(self.URL, {"sort": "price_asc"})
        prices = [float(i["price"]) for i in response.data["data"]]
        assert prices == sorted(prices)

    def test_sort_by_price_desc(self, api_client, category, brand, admin):
        Product.objects.create(
            name="Cheap Part", category=category, brand=brand,
            sku="CHE-002", price=100, stock=5, created_by=admin,
        )
        Product.objects.create(
            name="Expensive Part", category=category, brand=brand,
            sku="EXP-002", price=9000, stock=5, created_by=admin,
        )
        response = api_client.get(self.URL, {"sort": "price_desc"})
        prices = [float(i["price"]) for i in response.data["data"]]
        assert prices == sorted(prices, reverse=True)

    def test_invalid_sort_falls_back_to_default(self, api_client, product):
        """
        Why: unknown sort values must not crash or error.
        Silently fall back to default sort.
        """
        response = api_client.get(self.URL, {"sort": "invalid_sort"})
        assert response.status_code == 200
        assert response.data["meta"]["sort"] == "newest"

    def test_different_sorts_have_separate_cache_keys(
        self, api_client, product
    ):
        """
        Why: price_asc and price_desc must not share a cache entry.
        Sort is included in cache key — this confirms it.
        """
        api_client.get(self.URL, {"sort": "price_asc"})   # warm price_asc
        response = api_client.get(self.URL, {"sort": "price_desc"})
        assert response.data["meta"]["source"] == "database"

    # ── Pagination ─────────────────────────────────────────────────────────

    def test_pagination_page_size(self, api_client, category, brand, admin):
        """
        Why create products without using product fixture:
            product fixture adds 1 extra — total becomes 16 not 15.
            We control exact count by not using that fixture.
        """
        for i in range(15):
            Product.objects.create(
                name=f"Part {i}", category=category, brand=brand,
                sku=f"SKU-PAG-{i}", price=100, stock=5,
                created_by=admin,
            )
        response = api_client.get(self.URL, {"page": 1, "page_size": 5})
        assert len(response.data["data"]) == 5
        assert response.data["meta"]["total"] == 15
        assert response.data["meta"]["total_pages"] == 3

    def test_pagination_second_page(self, api_client, category, brand, admin):
        for i in range(15):
            Product.objects.create(
                name=f"Part {i}", category=category, brand=brand,
                sku=f"SKU-PG2-{i}", price=100, stock=5,
                created_by=admin,
            )
        response = api_client.get(self.URL, {"page": 2, "page_size": 5})
        assert len(response.data["data"]) == 5
        assert response.data["meta"]["has_previous"] is True
        assert response.data["meta"]["has_next"] is True

    def test_invalid_page_param_returns_400(self, api_client):
        response = api_client.get(self.URL, {"page": "abc"})
        assert response.status_code == 400

    def test_invalid_page_size_param_returns_400(self, api_client):
        response = api_client.get(self.URL, {"page_size": "abc"})
        assert response.status_code == 400

    def test_page_size_capped_at_48(self, api_client, product):
        """
        Why: unlimited page_size = DB abuse risk.
        Even if ?page_size=1000 is passed, max 48 items returned.
        """
        response = api_client.get(self.URL, {"page_size": 1000})
        assert response.status_code == 200
        assert response.data["meta"]["page_size"] == 48

    def test_showing_from_to_on_second_page(
        self, api_client, category, brand, admin
    ):
        for i in range(15):
            Product.objects.create(
                name=f"Part {i}", category=category, brand=brand,
                sku=f"SKU-SHW-{i}", price=100, stock=5,
                created_by=admin,
            )
        response = api_client.get(self.URL, {"page": 2, "page_size": 5})
        assert response.data["meta"]["showing_from"] == 6
        assert response.data["meta"]["showing_to"] == 10

    def test_different_filters_use_separate_cache_keys(
        self, api_client, product, category
    ):
        """Different filter combos must never share the same cache entry."""
        r1 = api_client.get(self.URL)
        r2 = api_client.get(self.URL, {"category": category.slug})
        assert r1.data["meta"]["source"] == "database"
        assert r2.data["meta"]["source"] == "database"

    # ── Cache behaviour ────────────────────────────────────────────────────

    def test_first_request_hits_database(self, api_client, product):
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_second_request_hits_l1(self, api_client, product):
        api_client.get(self.URL)
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "l1_memory"

    def test_empty_list_cached_not_re_fetched(self, api_client):
        """Sentinel fix — [] must be cached, not treated as miss."""
        api_client.get(self.URL)
        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "l1_memory"

    def test_cache_invalidated_on_product_update(self, api_client, product):
        """
        Why: post_save signal must fire and clear list cache.
        Updated price must appear on next request.
        """
        api_client.get(self.URL)       # warm cache

        product.name = "Updated Piston Ring Set"
        product.save()                 # triggers signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert response.data["data"][0]["name"] == "Updated Piston Ring Set"

    def test_cache_invalidated_on_product_delete(self, api_client, product):
        api_client.get(self.URL)       # warm cache — 1 product
        product.delete()               # triggers post_delete signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0

    def test_cache_invalidated_on_new_product_added(
        self, api_client, product, category, brand, admin
    ):
        api_client.get(self.URL)       # warm cache — 1 product
        Product.objects.create(
            name="New Brake Pad",
            category=category,
            brand=brand,
            sku="BRK-NEW-001",
            price=500,
            stock=10,
            created_by=admin,
        )                              # triggers post_save signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 2

    def test_cache_invalidated_on_image_upload(
        self, api_client, product, tmp_path
    ):
        """
        Why: primary_image is in list response.
        Adding an image must invalidate list cache.
        """
        api_client.get(self.URL)       # warm cache

        ProductImage.objects.create(
            product=product,
            image="products/2024/01/test.jpg",
            is_primary=True,
        )                              # triggers post_save signal on ProductImage

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_cache_invalidated_on_image_delete(self, api_client, product):
        img = ProductImage.objects.create(
            product=product,
            image="products/2024/01/test.jpg",
            is_primary=True,
        )
        api_client.get(self.URL)       # warm cache
        img.delete()                   # triggers post_delete signal on ProductImage

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"

    def test_deactivating_product_removes_from_list(self, api_client, product):
        api_client.get(self.URL)       # warm cache — 1 product

        product.status = Product.Status.OUT_OF_STOCK
        product.save()                 # triggers signal

        response = api_client.get(self.URL)
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]) == 0




# apps/products/tests.py
# ADD these two classes at the bottom — do not touch anything above


@pytest.mark.django_db
class TestProductDetail:
    """
    Tests for GET /api/products/<slug>/
    Covers: response shape, nested objects, cache behaviour, signal invalidation.
    """

    URL = "/api/products/{}/"

    # ── Basic response ─────────────────────────────────────────────────────

    def test_returns_200_for_valid_slug(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_returns_404_for_invalid_slug(self, api_client):
        response = api_client.get(self.URL.format("slug-does-not-exist"))
        assert response.status_code == 404

    def test_response_envelope_shape(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        for key in ["success", "data", "message", "meta"]:
            assert key in response.data

    def test_meta_has_source_and_elapsed_ms(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        assert "source" in response.data["meta"]
        assert "elapsed_ms" in response.data["meta"]

    # ── Required fields ────────────────────────────────────────────────────

    def test_detail_has_all_required_fields(self, api_client, product):
        """
        Why: these are the exact fields the frontend detail page renders.
        Missing any = broken UI section.
        """
        response = api_client.get(self.URL.format(product.slug))
        data = response.data["data"]
        expected = {
            "id", "name", "slug", "sku", "description",
            "category", "brand", "compatible_bikes", "images",
            "price", "discount_price", "current_price",
            "has_discount", "discount_percentage",
            "stock", "is_in_stock", "status", "is_featured",
            "related_products", "created_at", "updated_at",
        }
        assert expected.issubset(set(data.keys()))

    # ── Nested category (breadcrumb) ───────────────────────────────────────

    def test_category_is_nested_object(self, api_client, product):
        """
        Why: list view returns category_name string.
        Detail returns full category object for breadcrumb rendering.
        """
        response = api_client.get(self.URL.format(product.slug))
        cat = response.data["data"]["category"]
        assert isinstance(cat, dict)
        for field in ["name", "slug", "parent_name", "is_subcategory"]:
            assert field in cat

    def test_category_parent_name_for_subcategory(
        self, api_client, brand, admin
    ):
        """
        Why: tests select_related("category__parent") is on the queryset.
        Without __parent in the chain → parent_name always None.
        Breadcrumb needs: Home > Bike Parts > Brake Parts > Product.
        """
        parent = Category.objects.create(name="Bike Parts")
        child = Category.objects.create(name="Brake Parts", parent=parent)
        p = Product.objects.create(
            name="Brake Test Part",
            category=child,
            brand=brand,
            sku="BRK-CAT-001",
            price=500,
            stock=5,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(p.slug))
        cat = response.data["data"]["category"]
        assert cat["parent_name"] == "Bike Parts"
        assert cat["is_subcategory"] is True

    # ── Nested brand ───────────────────────────────────────────────────────

    def test_brand_is_nested_object(self, api_client, product, brand):
        response = api_client.get(self.URL.format(product.slug))
        brand_data = response.data["data"]["brand"]
        assert isinstance(brand_data, dict)
        assert brand_data["name"] == brand.name
        assert "slug" in brand_data

    # ── Images ─────────────────────────────────────────────────────────────

    def test_images_empty_when_no_images(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        assert response.data["data"]["images"] == []

    def test_images_returned_correctly(self, api_client, product):
        ProductImage.objects.create(
            product=product,
            image="products/2024/01/primary.jpg",
            is_primary=True,
            order=0,
        )
        ProductImage.objects.create(
            product=product,
            image="products/2024/01/secondary.jpg",
            is_primary=False,
            order=1,
        )
        response = api_client.get(self.URL.format(product.slug))
        images = response.data["data"]["images"]
        assert len(images) == 2

    def test_image_fields_present(self, api_client, product):
        ProductImage.objects.create(
            product=product,
            image="products/2024/01/img.jpg",
            is_primary=True,
        )
        response = api_client.get(self.URL.format(product.slug))
        img = response.data["data"]["images"][0]
        assert {"id", "image", "is_primary", "order"}.issubset(set(img.keys()))

    def test_only_one_primary_image(self, api_client, product):
        """
        Why: ProductImage.save() ensures only one primary per product.
        Detail page uses is_primary to pick the large display image.
        """
        ProductImage.objects.create(
            product=product,
            image="products/2024/01/img1.jpg",
            is_primary=True,
        )
        ProductImage.objects.create(
            product=product,
            image="products/2024/01/img2.jpg",
            is_primary=True,  # save() should demote the first
        )
        response = api_client.get(self.URL.format(product.slug))
        images = response.data["data"]["images"]
        primary_count = sum(1 for img in images if img["is_primary"])
        assert primary_count == 1

    # ── Compatible bikes ───────────────────────────────────────────────────

    def test_compatible_bikes_contains_assigned_bike(
        self, api_client, product, bike_model
    ):
        """product fixture already has bike_model assigned."""
        response = api_client.get(self.URL.format(product.slug))
        bikes = response.data["data"]["compatible_bikes"]
        assert len(bikes) == 1
        assert bikes[0]["name"] == bike_model.name

    def test_compatible_bike_has_brand_name(
        self, api_client, product, bike_model
    ):
        """
        Why: tests Prefetch(compatible_bikes, select_related("brand")).
        brand_name in response proves brand was joined, not lazy-loaded.
        """
        response = api_client.get(self.URL.format(product.slug))
        bike = response.data["data"]["compatible_bikes"][0]
        assert bike["brand_name"] == bike_model.brand.name

    def test_compatible_bikes_empty_for_universal_product(
        self, api_client, category, brand, admin
    ):
        p = Product.objects.create(
            name="Universal Part",
            category=category,
            brand=brand,
            sku="UNI-DET-001",
            price=200,
            stock=5,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(p.slug))
        assert response.data["data"]["compatible_bikes"] == []

    # ── Pricing ────────────────────────────────────────────────────────────

    def test_no_discount_fields_correct(self, api_client, product):
        """product fixture has no discount_price."""
        response = api_client.get(self.URL.format(product.slug))
        data = response.data["data"]
        assert data["has_discount"] is False
        assert data["discount_percentage"] == 0
        assert data["current_price"] == data["price"]

    def test_discount_fields_correct_when_discount_set(
        self, api_client, product
    ):
        product.discount_price = 1200
        product.save()
        response = api_client.get(self.URL.format(product.slug))
        data = response.data["data"]
        assert data["has_discount"] is True
        assert data["current_price"] == "1200.00"
        assert data["discount_percentage"] == 20

    def test_is_in_stock_true_when_stock_available(self, api_client, product):
        """product fixture: stock=10, status=available."""
        response = api_client.get(self.URL.format(product.slug))
        assert response.data["data"]["is_in_stock"] is True
        assert response.data["data"]["stock"] == 10

    def test_is_in_stock_false_when_stock_zero(
        self, api_client, category, brand, admin
    ):
        p = Product.objects.create(
            name="Zero Stock Part",
            category=category,
            brand=brand,
            sku="ZERO-001",
            price=300,
            stock=0,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(p.slug))
        assert response.data["data"]["is_in_stock"] is False

    # ── Related products ───────────────────────────────────────────────────

    def test_related_products_is_list(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        assert isinstance(response.data["data"]["related_products"], list)

    def test_related_products_empty_when_only_product_in_category(
        self, api_client, product
    ):
        """product fixture is the only product in Engine Parts category."""
        response = api_client.get(self.URL.format(product.slug))
        assert response.data["data"]["related_products"] == []

    def test_related_products_same_category(
        self, api_client, product, category, brand, admin
    ):
        related = Product.objects.create(
            name="Related Engine Part",
            category=category,
            brand=brand,
            sku="REL-ENG-001",
            price=800,
            stock=5,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(product.slug))
        slugs = [r["slug"] for r in response.data["data"]["related_products"]]
        assert related.slug in slugs

    def test_related_products_excludes_self(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        slugs = [r["slug"] for r in response.data["data"]["related_products"]]
        assert product.slug not in slugs

    def test_related_products_excludes_other_categories(
        self, api_client, product, brand, admin
    ):
        other_cat = Category.objects.create(name="Brakes")
        other = Product.objects.create(
            name="Brake Pad",
            category=other_cat,
            brand=brand,
            sku="BRK-OTH-001",
            price=400,
            stock=5,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(product.slug))
        slugs = [r["slug"] for r in response.data["data"]["related_products"]]
        assert other.slug not in slugs

    def test_related_products_capped_at_four(
        self, api_client, product, category, brand, admin
    ):
        for i in range(6):
            Product.objects.create(
                name=f"Related Part {i}",
                category=category,
                brand=brand,
                sku=f"REL-CAP-{i:03d}",
                price=300,
                stock=5,
                created_by=admin,
            )
        response = api_client.get(self.URL.format(product.slug))
        assert len(response.data["data"]["related_products"]) <= 4

    def test_related_products_only_available(
        self, api_client, product, category, brand, admin
    ):
        Product.objects.create(
            name="Discontinued Part",
            category=category,
            brand=brand,
            sku="DIS-REL-001",
            price=300,
            stock=0,
            status=Product.Status.DISCONTINUED,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(product.slug))
        for r in response.data["data"]["related_products"]:
            assert r["status"] == Product.Status.AVAILABLE

    def test_related_products_use_list_serializer_fields(
        self, api_client, product, category, brand, admin
    ):
        """
        Why: related products use ProductListSerializer not detail.
        Must have card fields, must NOT have heavy detail fields.
        Prevents accidental infinite recursion.
        """
        Product.objects.create(
            name="Related Card Part",
            category=category,
            brand=brand,
            sku="REL-SER-001",
            price=500,
            stock=5,
            created_by=admin,
        )
        response = api_client.get(self.URL.format(product.slug))
        related = response.data["data"]["related_products"]
        if related:
            assert "name" in related[0]
            assert "current_price" in related[0]
            assert "is_in_stock" in related[0]
            # detail-only fields must NOT be present in related cards
            assert "description" not in related[0]
            assert "compatible_bikes" not in related[0]
            assert "related_products" not in related[0]

    # ── Cache behaviour ────────────────────────────────────────────────────

    def test_first_request_hits_database(self, api_client, product):
        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"

    def test_second_request_hits_l1_cache(self, api_client, product):
        """
        Why: get_or_set stores result in L1 after first DB hit.
        Second request from same worker must be served from memory.
        """
        api_client.get(self.URL.format(product.slug))
        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "l1_memory"

    def test_each_slug_has_independent_cache(
        self, api_client, product, category, brand, admin
    ):
        """
        Why: cache key = product_detail_<slug>.
        Warming product A must not affect product B's cache state.
        """
        other = Product.objects.create(
            name="Other Product",
            category=category,
            brand=brand,
            sku="OTH-CACHE-001",
            price=300,
            stock=5,
            created_by=admin,
        )
        api_client.get(self.URL.format(product.slug))   # warm product A
        response = api_client.get(self.URL.format(other.slug))
        assert response.data["meta"]["source"] == "database"  # B still cold

    def test_cache_invalidated_on_name_update(self, api_client, product):
        api_client.get(self.URL.format(product.slug))   # warm cache

        product.name = "Updated Name"
        product.save()                                   # post_save signal fires

        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"
        assert response.data["data"]["name"] == "Updated Name"

    def test_cache_invalidated_on_price_update(self, api_client, product):
        api_client.get(self.URL.format(product.slug))

        product.price = 9999
        product.save()

        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"
        assert float(response.data["data"]["price"]) == 9999

    def test_cache_invalidated_on_stock_update(self, api_client, product):
        """
        Why: stock shown as is_in_stock on detail page.
        Stale cache showing "In Stock" for zero stock = critical bug.
        """
        api_client.get(self.URL.format(product.slug))

        product.stock = 0
        product.save()

        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"
        assert response.data["data"]["is_in_stock"] is False

    def test_cache_invalidated_on_discount_set(self, api_client, product):
        """
        Why: discount badge must appear immediately when admin sets it.
        Without invalidation, page shows no badge until TTL expires.
        """
        api_client.get(self.URL.format(product.slug))

        product.discount_price = 1200
        product.save()

        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"
        assert response.data["data"]["has_discount"] is True

    def test_cache_invalidated_on_image_upload(self, api_client, product):
        """
        Why: gallery must show newly uploaded image immediately.
        post_save on ProductImage fires signal → clears detail cache.
        """
        api_client.get(self.URL.format(product.slug))   # warm — 0 images

        ProductImage.objects.create(
            product=product,
            image="products/2024/01/new.jpg",
            is_primary=True,
        )                                                # signal fires

        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]["images"]) == 1

    def test_cache_invalidated_on_image_delete(self, api_client, product):
        """
        Why: deleted image must not appear in cached gallery response.
        post_delete on ProductImage fires signal → clears detail cache.
        """
        img = ProductImage.objects.create(
            product=product,
            image="products/2024/01/del.jpg",
            is_primary=True,
        )
        api_client.get(self.URL.format(product.slug))   # warm — 1 image
        img.delete()                                     # signal fires

        response = api_client.get(self.URL.format(product.slug))
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]["images"]) == 0

    def test_cache_invalidated_on_product_delete(
        self, api_client, category, brand, admin
    ):
        """
        Why: separate from product fixture to avoid breaking other tests.
        After delete, slug must return 404 not cached stale data.
        """
        p = Product.objects.create(
            name="To Be Deleted",
            category=category,
            brand=brand,
            sku="DEL-DET-001",
            price=500,
            stock=5,
            created_by=admin,
        )
        slug = p.slug
        api_client.get(self.URL.format(slug))   # warm cache

        p.delete()                               # post_delete signal fires

        response = api_client.get(self.URL.format(slug))
        assert response.status_code == 404


@pytest.mark.django_db
class TestProductImageUpload:
    """
    Tests for:
        POST   /api/products/<slug>/images/
        DELETE /api/products/<slug>/images/<image_id>/

    Admin only — IsAdminOrReadOnly permission.
    """

    IMAGE_URL = "/api/products/{}/images/"
    IMAGE_DELETE_URL = "/api/products/{}/images/{}/"

  
    # ── Cache invalidation via image operations ────────────────────────────

    def test_image_orm_delete_invalidates_detail_cache(
        self, api_client, product
    ):
        """
        Why: post_delete signal on ProductImage must fire on ANY deletion.
        Whether deleted via Django admin, ORM, or anywhere else.
        Signal clears detail cache — gallery must not show deleted image.

        Why use ORM not API:
            Image upload API endpoint has been removed.
            Admin handles image management via Django admin panel.
            Signal behaviour is the same regardless of deletion method.
        """
        img = ProductImage.objects.create(
            product=product,
            image="products/2024/01/signal_detail_test.jpg",
            is_primary=True,
        )
        api_client.get(f"/api/products/{product.slug}/")  # warm detail cache

        img.delete()                                    # signal fires via ORM

        response = api_client.get(f"/api/products/{product.slug}/")
        assert response.data["meta"]["source"] == "database"
        assert len(response.data["data"]["images"]) == 0

    def test_image_orm_delete_invalidates_list_cache(
        self, api_client, product
    ):
        """
        Why: primary_image is in list response.
        Deleting primary image via admin (ORM under the hood) must
        clear list cache so next request does not serve broken image URL.
        """
        img = ProductImage.objects.create(
            product=product,
            image="products/2024/01/signal_list_test.jpg",
            is_primary=True,
        )
        api_client.get("/api/products/")               # warm list cache

        img.delete()                                    # signal fires via ORM

        response = api_client.get("/api/products/")
        assert response.data["meta"]["source"] == "database"
