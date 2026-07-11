# apps/products/tests/unit/test_models.py
"""
Unit tests for product app models.

What is tested:
    Category  — slug auto-generation, is_subcategory, save()
    Brand     — slug auto-generation, save()
    BikeModel — slug auto-generation, display_name, covers_year(), save()
    Product   — slug auto-generation, is_in_stock, current_price,
                has_discount, discount_percentage, is_compatible_with()
    ProductImage — is_primary enforcement (only one primary per product)

What is NOT tested here:
    - API responses       → api/ test files
    - Serializer output   → test_serializers.py
    - Cache invalidation  → test_signals.py

Markers:
    @pytest.mark.unit    — no HTTP, no cache
    @pytest.mark.django_db — all tests need DB
"""
from __future__ import annotations

import pytest

from apps.products.models import (
    BikeModel,
    Brand,
    Category,
    Product,
    ProductImage,
)


# ─── Category Model Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCategoryModel:
    """Tests for Category model save(), properties."""

    @pytest.mark.unit
    def test_slug_auto_generated_from_name(self, category: Category) -> None:
        """
        Category.save() must auto-generate slug from name via slugify().

        Why:
            Slug drives the ?category= filter in the product list API.
            If slug is empty, filter returns nothing — silent data bug.
        """
        assert category.slug == "engine-parts"

    @pytest.mark.unit
    def test_slug_not_overwritten_if_already_set(self, db) -> None:
        """
        If slug is explicitly provided, save() must not overwrite it.

        Why:
            Admin may set a custom slug for SEO purposes.
            Auto-generation only fills blank slugs — never overwrites.
        """
        cat = Category.objects.create(name="Brakes", slug="custom-brakes-slug")
        assert cat.slug == "custom-brakes-slug"

    @pytest.mark.unit
    def test_str_returns_name(self, category: Category) -> None:
        assert str(category) == "Engine Parts"

    @pytest.mark.unit
    def test_is_subcategory_false_for_root(self, category: Category) -> None:
        """
        Root category (no parent) must return is_subcategory=False.
        """
        assert category.is_subcategory is False

    @pytest.mark.unit
    def test_is_subcategory_true_for_child(self, subcategory: Category) -> None:
        """
        Category with parent must return is_subcategory=True.
        """
        assert subcategory.is_subcategory is True

    @pytest.mark.unit
    def test_parent_relationship(
        self,
        category: Category,
        subcategory: Category,
    ) -> None:
        """
        Subcategory.parent must point to the root category.
        Root category.subcategories must include the subcategory.
        """
        assert subcategory.parent == category
        assert subcategory in category.subcategories.all()

    @pytest.mark.unit
    def test_unique_name_constraint(self, category: Category) -> None:
        """
        Two categories with the same name must raise IntegrityError.

        Why:
            name is unique=True — enforced at DB level.
            Duplicate names would break slug uniqueness too.
        """
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Category.objects.create(name="Engine Parts")

    @pytest.mark.unit
    def test_unique_slug_constraint(self, db) -> None:
        """
        Two categories with the same slug must raise IntegrityError.
        """
        from django.db import IntegrityError
        Category.objects.create(name="Brakes Alpha", slug="brakes")
        with pytest.raises(IntegrityError):
            Category.objects.create(name="Brakes Beta", slug="brakes")


# ─── Brand Model Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBrandModel:
    """Tests for Brand model save(), str()."""

    @pytest.mark.unit
    def test_slug_auto_generated_from_name(self, brand: Brand) -> None:
        """
        Brand.save() must auto-generate slug from name.
        slug = "honda"
        """
        assert brand.slug == "honda"

    @pytest.mark.unit
    def test_slug_not_overwritten_if_already_set(self, db) -> None:
        """
        Explicit slug must not be overwritten by save().
        """
        b = Brand.objects.create(name="Suzuki", slug="suzuki-motors")
        assert b.slug == "suzuki-motors"

    @pytest.mark.unit
    def test_str_returns_name(self, brand: Brand) -> None:
        assert str(brand) == "Honda"

    @pytest.mark.unit
    def test_unique_name_constraint(self, brand: Brand) -> None:
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Brand.objects.create(name="Honda")


