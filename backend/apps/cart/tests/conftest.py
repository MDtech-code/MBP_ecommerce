# apps/cart/tests/conftest.py
"""
Cart app test configuration — fixtures and constants.

Scope:
    Available to ALL test files inside apps/cart/tests/
    and its subdirectories automatically.

What belongs here:
    ✓ URL constants        — single source of truth for cart endpoints
    ✓ User fixtures        — customer with cart, second customer
    ✓ Authenticated clients — auth_client for cart operations
    ✓ Cart fixtures        — empty cart, cart with items
    ✓ CartItem fixtures    — single item, multiple items
    ✓ Product fixtures     — reused from products app patterns

What does NOT belong here:
    ✗ URL constants        — those live in tests/urls.py
    ✗ Test logic           — that goes in individual test files
    ✗ Global fixtures      — api_client, clear_all_caches in root conftest.py
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.cart.models import Cart, CartItem
from apps.products.models import Brand, Category, Product, ProductImage


# ─── Password constant ─────────────────────────────────────────────────────────

STRONG_PASSWORD = "X!9vQm2#rLpZ"


# ─── URL Constants — single source of truth ───────────────────────────────────

CART_DETAIL_URL  = "/api/cart/"
CART_ADD_URL     = "/api/cart/items/"
CART_CLEAR_URL   = "/api/cart/clear/"


def cart_item_url(item_id: int) -> str:
    """Dynamic URL for PATCH/DELETE on a specific cart item."""
    return f"/api/cart/items/{item_id}/"


# ─── User Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def user(db) -> User:
    """
    Standard verified customer with auto-created cart.

    Cart is created via post_save signal on User creation.
    This is the primary user for all cart operation tests.
    """
    return User.objects.create_user(
        email="cartuser@test.com",
        full_name="Cart User",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


@pytest.fixture
def other_user(db) -> User:
    """
    Second verified customer with their own cart.

    Used for:
        - Ownership isolation tests (user cannot modify other's cart)
        - Cart item not found when wrong user tries to access
    """
    return User.objects.create_user(
        email="otheruser@test.com",
        full_name="Other User",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


# ─── Authenticated Clients ────────────────────────────────────────────────────

@pytest.fixture
def auth_client(user: User) -> APIClient:
    """
    APIClient force-authenticated as the standard `user`.

    Why force_authenticate not JWT login:
        JWT login adds HTTP overhead not relevant to cart logic tests.
        force_authenticate bypasses auth layer — tests only cart logic.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_client(other_user: User) -> APIClient:
    """
    APIClient force-authenticated as `other_user`.

    Used for cart item ownership isolation tests.
    """
    client = APIClient()
    client.force_authenticate(user=other_user)
    return client


# ─── Product Infrastructure ───────────────────────────────────────────────────
# Minimal product setup needed for cart tests.
# Mirrors products/tests/conftest.py patterns exactly.

@pytest.fixture
def admin_user(db) -> User:
    """Superuser needed as product created_by field."""
    return User.objects.create_superuser(
        email="admin@cart.test",
        full_name="Cart Admin",
        password=STRONG_PASSWORD,
    )


@pytest.fixture
def category(db) -> Category:
    """Root active category for test products."""
    return Category.objects.create(
        name="Engine Parts",
        is_active=True,
    )


@pytest.fixture
def brand(db) -> Brand:
    """Active brand for test products."""
    return Brand.objects.create(
        name="Honda",
        is_active=True,
    )


@pytest.fixture
def fake_image() -> SimpleUploadedFile:
    """Minimal valid JPEG for product image tests."""
    return SimpleUploadedFile(
        name="test_product.jpg",
        content=b"\xff\xd8\xff\xe0" + b"\x00" * 20,
        content_type="image/jpeg",
    )


# ─── Product Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def product(db, category: Category, brand: Brand, admin_user: User) -> Product:
    """
    Standard available product — 10 units in stock.

    Used as the primary product for add-to-cart tests.
    price = 850.00, stock = 10, status = AVAILABLE
    """
    return Product.objects.create(
        name="Honda CD70 Brake Shoe Set",
        category=category,
        brand=brand,
        sku="CART-SKU-001",
        price=Decimal("850.00"),
        stock=10,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )


@pytest.fixture
def second_product(db, category: Category, brand: Brand, admin_user: User) -> Product:
    """
    Second available product — 5 units in stock.

    Used for:
        - Multiple items in cart tests
        - total_price calculation with mixed items
        - Cart clear removes all items tests
    """
    return Product.objects.create(
        name="Honda CD70 Air Filter",
        category=category,
        brand=brand,
        sku="CART-SKU-002",
        price=Decimal("350.00"),
        stock=5,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )


@pytest.fixture
def low_stock_product(db, category: Category, brand: Brand, admin_user: User) -> Product:
    """
    Product with only 2 units in stock.

    Used for:
        - Stock exceeded validation tests
        - Quantity cap at stock boundary tests
        - Upsert quantity + existing exceeds stock tests
    """
    return Product.objects.create(
        name="Rare Carburetor Kit",
        category=category,
        brand=brand,
        sku="CART-SKU-003",
        price=Decimal("1200.00"),
        stock=2,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )


@pytest.fixture
def unavailable_product(db, category: Category, brand: Brand, admin_user: User) -> Product:
    """
    Product with OUT_OF_STOCK status.

    Used for:
        - Add to cart rejects unavailable product tests
        - Serializer validate() status check tests
    """
    return Product.objects.create(
        name="Discontinued Chain Kit",
        category=category,
        brand=brand,
        sku="CART-SKU-004",
        price=Decimal("999.00"),
        stock=0,
        status=Product.Status.OUT_OF_STOCK,
        created_by=admin_user,
    )


@pytest.fixture
def draft_product(db, category: Category, brand: Brand, admin_user: User) -> Product:
    """
    Product with DRAFT status — not publicly available.

    Used for:
        - Serializer rejects DRAFT status products
        - Only AVAILABLE products can be added to cart
    """
    return Product.objects.create(
        name="Draft Spark Plug",
        category=category,
        brand=brand,
        sku="CART-SKU-005",
        price=Decimal("120.00"),
        stock=50,
        status=Product.Status.DISCONTINUED,
        created_by=admin_user,
    )


@pytest.fixture
def product_with_image(
    db,
    product: Product,
    fake_image: SimpleUploadedFile,
) -> Product:
    """
    The standard `product` with a primary image attached.

    Used for:
        - CartItemSerializer.get_product_image() tests
        - Image URL resolution in cart response tests
    """
    ProductImage.objects.create(
        product=product,
        image=fake_image,
        is_primary=True,
        order=0,
    )
    return product


# ─── Cart Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def cart(user: User) -> Cart:
    """
    The auto-created empty cart for `user`.

    Why not Cart.objects.create():
        Signal already created the cart when user was created.
        Fetching it here ensures we test the real signal-created cart,
        not a duplicate created by the test setup.

    Used as the baseline for all cart operation tests.
    """
    return Cart.objects.get(user=user)


@pytest.fixture
def other_cart(other_user: User) -> Cart:
    """
    The auto-created empty cart for `other_user`.

    Used for ownership isolation tests.
    """
    return Cart.objects.get(user=other_user)


# ─── CartItem Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def cart_item(cart: Cart, product: Product) -> CartItem:
    """
    Single CartItem — 2 units of `product` in `user`'s cart.

    Created directly via model — no HTTP request.
    Use when tests need an existing item to operate on
    (update quantity, delete, clear) without testing creation.

    quantity=2, subtotal = 2 × 850.00 = 1700.00
    """
    return CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=2,
    )


