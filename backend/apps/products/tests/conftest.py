# apps/products/tests/conftest.py
"""
Product app test configuration — fixtures and constants.

Scope:
    Available to ALL test files inside apps/products/tests/
    and its subdirectories automatically.

What belongs here:
    ✓ User fixtures         — admin, customer (products are admin-managed)
    ✓ Authenticated clients — admin_client, auth_client
    ✓ Model fixtures        — category, brand, bike_model, product, image
    ✓ Payload fixtures      — valid creation payloads
    ✓ Image helper          — SimpleUploadedFile factory

What does NOT belong here:
    ✗ URL constants         — those live in tests/urls.py
    ✗ Test logic            — that goes in individual test files
    ✗ Global fixtures       — api_client, clear_all_caches in root conftest.py
"""
from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from decimal import Decimal

from apps.accounts.models import User
from apps.products.models import (
    BikeModel,
    Brand,
    Category,
    Product,
    ProductImage,
)

# ─── Password constant ─────────────────────────────────────────────────────────
STRONG_PASSWORD = "X!9vQm2#rLpZ"


# ─── User fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def admin_user(db) -> User:
    """
    Superuser with ADMIN role.

    Used for:
        - Write endpoints (POST/PUT/PATCH/DELETE) guarded by IsAdminOrReadOnly
        - Admin-only management tests

    Why create_superuser not create_user:
        create_superuser forces role=ADMIN, is_verified=True, is_staff=True.
        No risk of accidentally creating an admin without correct flags.
    """
    return User.objects.create_superuser(
        email="admin@products.test",
        full_name="Product Admin",
        password=STRONG_PASSWORD,
    )