# ─── BikeModel Model Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestBikeModelModel:
    """Tests for BikeModel save(), properties, covers_year()."""

    @pytest.mark.unit
    def test_slug_auto_generated_from_brand_and_name(
        self,
        bike_model: BikeModel,
    ) -> None:
        """
        BikeModel.save() slugifies "{brand.name}-{name}".
        brand=Honda, name=CD70 → slug="honda-cd70"
        """
        assert bike_model.slug == "honda-cd70"

    @pytest.mark.unit
    def test_slug_not_overwritten_if_already_set(
        self,
        db,
        brand: Brand,
    ) -> None:
        bm = BikeModel.objects.create(
            brand=brand,
            name="CB125F",
            slug="custom-cb125f-slug",
            year_start=2020,
        )
        assert bm.slug == "custom-cb125f-slug"

    @pytest.mark.unit
    def test_str_includes_brand_name_and_year_range(
        self,
        bike_model: BikeModel,
    ) -> None:
        """
        __str__ must return "Honda CD70 (2015–2023)".
        """
        assert str(bike_model) == "Honda CD70 (2015–2023)"

    @pytest.mark.unit
    def test_str_shows_present_when_no_year_end(
        self,
        db,
        brand: Brand,
    ) -> None:
        """
        When year_end is None, __str__ must show "present".
        """
        bm = BikeModel.objects.create(
            brand=brand,
            name="CB150F",
            year_start=2020,
            year_end=None,
        )
        assert str(bm) == "Honda CB150F (2020–present)"

    @pytest.mark.unit
    def test_display_name_property(self, bike_model: BikeModel) -> None:
        """
        display_name must return "{brand.name} {name}" without year range.
        """
        assert bike_model.display_name == "Honda CD70"

    @pytest.mark.unit
    def test_covers_year_within_range(self, bike_model: BikeModel) -> None:
        """
        covers_year() must return True for years within production range.
        bike_model: year_start=2015, year_end=2023
        """
        assert bike_model.covers_year(2015) is True
        assert bike_model.covers_year(2019) is True
        assert bike_model.covers_year(2023) is True

    @pytest.mark.unit
    def test_covers_year_outside_range(self, bike_model: BikeModel) -> None:
        """
        covers_year() must return False for years outside production range.
        """
        assert bike_model.covers_year(2014) is False
        assert bike_model.covers_year(2024) is False

    @pytest.mark.unit
    def test_covers_year_no_end_year(self, db, brand: Brand) -> None:
        """
        When year_end is None (still in production),
        covers_year() must return True for any year >= year_start.
        """
        bm = BikeModel.objects.create(
            brand=brand,
            name="CB150F",
            year_start=2020,
            year_end=None,
        )
        assert bm.covers_year(2020) is True
        assert bm.covers_year(2025) is True
        assert bm.covers_year(2019) is False

    @pytest.mark.unit
    def test_unique_together_brand_and_name(
        self,
        db,
        brand: Brand,
        bike_model: BikeModel,
    ) -> None:
        """
        Same brand + same name combination must raise IntegrityError.
        unique_together = [["brand", "name"]]
        """
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            BikeModel.objects.create(
                brand=brand,
                name="CD70",
                year_start=2010,
            )