@pytest.fixture
def second_cart_item(cart: Cart, second_product: Product) -> CartItem:
    """
    Second CartItem — 1 unit of `second_product` in `user`'s cart.

    Used with `cart_item` for multi-item cart tests.
    quantity=1, subtotal = 1 × 350.00 = 350.00

    Combined with cart_item:
        total_items = 3
        total_price = 1700.00 + 350.00 = 2050.00
    """
    return CartItem.objects.create(
        cart=cart,
        product=second_product,
        quantity=1,
    )


@pytest.fixture
def other_cart_item(other_cart: Cart, product: Product) -> CartItem:
    """
    CartItem in `other_user`'s cart — same product as `cart_item`.

    Used for:
        - User cannot PATCH/DELETE another user's cart item
        - Item not found response when wrong user requests item
    """
    return CartItem.objects.create(
        cart=other_cart,
        product=product,
        quantity=1,
    )



@pytest.fixture
def discounted_product(
    db, category: Category, brand: Brand, admin_user: User
) -> Product:
    """
    Product with discount_price set below regular price.

    Used for:
        - subtotal uses current_price (discount-aware) tests
        - total_price uses discounted price tests

    price=500.00, discount_price=400.00
    current_price = 400.00
    """
    return Product.objects.create(
        name="Discounted Air Filter",
        category=category,
        brand=brand,
        sku="CART-SKU-DISC-001",
        price=Decimal("500.00"),
        discount_price=Decimal("400.00"),
        stock=5,
        status=Product.Status.AVAILABLE,
        created_by=admin_user,
    )
