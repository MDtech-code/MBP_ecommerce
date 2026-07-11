# apps/products/tests/unit/test_signals.py
"""
Unit tests for product app cache invalidation signals.

What is tested:
    Category signals  — post_save, post_delete invalidate flat + tree cache
    Brand signals     — post_save, post_delete invalidate brand cache
    BikeModel signals — post_save, post_delete invalidate bike model cache
    Product signals   — post_save, post_delete invalidate list + detail cache
    ProductImage signals — post_save, post_delete invalidate list + detail cache

Testing strategy:
    1. Manually SET a known value into cache under the exact key
    2. Trigger the signal (create / update / delete the model instance)
    3. Assert cache returns "miss" — signal cleared it correctly

Why this strategy:
    We test the CONTRACT — "signal must clear this key" — not the
    implementation detail of how two_level_cache.delete() works internally.
    If someone renames a cache key constant without updating signals,
    this test catches it immediately.

Why we use two_level_cache directly not Django cache API:
    Signals call two_level_cache.delete().
    two_level_cache.get() is the correct way to verify the key is gone.
    Using Django's cache.get() directly would bypass the versioning
    wrapper (_versioned_key) and always return None — false positive.

Markers:
    @pytest.mark.unit
    @pytest.mark.django_db
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.cache import two_level_cache
from apps.products.constants import (
    BIKE_MODELS_CACHE_PREFIX,
    BRANDS_CACHE_KEY,
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
    PRODUCT_DETAIL_CACHE_PREFIX,
    PRODUCTS_LIST_CACHE_PREFIX,
)
from apps.products.models import (
    BikeModel,
    Brand,
    Category,
    Product,
    ProductImage,
)


# ─── Helpers ───────────────────────────────────────────────────────────────────

SENTINEL = {"cached": True, "data": "sentinel_value"}
"""
Sentinel value written to cache before each test.

Why a dict not a string:
    two_level_cache uses sentinel encoding {"__v": value} internally.
    A plain string could collide with encoding edge cases.
    A dict with known keys makes assertion failures obvious.