# ─── Product Model Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductModel:
    """Tests for Product model save(), properties, is_compatible_with()."""

    @pytest.mark.unit
    def test_slug_auto_generated_from_name(self, product: Product) -> None:
        """
        Product.save() slugifies name.
        name="Honda CD70 Brake Shoe Set" → slug="honda-cd70-brake-shoe-set"
        """
        assert product.slug == "honda-cd70-brake-shoe-set"

    @pytest.mark.unit
    def test_slug_not_overwritten_if_already_set(
        self,
        db,
        category: Category,
        brand: Brand,
        admin_user,
    ) -> None:
        p = Product.objects.create(
            name="Test Part",
            slug="my-custom-slug",
            category=category,
            brand=brand,
            sku="CUSTOM-SLUG-SKU",
            price="100.00",
            stock=5,
            created_by=admin_user,
        )
        assert p.slug == "my-custom-slug"

    @pytest.mark.unit
    def test_str_returns_name(self, product: Product) -> None:
        assert str(product) == "Honda CD70 Brake Shoe Set"

    @pytest.mark.unit
    def test_is_in_stock_true_when_stock_and_available(
        self,
        product: Product,
    ) -> None:
        """
        is_in_stock must be True when stock > 0 AND status=AVAILABLE.
        """
        assert product.stock > 0
        assert product.status == Product.Status.AVAILABLE
        assert product.is_in_stock is True

    @pytest.mark.unit
    def test_is_in_stock_false_when_stock_zero(
        self,
        out_of_stock_product: Product,
    ) -> None:
        """
        is_in_stock must be False when stock=0.
        """
        assert out_of_stock_product.is_in_stock is False

    @pytest.mark.unit
    def test_is_in_stock_false_when_status_not_available(
        self,
        db,
        category: Category,
        brand: Brand,
        admin_user,
    ) -> None:
        """
        is_in_stock must be False when status=DISCONTINUED even if stock > 0.

        Why:
            Discontinued products must never show as purchasable.
            Stock field alone is not enough — status must also be AVAILABLE.
        """
        p = Product.objects.create(
            name="Discontinued Part",
            category=category,
            brand=brand,
            sku="DISC-SKU-001",
            price="100.00",
            stock=100,
            status=Product.Status.DISCONTINUED,
            created_by=admin_user,
        )
        assert p.is_in_stock is False

    @pytest.mark.unit
    def test_current_price_returns_regular_price_when_no_discount(
        self,
        product: Product,
    ) -> None:
        """
        current_price must return price when discount_price is None.
        """
        assert product.discount_price is None
        assert product.current_price == product.price

    @pytest.mark.unit
    def test_current_price_returns_discount_price_when_set(
        self,
        discounted_product: Product,
    ) -> None:
        """
        current_price must return discount_price when it is set.
        """
        assert discounted_product.current_price == discounted_product.discount_price

    @pytest.mark.unit
    def test_has_discount_false_when_no_discount_price(
        self,
        product: Product,
    ) -> None:
        assert product.has_discount is False

    @pytest.mark.unit
    def test_has_discount_true_when_discount_price_below_price(
        self,
        discounted_product: Product,
    ) -> None:
        assert discounted_product.has_discount is True

    @pytest.mark.unit
    def test_has_discount_false_when_discount_equals_price(
        self,
        db,
        category: Category,
        brand: Brand,
        admin_user,
    ) -> None:
        """
        has_discount must be False when discount_price == price.

        Why:
            Zero discount is not a real discount.
            Frontend badge must not show "0% off".
        """
        p = Product.objects.create(
            name="Same Price Part",
            category=category,
            brand=brand,
            sku="SAME-PRICE-SKU",
            price="500.00",
            discount_price="500.00",
            stock=10,
            created_by=admin_user,
        )
        assert p.has_discount is False

    @pytest.mark.unit
    def test_discount_percentage_zero_when_no_discount(
        self,
        product: Product,
    ) -> None:
        assert product.discount_percentage == 0

    @pytest.mark.unit
    def test_discount_percentage_calculated_correctly(
        self,
        discounted_product: Product,
    ) -> None:
        """
        discount_percentage = round((1 - discount/price) * 100)
        price=500, discount=400 → (1 - 400/500) * 100 = 20%
        """
        assert discounted_product.discount_percentage == 20

    @pytest.mark.unit
    def test_is_compatible_with_returns_true_for_assigned_bike(
        self,
        compatible_product: Product,
        bike_model: BikeModel,
    ) -> None:
        """
        is_compatible_with() must return True when bike is in compatible_bikes.
        """
        assert compatible_product.is_compatible_with(bike_model.id) is True

    @pytest.mark.unit
    def test_is_compatible_with_returns_false_for_unassigned_bike(
        self,
        product: Product,
        bike_model: BikeModel,
    ) -> None:
        """
        is_compatible_with() must return False when bike not in compatible_bikes.
        product fixture has no compatible_bikes assigned.
        """
        assert product.is_compatible_with(bike_model.id) is False

    @pytest.mark.unit
    def test_unique_sku_constraint(self, product: Product) -> None:
        """
        Two products with same SKU must raise IntegrityError.
        SKU is the unique product identifier across the store.
        """
        from django.db import IntegrityError
        with pytest.raises(IntegrityError):
            Product.objects.create(
                name="Duplicate SKU Part",
                category=product.category,
                sku="TEST-SKU-001",
                price="100.00",
                created_by=product.created_by,
            )


# ─── ProductImage Model Tests ──────────────────────────────────────────────────

@pytest.mark.django_db
class TestProductImageModel:
    """Tests for ProductImage model save() primary image enforcement."""

    @pytest.mark.unit
    def test_str_returns_product_name(
        self,
        product_image: ProductImage,
        product: Product,
    ) -> None:
        assert str(product_image) == f"Image for {product.name}"

    @pytest.mark.unit
    def test_only_one_primary_image_per_product(
        self,
        product: Product,
        product_image: ProductImage,
    ) -> None:
        """
        When a new image is saved with is_primary=True,
        all other images for the same product must be set to is_primary=False.

        Why:
            ProductImage.save() enforces this via:
            ProductImage.objects.filter(product=self.product, is_primary=True)
                                .exclude(id=self.id)
                                .update(is_primary=False)

            Without this, multiple primary images would exist and
            get_primary_image() would return an arbitrary one.
        """
        # product_image is already primary (is_primary=True)
        secondary_file = __import__(
            "django.core.files.uploadedfile",
            fromlist=["SimpleUploadedFile"],
        ).SimpleUploadedFile(
            name="new_primary.jpg",
            content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
            content_type="image/jpeg",
        )
        new_primary = ProductImage.objects.create(
            product=product,
            image=secondary_file,
            is_primary=True,
            order=1,
        )
        # Refresh from DB — product_image must now be non-primary
        product_image.refresh_from_db()

        assert new_primary.is_primary is True
        assert product_image.is_primary is False

    @pytest.mark.unit
    def test_non_primary_image_does_not_affect_existing_primary(
        self,
        product: Product,
        product_image: ProductImage,
    ) -> None:
        """
        Adding a non-primary image must not change existing primary.

        Why:
            save() only runs the unmark logic when self.is_primary=True.
            Adding a non-primary image must leave existing primary untouched.
        """
        secondary_file = __import__(
            "django.core.files.uploadedfile",
            fromlist=["SimpleUploadedFile"],
        ).SimpleUploadedFile(
            name="non_primary.jpg",
            content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
            content_type="image/jpeg",
        )
        ProductImage.objects.create(
            product=product,
            image=secondary_file,
            is_primary=False,
            order=1,
        )
        product_image.refresh_from_db()
        assert product_image.is_primary is True