@pytest.fixture
def customer_user(db) -> User:
    """
    Standard verified customer.

    Used for:
        - Read endpoint tests (GET is public, but customer represents
          a real authenticated user browsing the store)
        - Permission denial tests on write endpoints
    """
    return User.objects.create_user(
        email="customer@products.test",
        full_name="Test Customer",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


# ─── Authenticated clients ─────────────────────────────────────────────────────

@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """
    APIClient force-authenticated as admin_user.

    Why force_authenticate not JWT login:
        JWT login adds HTTP overhead and tests token expiry logic
        which is not relevant to product endpoint tests.
        force_authenticate bypasses auth layer entirely — tests
        only the view/permission logic we actually care about.
    """
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def customer_client(customer_user: User) -> APIClient:
    """
    APIClient force-authenticated as customer_user.

    Used for write-endpoint permission denial tests.
    Customer must receive 403 on POST/PUT/PATCH/DELETE.
    """
    client = APIClient()
    client.force_authenticate(user=customer_user)
    return client


# ─── Image helper ──────────────────────────────────────────────────────────────

@pytest.fixture
def fake_image() -> SimpleUploadedFile:
    """
    Minimal valid JPEG bytes wrapped in SimpleUploadedFile.

    Why SimpleUploadedFile not a real image file:
        - Zero disk I/O — no tmp_path, no cleanup
        - Django's ImageField accepts it without Pillow validation
          in tests (Pillow validates only when VALIDATE_IMAGE=True)
        - Used by Django and DRF themselves in their own test suites

    Why these specific bytes:
        Valid JPEG header (FFD8FF) + minimal body.
        Passes Django's basic content_type check without being a
        full valid JPEG — sufficient for field assignment tests.

    Usage:
        product_image = ProductImage.objects.create(
            product=product,
            image=fake_image,
        )
    """
    return SimpleUploadedFile(
        name="test_product.jpg",
        content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
        content_type="image/jpeg",
    )


# ─── Category fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def category(db) -> Category:
    """
    Root active category — no parent.

    Slug auto-generated from name in Category.save().
    slug = "engine-parts"
    """
    return Category.objects.create(
        name="Engine Parts",
        is_active=True,
    )


@pytest.fixture
def subcategory(db, category: Category) -> Category:
    """
    Active subcategory — parent is `category` fixture.

    Used for:
        - is_subcategory property tests
        - parent_name serializer field tests
        - Tree view structure tests

    slug = "pistons"
    """
    return Category.objects.create(
        name="Pistons",
        parent=category,
        is_active=True,
    )


@pytest.fixture
def inactive_category(db) -> Category:
    """
    Inactive category — must never appear in API responses.

    Used for:
        - Confirming is_active=False filters work
        - Category list returns only active categories
    """
    return Category.objects.create(
        name="Discontinued Parts",
        is_active=False,
    )


# ─── Brand fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def brand(db) -> Brand:
    """
    Active brand — Honda.

    slug = "honda"
    """
    return Brand.objects.create(
        name="Honda",
        is_active=True,
    )


@pytest.fixture
def second_brand(db) -> Brand:
    """
    Second active brand — Yamaha.

    Used for:
        - ?brand= filter isolation tests
        - Multiple brand listing tests
    """
    return Brand.objects.create(
        name="Yamaha",
        is_active=True,
    )


@pytest.fixture
def inactive_brand(db) -> Brand:
    """
    Inactive brand — must never appear in API responses.
    """
    return Brand.objects.create(
        name="Defunct Motors",
        is_active=False,
    )


# ─── BikeModel fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def bike_model(db, brand: Brand) -> BikeModel:
    """
    Active Honda CD70 bike model.

    Used for:
        - Compatibility filter tests (?bike_model=<id>)
        - BikeModel list tests
        - Product compatibility tests

    slug = "honda-cd70"
    """
    return BikeModel.objects.create(
        brand=brand,
        name="CD70",
        year_start=2015,
        year_end=2023,
        is_active=True,
    )


@pytest.fixture
def second_bike_model(db, second_brand: Brand) -> BikeModel:
    """
    Active Yamaha YBR125 bike model.

    Used for:
        - ?brand= filter isolation on bike model list
        - Multiple compatible bikes on a product
    """
    return BikeModel.objects.create(
        brand=second_brand,
        name="YBR125",
        year_start=2018,
        is_active=True,
    )


@pytest.fixture
def inactive_bike_model(db, brand: Brand) -> BikeModel:
    """
    Inactive bike model — must never appear in API responses.
    """
    return BikeModel.objects.create(
        brand=brand,
        name="Old Model",
        year_start=2000,
        year_end=2005,
        is_active=False,
    )


# ─── Product fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def product(db, category: Category, brand: Brand, admin_user: User) -> Product:
    """
    Standard available product with all required fields.

    SKU is unique — "TEST-SKU-001".
    slug auto-generated = "honda-cd70-brake-shoe-set"

    Used as the baseline product for most tests.
    """
    return Product.objects.create(
        name="Honda CD70 Brake Shoe Set",
        category=category,
        brand=brand,
        sku="TEST-SKU-001",
        price="850.00",
        stock=10,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )


@pytest.fixture
def discounted_product(
    db,
    category: Category,
    brand: Brand,
    admin_user: User,
) -> Product:
    """
    Product with discount_price set below regular price.

    Used for:
        - has_discount=True tests
        - discount_percentage calculation tests
        - current_price returns discount_price tests
    """
    return Product.objects.create(
        name="Discounted Air Filter",
        category=category,
        brand=brand,
        sku="TEST-SKU-002",
        price=Decimal("500.00"),
        discount_price=Decimal("400.00"),
        stock=5,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )


@pytest.fixture
def out_of_stock_product(
    db,
    category: Category,
    brand: Brand,
    admin_user: User,
) -> Product:
    """
    Product with stock=0 and status=OUT_OF_STOCK.

    Used for:
        - is_in_stock=False tests
        - Product list excludes out-of-stock (status filter)
        - Related products excludes out-of-stock
    """
    return Product.objects.create(
        name="Out Of Stock Chain Kit",
        category=category,
        brand=brand,
        sku="TEST-SKU-003",
        price="1200.00",
        stock=0,
        status=Product.Status.OUT_OF_STOCK,
        created_by=admin_user,
    )


@pytest.fixture
def featured_product(
    db,
    category: Category,
    brand: Brand,
    admin_user: User,
) -> Product:
    """
    Featured available product.

    Used for:
        - ?featured=true filter tests
        - sort=featured ordering tests
    """
    return Product.objects.create(
        name="Featured Spark Plug",
        category=category,
        brand=brand,
        sku="TEST-SKU-004",
        price="150.00",
        stock=50,
        status=Product.Status.AVAILABLE,
        is_featured=True,
        created_by=admin_user,
    )


@pytest.fixture
def universal_product(
    db,
    category: Category,
    admin_user: User,
) -> Product:
    """
    Product with no brand and no compatible_bikes.

    Used for:
        - primary_bike returns "Universal" tests
        - brand_name returns None tests
        - Universal parts filtering tests
    """
    return Product.objects.create(
        name="Universal Engine Oil",
        category=category,
        brand=None,
        sku="TEST-SKU-005",
        price="300.00",
        stock=100,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )


@pytest.fixture
def compatible_product(
    db,
    category: Category,
    brand: Brand,
    bike_model: BikeModel,
    admin_user: User,
) -> Product:
    """
    Product with compatible_bikes assigned.

    Used for:
        - ?bike_model= compatibility filter tests
        - is_compatible_with() method tests
        - primary_bike serializer field tests
    """
    p = Product.objects.create(
        name="CD70 Piston Ring Set",
        category=category,
        brand=brand,
        sku="TEST-SKU-006",
        price="650.00",
        stock=20,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )
    p.compatible_bikes.add(bike_model)
    return p


# ─── ProductImage fixtures ─────────────────────────────────────────────────────

@pytest.fixture
def product_image(db, product: Product, fake_image: SimpleUploadedFile) -> ProductImage:
    """
    Primary image for `product`.

    Used for:
        - primary_image serializer field tests
        - Image gallery in detail serializer tests
        - Signal invalidation on image save/delete tests
    """
    return ProductImage.objects.create(
        product=product,
        image=fake_image,
        is_primary=True,
        order=0,
    )


@pytest.fixture
def secondary_image(db, product: Product) -> ProductImage:
    """
    Non-primary image for `product`.

    Used for:
        - Fallback image logic tests (no primary → use first)
        - Multiple image ordering tests
        - Primary image promotion tests
    """
    secondary_file = SimpleUploadedFile(
        name="secondary.jpg",
        content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
        content_type="image/jpeg",
    )
    return ProductImage.objects.create(
        product=product,
        image=secondary_file,
        is_primary=False,
        order=1,
    )