"""


def _seed_cache(key: str) -> None:
    """Write sentinel into both L1 and L2 under the given key."""
    two_level_cache.set(key, SENTINEL)


def _is_cache_miss(key: str) -> bool:
    """
    Returns True if key is gone from both cache levels.

    Why check source == "miss":
        two_level_cache.get() returns (value, source).
        source="miss" means neither L1 nor L2 had the key.
        This is the only correct way to verify deletion through
        the versioning wrapper.
    """
    _, source = two_level_cache.get(key)
    return source == "miss"


# ─── Category Signal Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategorySignals:
    """
    Category post_save and post_delete must invalidate
    both flat and tree cache keys.

    Why both keys always:
        Any category change (name, parent, is_active) makes
        both flat list and tree structure stale simultaneously.
        Clearing only one would serve stale data on the other endpoint.
    """

    @pytest.mark.unit
    def test_create_invalidates_flat_cache(self, db) -> None:
        """
        Creating a new Category must clear the flat cache key.
        """
        _seed_cache(CATEGORIES_FLAT_CACHE_KEY)
        assert not _is_cache_miss(CATEGORIES_FLAT_CACHE_KEY)

        Category.objects.create(name="New Category For Signal Test")

        assert _is_cache_miss(CATEGORIES_FLAT_CACHE_KEY)

    @pytest.mark.unit
    def test_create_invalidates_tree_cache(self, db) -> None:
        """
        Creating a new Category must clear the tree cache key.
        """
        _seed_cache(CATEGORIES_TREE_CACHE_KEY)
        assert not _is_cache_miss(CATEGORIES_TREE_CACHE_KEY)

        Category.objects.create(name="Tree Signal Test Category")

        assert _is_cache_miss(CATEGORIES_TREE_CACHE_KEY)

    @pytest.mark.unit
    def test_update_invalidates_flat_cache(self, category: Category) -> None:
        """
        Updating an existing Category must clear the flat cache.
        """
        _seed_cache(CATEGORIES_FLAT_CACHE_KEY)

        category.name = "Engine Parts Updated"
        category.slug = ""  # force slug regeneration
        category.save()

        assert _is_cache_miss(CATEGORIES_FLAT_CACHE_KEY)

    @pytest.mark.unit
    def test_update_invalidates_tree_cache(self, category: Category) -> None:
        """
        Updating an existing Category must clear the tree cache.
        """
        _seed_cache(CATEGORIES_TREE_CACHE_KEY)

        category.is_active = False
        category.save()

        assert _is_cache_miss(CATEGORIES_TREE_CACHE_KEY)

    @pytest.mark.unit
    def test_delete_invalidates_flat_cache(self, category: Category) -> None:
        """
        Deleting a Category must clear the flat cache.
        """
        _seed_cache(CATEGORIES_FLAT_CACHE_KEY)

        category.delete()

        assert _is_cache_miss(CATEGORIES_FLAT_CACHE_KEY)

    @pytest.mark.unit
    def test_delete_invalidates_tree_cache(self, category: Category) -> None:
        """
        Deleting a Category must clear the tree cache.
        """
        _seed_cache(CATEGORIES_TREE_CACHE_KEY)

        category.delete()

        assert _is_cache_miss(CATEGORIES_TREE_CACHE_KEY)

    @pytest.mark.unit
    def test_both_keys_cleared_together_on_save(
        self,
        category: Category,
    ) -> None:
        """
        Both flat and tree cache must be cleared in the same signal call.

        Why one test for both:
            The signal helper _invalidate_all_category_caches() iterates
            _CATEGORY_CACHE_KEYS tuple and clears both in one call.
            This test verifies the tuple contains both keys and
            both are actually cleared — not just one.
        """
        _seed_cache(CATEGORIES_FLAT_CACHE_KEY)
        _seed_cache(CATEGORIES_TREE_CACHE_KEY)

        category.is_active = True
        category.save()

        assert _is_cache_miss(CATEGORIES_FLAT_CACHE_KEY)
        assert _is_cache_miss(CATEGORIES_TREE_CACHE_KEY)


# ─── Brand Signal Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBrandSignals:
    """
    Brand post_save and post_delete must invalidate the brand list cache.

    Why only one key:
        Brands have no filter variations — always one flat list.
    """

    @pytest.mark.unit
    def test_create_invalidates_brand_cache(self, db) -> None:
        """
        Creating a new Brand must clear the brand list cache.
        """
        _seed_cache(BRANDS_CACHE_KEY)
        assert not _is_cache_miss(BRANDS_CACHE_KEY)

        Brand.objects.create(name="Suzuki")

        assert _is_cache_miss(BRANDS_CACHE_KEY)

    @pytest.mark.unit
    def test_update_invalidates_brand_cache(self, brand: Brand) -> None:
        """
        Updating a Brand must clear the brand list cache.
        """
        _seed_cache(BRANDS_CACHE_KEY)

        brand.is_active = False
        brand.save()

        assert _is_cache_miss(BRANDS_CACHE_KEY)

    @pytest.mark.unit
    def test_delete_invalidates_brand_cache(self, brand: Brand) -> None:
        """
        Deleting a Brand must clear the brand list cache.
        """
        _seed_cache(BRANDS_CACHE_KEY)

        brand.delete()

        assert _is_cache_miss(BRANDS_CACHE_KEY)


# ─── BikeModel Signal Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBikeModelSignals:
    """
    BikeModel post_save and post_delete must invalidate
    the bike model cache prefix.

    Why prefix not exact key:
        Bike model list has two cache variants:
            1. products_bike_models_brand_all   (no filter)
            2. products_bike_models_brand_<id>  (brand filtered)
        Prefix delete clears ALL variants in one operation.
    """

    @pytest.mark.unit
    def test_create_invalidates_bike_model_cache(self, db, brand: Brand) -> None:
        """
        Creating a BikeModel must clear the bike model cache prefix.
        """
        cache_key = f"{BIKE_MODELS_CACHE_PREFIX}_all"
        _seed_cache(cache_key)
        assert not _is_cache_miss(cache_key)

        BikeModel.objects.create(
            brand=brand,
            name="CB125F",
            year_start=2020,
        )

        assert _is_cache_miss(cache_key)

    @pytest.mark.unit
    def test_update_invalidates_bike_model_cache(
        self,
        bike_model: BikeModel,
    ) -> None:
        """
        Updating a BikeModel must clear the bike model cache prefix.
        """
        cache_key = f"{BIKE_MODELS_CACHE_PREFIX}_all"
        _seed_cache(cache_key)

        bike_model.is_active = False
        bike_model.save()

        assert _is_cache_miss(cache_key)

    @pytest.mark.unit
    def test_delete_invalidates_bike_model_cache(
        self,
        bike_model: BikeModel,
    ) -> None:
        """
        Deleting a BikeModel must clear the bike model cache prefix.
        """
        cache_key = f"{BIKE_MODELS_CACHE_PREFIX}_all"
        _seed_cache(cache_key)

        bike_model.delete()

        assert _is_cache_miss(cache_key)

    @pytest.mark.unit
    def test_brand_specific_cache_also_cleared(
        self,
        bike_model: BikeModel,
        brand: Brand,
    ) -> None:
        """
        Brand-specific cache variant must also be cleared.

        Why:
            products_bike_models_brand_<id> is a separate cache key.
            prefix delete pattern clears ALL keys matching the prefix.
            This test verifies the brand-specific variant is gone too.
        """
        brand_specific_key = f"{BIKE_MODELS_CACHE_PREFIX}_{brand.pk}"
        _seed_cache(brand_specific_key)

        bike_model.is_active = False
        bike_model.save()

        assert _is_cache_miss(brand_specific_key)


# ─── Product Signal Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductSignals:
    """
    Product post_save and post_delete must invalidate:
        - Product list cache (prefix — all filter/sort/page variants)
        - Product detail cache (exact key per slug)
    """

    @pytest.mark.unit
    def test_create_invalidates_list_cache(
        self,
        db,
        category,
        brand,
        admin_user,
    ) -> None:
        """
        Creating a Product must clear the product list cache prefix.
        """
        list_key = f"{PRODUCTS_LIST_CACHE_PREFIX}_p1_ps12_snewest"
        _seed_cache(list_key)
        assert not _is_cache_miss(list_key)

        Product.objects.create(
            name="Signal Test Product",
            category=category,
            brand=brand,
            sku="SIGNAL-SKU-001",
            price=Decimal("500.00"),
            stock=10,
            status=Product.Status.AVAILABLE,
            created_by=admin_user,
        )

        assert _is_cache_miss(list_key)

    @pytest.mark.unit
    def test_update_invalidates_list_cache(self, product: Product) -> None:
        """
        Updating a Product must clear the product list cache prefix.
        """
        list_key = f"{PRODUCTS_LIST_CACHE_PREFIX}_p1_ps12_snewest"
        _seed_cache(list_key)

        product.price = Decimal("999.00")
        product.save()

        assert _is_cache_miss(list_key)

    @pytest.mark.unit
    def test_update_invalidates_detail_cache(self, product: Product) -> None:
        """
        Updating a Product must clear that product's detail cache key.

        Why exact key:
            Only this product's detail cache needs clearing.
            Other products' detail caches stay warm.
        """
        detail_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{product.slug}"
        _seed_cache(detail_key)

        product.price = Decimal("999.00")
        product.save()

        assert _is_cache_miss(detail_key)

    @pytest.mark.unit
    def test_delete_invalidates_list_cache(self, product: Product) -> None:
        """
        Deleting a Product must clear the product list cache prefix.
        """
        list_key = f"{PRODUCTS_LIST_CACHE_PREFIX}_p1_ps12_snewest"
        _seed_cache(list_key)

        product.delete()

        assert _is_cache_miss(list_key)

    @pytest.mark.unit
    def test_delete_invalidates_detail_cache(self, product: Product) -> None:
        """
        Deleting a Product must clear that product's detail cache key.
        """
        detail_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{product.slug}"
        _seed_cache(detail_key)

        slug = product.slug  # capture before delete
        product.delete()

        assert _is_cache_miss(f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}")

    @pytest.mark.unit
    def test_other_product_detail_cache_untouched(
        self,
        product: Product,
        featured_product: Product,
    ) -> None:
        """
        Updating one product must NOT clear another product's detail cache.

        Why:
            Detail cache is per-slug — exact key, not prefix.
            Only the changed product's cache must be cleared.
            Other products stay warm — no unnecessary DB hits.
        """
        other_detail_key = (
            f"{PRODUCT_DETAIL_CACHE_PREFIX}_{featured_product.slug}"
        )
        _seed_cache(other_detail_key)

        # Update product — must NOT touch featured_product cache
        product.price = Decimal("999.00")
        product.save()

        assert not _is_cache_miss(other_detail_key)


# ─── ProductImage Signal Tests ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductImageSignals:
    """
    ProductImage post_save and post_delete must invalidate:
        - Product list cache (primary_image is in list serializer)
        - Product detail cache (full image gallery is in detail serializer)

    Why image changes affect list cache:
        ProductListSerializer.get_primary_image() returns the primary image URL.
        If a new image is uploaded or primary changes → list cache is stale.

    Why image changes affect detail cache:
        ProductDetailSerializer includes full images[] gallery.
        Any image add/delete/reorder → gallery in cache is stale.
    """

    @pytest.mark.unit
    def test_image_save_invalidates_list_cache(
        self,
        product: Product,
    ) -> None:
        """
        Saving a ProductImage must clear the product list cache.
        """
        list_key = f"{PRODUCTS_LIST_CACHE_PREFIX}_p1_ps12_snewest"
        _seed_cache(list_key)

        fake = SimpleUploadedFile(
            name="signal_test.jpg",
            content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
            content_type="image/jpeg",
        )
        ProductImage.objects.create(
            product=product,
            image=fake,
            is_primary=False,
        )

        assert _is_cache_miss(list_key)

    @pytest.mark.unit
    def test_image_save_invalidates_detail_cache(
        self,
        product: Product,
    ) -> None:
        """
        Saving a ProductImage must clear that product's detail cache.
        """
        detail_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{product.slug}"
        _seed_cache(detail_key)

        fake = SimpleUploadedFile(
            name="signal_test2.jpg",
            content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
            content_type="image/jpeg",
        )
        ProductImage.objects.create(
            product=product,
            image=fake,
            is_primary=True,
        )

        assert _is_cache_miss(detail_key)

    @pytest.mark.unit
    def test_image_delete_invalidates_list_cache(
        self,
        product: Product,
        product_image: ProductImage,
    ) -> None:
        """
        Deleting a ProductImage must clear the product list cache.

        Why:
            Deleted image may have been the primary image.
            List cache would serve broken URL without invalidation.
        """
        list_key = f"{PRODUCTS_LIST_CACHE_PREFIX}_p1_ps12_snewest"
        _seed_cache(list_key)

        product_image.delete()

        assert _is_cache_miss(list_key)

    @pytest.mark.unit
    def test_image_delete_invalidates_detail_cache(
        self,
        product: Product,
        product_image: ProductImage,
    ) -> None:
        """
        Deleting a ProductImage must clear that product's detail cache.

        Why:
            Detail gallery must not show the deleted image.
        """
        detail_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{product.slug}"
        _seed_cache(detail_key)

        product_image.delete()

        assert _is_cache_miss(detail_key)

    @pytest.mark.unit
    def test_image_change_does_not_clear_other_product_detail_cache(
        self,
        product: Product,
        featured_product: Product,
        product_image: ProductImage,
    ) -> None:
        """
        Image change on one product must NOT clear another product's cache.

        Why:
            Image signals use exact slug key — not prefix delete.
            Only the affected product's cache must be cleared.
        """
        other_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{featured_product.slug}"
        _seed_cache(other_key)

        # Delete product's image — must NOT touch featured_product cache
        product_image.delete()

        assert not _is_cache_miss(other_key)