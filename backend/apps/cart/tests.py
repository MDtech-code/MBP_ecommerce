# apps/cart/tests.py
from __future__ import annotations

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.products.models import Product,Category
from .models import Cart, CartItem

# ─── Constants ────────────────────────────────────────────────────────────────

CART_URL        = "/api/cart/"
CART_ITEMS_URL  = "/api/cart/items/"
CART_CLEAR_URL  = "/api/cart/clear/"
STRONG_PASSWORD = "X!9vQm2#rLpZ"


def cart_item_url(item_id: int) -> str:
    return f"/api/cart/items/{item_id}/"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    """Verified customer with auto-created cart via signal."""
    return User.objects.create_user(
        email="customer@test.com",
        full_name="Test Customer",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


@pytest.fixture
def another_user(db) -> User:
    """Second verified user — used for ownership isolation tests."""
    return User.objects.create_user(
        email="other@test.com",
        full_name="Other Customer",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


@pytest.fixture
def auth_client(user: User) -> APIClient:
    """
    Authenticated client — creates its own APIClient instance.
    Does NOT share the api_client fixture to prevent state leakage.
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def another_auth_client(another_user: User) -> APIClient:
    """Authenticated client for the second user."""
    client = APIClient()
    client.force_authenticate(user=another_user)
    return client


@pytest.fixture
def cart(user: User) -> Cart:
    """The auto-created cart for the primary user."""
    return Cart.objects.get(user=user)


@pytest.fixture
def another_cart(another_user: User) -> Cart:
    """The auto-created cart for the second user."""
    return Cart.objects.get(user=another_user)


@pytest.fixture
def category(db) -> Category:
    """Category required for product creation (non-null FK)."""
    return Category.objects.create(
        name="Brake Parts",
        slug="brake-parts",
    )
@pytest.fixture
def product(db, category: Category) -> Product:
    """Available product with stock=10 for cart testing."""
    return Product.objects.create(
        name="Test Brake Pad",
        slug="test-brake-pad",
        sku="BRK-TEST-001",
        category=category,
        price=Decimal("500.00"),
        stock=10,
        status=Product.Status.AVAILABLE,
    )


@pytest.fixture
def out_of_stock_product(db, category: Category) -> Product:
    """Product with zero stock — used for stock validation tests."""
    return Product.objects.create(
        name="Out Of Stock Part",
        slug="out-of-stock-part",
        sku="OOS-TEST-001",
        category=category,
        price=Decimal("200.00"),
        stock=0,
        status=Product.Status.AVAILABLE,
    )


@pytest.fixture
def unavailable_product(db, category: Category) -> Product:
    """Product with non-available status — cannot be added to cart."""
    return Product.objects.create(
        name="Unavailable Part",
        slug="unavailable-part",
        sku="UNA-TEST-001",
        category=category,
        price=Decimal("300.00"),
        stock=5,
        status=Product.Status.DISCONTINUED,
    )


@pytest.fixture
def cart_item(cart: Cart, product: Product) -> CartItem:
    """A CartItem already in the user's cart with quantity=2."""
    return CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=2,
    )


# ─── Signal Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartSignal:
    """
    Tests for post_save signal that auto-creates Cart on User creation.

    Coverage:
        - Cart created automatically on user creation
        - Cart is empty on creation
        - Second save does not create duplicate cart
        - Each user gets their own cart
    """

    def test_cart_created_on_user_creation(self, user: User):
        """Cart must exist immediately after user creation."""
        assert Cart.objects.filter(user=user).exists()

    def test_cart_is_empty_on_creation(self, user: User):
        """Newly created cart must have no items."""
        cart = Cart.objects.get(user=user)
        assert cart.is_empty is True
        assert cart.total_items == 0

    def test_cart_not_duplicated_on_user_save(self, user: User):
        """
        Saving an existing user must not create a second cart.
        Signal guard (if not created) prevents this.
        """
        user.full_name = "Updated Name"
        user.save()
        assert Cart.objects.filter(user=user).count() == 1

    def test_each_user_gets_own_cart(self, user: User, another_user: User):
        """Two users must have two separate carts."""
        assert Cart.objects.filter(user=user).count() == 1
        assert Cart.objects.filter(user=another_user).count() == 1
        assert (
            Cart.objects.get(user=user).id
            != Cart.objects.get(user=another_user).id
        )


# ─── Cart Model Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartModel:
    """
    Tests for Cart and CartItem model logic.

    Coverage:
        - total_items sums quantities correctly
        - total_price computes correctly as Decimal
        - is_empty reflects item state
        - subtotal is Decimal not float
        - CartItem clean() blocks quantity > stock
        - unique_together prevents duplicate product in cart
    """

    def test_total_items_sums_quantities(self, cart: Cart, product: Product):
        """total_items must sum all item quantities."""
        CartItem.objects.create(cart=cart, product=product, quantity=3)
        assert cart.total_items == 3

    def test_total_price_correct(self, cart: Cart, product: Product):
        """total_price = sum(quantity * current_price) for all items."""
        CartItem.objects.create(cart=cart, product=product, quantity=2)
        expected = Decimal("500.00") * 2
        assert cart.total_price == expected

    def test_total_price_returns_decimal(self, cart: Cart, product: Product):
        """total_price must be Decimal — never float for monetary values."""
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        assert isinstance(cart.total_price, Decimal)

    def test_total_price_zero_when_empty(self, cart: Cart):
        """total_price must be Decimal('0.00') for empty cart."""
        assert cart.total_price == Decimal("0.00")

    def test_is_empty_true_when_no_items(self, cart: Cart):
        assert cart.is_empty is True

    def test_is_empty_false_when_has_items(self, cart: Cart, product: Product):
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        assert cart.is_empty is False

    def test_subtotal_is_decimal(self, cart: Cart, product: Product):
        """CartItem.subtotal must be Decimal."""
        item = CartItem.objects.create(cart=cart, product=product, quantity=2)
        assert isinstance(item.subtotal, Decimal)

    def test_subtotal_correct(self, cart: Cart, product: Product):
        """subtotal = quantity * current_price."""
        item = CartItem.objects.create(cart=cart, product=product, quantity=3)
        assert item.subtotal == Decimal("500.00") * 3

    def test_cartitem_clean_blocks_over_stock(
        self, cart: Cart, product: Product
    ):
        """
        CartItem.clean() must raise ValidationError when
        quantity > product.stock (stock=10).
        """
        from django.core.exceptions import ValidationError
        item = CartItem(cart=cart, product=product, quantity=999)
        with pytest.raises(ValidationError):
            item.clean()

    def test_cartitem_unique_together(self, cart: Cart, product: Product):
        """Same product cannot appear twice in the same cart."""
        from django.core.exceptions import ValidationError

        CartItem.objects.create(cart=cart, product=product, quantity=1)

        with pytest.raises(ValidationError):
         CartItem.objects.create(cart=cart, product=product, quantity=1)
 
 
# ─── Cart Detail Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestCartDetail:
    """
    Tests for GET /api/cart/

    Coverage:
        - Happy path (cart returned)
        - Response shape conformance
        - Empty cart returns is_empty=True
        - Items appear in response
        - Unauthenticated request blocked
    """

    def test_get_cart_returns_200(self, auth_client: APIClient):
        response = auth_client.get(CART_URL, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_get_cart_response_shape(self, auth_client: APIClient):
        """Response must conform to standardized envelope."""
        response = auth_client.get(CART_URL, format="json")
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data
        cart_data = data["data"]
        assert "id" in cart_data
        assert "items" in cart_data
        assert "total_items" in cart_data
        assert "total_price" in cart_data
        assert "is_empty" in cart_data

    def test_get_cart_empty_on_fresh_account(self, auth_client: APIClient):
        """Newly created user's cart must be empty."""
        response = auth_client.get(CART_URL, format="json")
        assert response.data["data"]["is_empty"] is True
        assert response.data["data"]["total_items"] == 0
        assert response.data["data"]["items"] == []

    def test_get_cart_shows_items(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Cart with items must return them in the items list."""
        response = auth_client.get(CART_URL, format="json")
        assert len(response.data["data"]["items"]) == 1
        assert response.data["data"]["total_items"] == cart_item.quantity

    def test_get_cart_unauthenticated_returns_401(self, api_client: APIClient):
        response = api_client.get(CART_URL, format="json")
        assert response.status_code == 401


# ─── Add To Cart Tests ────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAddToCart:
    """
    Tests for POST /api/cart/items/

    Coverage:
        - Happy path (item added, 201 returned)
        - Response shape conformance
        - Adding same product increases quantity (upsert)
        - Quantity defaults to 1 if not provided
        - Product not found returns 400
        - Unavailable product returns 400
        - Quantity exceeds stock returns 400 on correct field
        - Upsert exceeding stock returns 400
        - Zero quantity returns 400 (min_value=1 for add)
        - Missing product_id returns 400
        - Unauthenticated request blocked
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_add_to_cart_returns_201(
        self, auth_client: APIClient, product: Product
    ):
        """First add must return 201."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        assert response.status_code == 201
        assert response.data["success"] is True

    def test_add_to_cart_response_shape(
        self, auth_client: APIClient, product: Product
    ):
        """Response must conform to standardized envelope."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data
        assert "items" in data["data"]

    def test_add_to_cart_creates_cart_item(
        self, auth_client: APIClient, product: Product, cart: Cart
    ):
        """CartItem must exist in DB after add."""
        auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 2},
            format="json",
        )
        assert CartItem.objects.filter(cart=cart, product=product).exists()

    def test_add_to_cart_correct_quantity(
        self, auth_client: APIClient, product: Product, cart: Cart
    ):
        """CartItem quantity must match the requested quantity."""
        auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 3},
            format="json",
        )
        item = CartItem.objects.get(cart=cart, product=product)
        assert item.quantity == 3

    def test_add_to_cart_default_quantity_is_one(
        self, auth_client: APIClient, product: Product, cart: Cart
    ):
        """Omitting quantity must default to 1."""
        auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id},
            format="json",
        )
        item = CartItem.objects.get(cart=cart, product=product)
        assert item.quantity == 1

    def test_add_same_product_increases_quantity(
        self, auth_client: APIClient, product: Product, cart: Cart
    ):
        """
        Adding same product twice must upsert — increase quantity,
        not create a duplicate CartItem.
        """
        auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 2},
            format="json",
        )
        auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 3},
            format="json",
        )
        assert CartItem.objects.filter(cart=cart, product=product).count() == 1
        item = CartItem.objects.get(cart=cart, product=product)
        assert item.quantity == 5

    def test_add_to_cart_response_includes_updated_totals(
        self, auth_client: APIClient, product: Product
    ):
        """Response must reflect updated cart totals after add."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 2},
            format="json",
        )
        cart_data = response.data["data"]
        assert cart_data["total_items"] == 2
        assert Decimal(str(cart_data["total_price"])) == Decimal("500.00") * 2

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_add_nonexistent_product_returns_400(self, auth_client: APIClient):
        """Non-existent product_id must return 400."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": 99999, "quantity": 1},
            format="json",
        )
        assert response.status_code == 400
        assert "product_id" in response.data["errors"]

    def test_add_unavailable_product_returns_400(
        self, auth_client: APIClient, unavailable_product: Product
    ):
        """Product with UNAVAILABLE status must return 400."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": unavailable_product.id, "quantity": 1},
            format="json",
        )
        assert response.status_code == 400
        assert "product_id" in response.data["errors"]

    def test_add_quantity_exceeds_stock_returns_400(
        self, auth_client: APIClient, product: Product
    ):
        """Quantity > stock must return 400 on quantity field."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 999},
            format="json",
        )
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    def test_add_zero_quantity_returns_400(
        self, auth_client: APIClient, product: Product
    ):
        """
        Quantity=0 on ADD must return 400.
        min_value=1 enforced on AddToCartSerializer.
        Note: quantity=0 on UPDATE auto-deletes (different behaviour).
        """
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 0},
            format="json",
        )
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    def test_add_missing_product_id_returns_400(self, auth_client: APIClient):
        """Missing product_id field must return 400."""
        response = auth_client.post(
            CART_ITEMS_URL,
            {"quantity": 1},
            format="json",
        )
        assert response.status_code == 400
        assert "product_id" in response.data["errors"]

    def test_upsert_exceeding_stock_returns_400(
        self, auth_client: APIClient, product: Product, cart: Cart
    ):
        """
        If existing quantity + new quantity > stock, must return 400.
        product stock=10. existing=8. adding 5 = 13 > 10.
        """
        CartItem.objects.create(cart=cart, product=product, quantity=8)
        response = auth_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 5},
            format="json",
        )
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    def test_add_to_cart_unauthenticated_returns_401(
        self, api_client: APIClient, product: Product
    ):
        response = api_client.post(
            CART_ITEMS_URL,
            {"product_id": product.id, "quantity": 1},
            format="json",
        )
        assert response.status_code == 401


# ─── Update Cart Item Tests ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestUpdateCartItem:
    """
    Tests for PATCH /api/cart/items/<item_id>/

    Behaviour summary:
        quantity > 0  → set absolute quantity (replaces current value)
        quantity = 0  → auto-delete the item (frontend − button on qty=1)
        quantity < 0  → 400 (invalid)
        quantity > stock → 400 (stock exceeded)

    Coverage:
        - Happy path (quantity updated, cart returned)
        - Response shape conformance
        - PUT also accepted (alias)
        - Quantity set is absolute not delta
        - quantity=0 auto-deletes item and returns 200
        - quantity=0 returns empty cart
        - Negative quantity returns 400
        - Quantity exceeds stock returns 400
        - Missing quantity returns 400
        - Item not found returns 404
        - Ownership isolation (user B cannot update user A's item)
        - Unauthenticated request blocked
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_update_item_returns_200(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Valid quantity update must return 200."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 3},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_update_item_response_shape(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Response must conform to standardized envelope."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 3},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_update_item_persists_quantity(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Updated quantity must be saved to DB."""
        auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 5},
            format="json",
        )
        cart_item.refresh_from_db()
        assert cart_item.quantity == 5

    def test_update_item_sets_absolute_not_delta(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """
        PATCH sets absolute quantity — not a delta increment.
        cart_item starts at quantity=2. Sending 4 sets it to 4, not 6.
        Frontend calculates the desired final value before sending.
        """
        auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 4},
            format="json",
        )
        cart_item.refresh_from_db()
        assert cart_item.quantity == 4  # absolute set, not 2+4=6

    def test_update_item_response_reflects_new_quantity(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Response cart data must contain the updated quantity."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 4},
            format="json",
        )
        items = response.data["data"]["items"]
        updated = next(i for i in items if i["id"] == cart_item.id)
        assert updated["quantity"] == 4

    def test_put_also_accepted(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """PUT must be accepted as alias for PATCH."""
        response = auth_client.put(
            cart_item_url(cart_item.id),
            {"quantity": 2},
            format="json",
        )
        assert response.status_code == 200

    # ── quantity=0 Auto-Delete ────────────────────────────────────────────────

    def test_update_item_zero_quantity_auto_deletes_item(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """
        quantity=0 must auto-delete the item and return 200.

        This supports the frontend − button on quantity=1 use case.
        Rather than returning a 400 error, the item is cleanly removed.
        """
        item_id = cart_item.id
        response = auth_client.patch(
            cart_item_url(item_id),
            {"quantity": 0},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True
        assert not CartItem.objects.filter(id=item_id).exists()

    def test_update_item_zero_quantity_returns_empty_cart(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """
        After quantity=0 auto-delete, response must show empty cart.
        cart_item is the only item — cart becomes empty after delete.
        """
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 0},
            format="json",
        )
        assert response.data["data"]["is_empty"] is True
        assert response.data["data"]["total_items"] == 0
        assert response.data["data"]["items"] == []

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_update_item_negative_quantity_returns_400(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """
        Negative quantity must return 400.
        min_value=0 is enforced — only 0 is valid as special auto-delete.
        """
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": -1},
            format="json",
        )
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    def test_update_item_exceeds_stock_returns_400(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """quantity > stock (10) must return 400 on quantity field."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 999},
            format="json",
        )
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    def test_update_item_missing_quantity_returns_400(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Missing quantity field must return 400."""
        response = auth_client.patch(
            cart_item_url(cart_item.id),
            {},
            format="json",
        )
        assert response.status_code == 400
        assert "quantity" in response.data["errors"]

    # ── Ownership & Auth ──────────────────────────────────────────────────────

    def test_update_item_not_found_returns_404(
        self, auth_client: APIClient
    ):
        """Non-existent item_id must return 404."""
        response = auth_client.patch(
            cart_item_url(99999),
            {"quantity": 1},
            format="json",
        )
        assert response.status_code == 404

    def test_cannot_update_another_users_cart_item(
        self,
        another_auth_client: APIClient,
        cart_item: CartItem,
    ):
        """
        User B must not be able to update User A's cart item.
        Returns 404 — not 403 — to avoid exposing item existence.
        """
        response = another_auth_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 1},
            format="json",
        )
        assert response.status_code == 404

    def test_update_item_unauthenticated_returns_401(
        self, api_client: APIClient, cart_item: CartItem
    ):
        response = api_client.patch(
            cart_item_url(cart_item.id),
            {"quantity": 1},
            format="json",
        )
        assert response.status_code == 401


# ─── Remove Cart Item Tests ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestRemoveCartItem:
    """
    Tests for DELETE /api/cart/items/<item_id>/

    Coverage:
        - Happy path (item removed, cart returned)
        - Response shape conformance
        - Item removed from DB
        - Cart totals updated after removal
        - Item not found returns 404
        - Ownership isolation (user B cannot remove user A's item)
        - Unauthenticated request blocked
    """

    def test_remove_item_returns_200(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Valid delete must return 200."""
        response = auth_client.delete(
            cart_item_url(cart_item.id),
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_remove_item_response_shape(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Response must conform to standardized envelope."""
        response = auth_client.delete(
            cart_item_url(cart_item.id),
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_remove_item_deletes_from_db(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """CartItem must not exist in DB after deletion."""
        item_id = cart_item.id
        auth_client.delete(cart_item_url(item_id), format="json")
        assert not CartItem.objects.filter(id=item_id).exists()

    def test_remove_item_cart_becomes_empty(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Cart must show is_empty=True after last item removed."""
        response = auth_client.delete(
            cart_item_url(cart_item.id),
            format="json",
        )
        assert response.data["data"]["is_empty"] is True
        assert response.data["data"]["total_items"] == 0

    def test_remove_item_not_found_returns_404(
        self, auth_client: APIClient
    ):
        response = auth_client.delete(
            cart_item_url(99999),
            format="json",
        )
        assert response.status_code == 404

    def test_cannot_remove_another_users_cart_item(
        self,
        another_auth_client: APIClient,
        cart_item: CartItem,
    ):
        """
        User B must not be able to delete User A's cart item.
        Returns 404 — not 403 — to avoid exposing item existence.
        """
        response = another_auth_client.delete(
            cart_item_url(cart_item.id),
            format="json",
        )
        assert response.status_code == 404
        assert CartItem.objects.filter(id=cart_item.id).exists()

    def test_remove_item_unauthenticated_returns_401(
        self, api_client: APIClient, cart_item: CartItem
    ):
        response = api_client.delete(
            cart_item_url(cart_item.id),
            format="json",
        )
        assert response.status_code == 401


# ─── Clear Cart Tests ─────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestClearCart:
    """
    Tests for DELETE /api/cart/clear/

    Coverage:
        - Happy path (all items removed, empty cart returned)
        - Response shape conformance
        - All items deleted from DB
        - Clearing already-empty cart returns 200 (idempotent)
        - Does not affect other users' carts
        - Unauthenticated request blocked
    """

    def test_clear_cart_returns_200(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Clear must return 200 with success=True."""
        response = auth_client.delete(CART_CLEAR_URL, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_clear_cart_response_shape(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Response must conform to standardized envelope."""
        response = auth_client.delete(CART_CLEAR_URL, format="json")
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_clear_cart_removes_all_items_from_db(
        self, auth_client: APIClient, cart: Cart, product: Product
    ):
        """All CartItems must be deleted from DB after clear."""
        CartItem.objects.create(cart=cart, product=product, quantity=1)
        auth_client.delete(CART_CLEAR_URL, format="json")
        assert CartItem.objects.filter(cart=cart).count() == 0

    def test_clear_cart_returns_empty_cart(
        self, auth_client: APIClient, cart_item: CartItem
    ):
        """Response must show empty cart after clear."""
        response = auth_client.delete(CART_CLEAR_URL, format="json")
        cart_data = response.data["data"]
        assert cart_data["is_empty"] is True
        assert cart_data["total_items"] == 0
        assert cart_data["items"] == []

    def test_clear_empty_cart_returns_200(self, auth_client: APIClient):
        """
        Clearing an already-empty cart must return 200.
        Idempotent — safe to call multiple times.
        """
        response = auth_client.delete(CART_CLEAR_URL, format="json")
        assert response.status_code == 200

    def test_clear_cart_does_not_affect_other_users(
        self,
        auth_client: APIClient,
        another_cart: Cart,
        another_user: User,
        product: Product,
    ):
        """
        Clearing User A's cart must not remove User B's items.
        Cart isolation is a critical data integrity requirement.
        """
        CartItem.objects.create(
            cart=another_cart, product=product, quantity=2
        )
        auth_client.delete(CART_CLEAR_URL, format="json")
        assert CartItem.objects.filter(cart=another_cart).count() == 1

    def test_clear_cart_unauthenticated_returns_401(
        self, api_client: APIClient
    ):
        response = api_client.delete(CART_CLEAR_URL, format="json")
        assert response.status_code == 401
# from __future__ import annotations

# import pytest
# from rest_framework.test import APIClient

# from apps.accounts.models import User
# from apps.products.models import Category, Brand, Product
# from .models import Cart, CartItem


# # ─── Fixtures ──────────────────────────────────────────────────────────────

# @pytest.fixture
# def api_client() -> APIClient:
#     return APIClient()


# @pytest.fixture
# def customer(db) -> User:
#     return User.objects.create_user(
#         email="customer@test.com",
#         full_name="Test Customer",
#         password="StrongPass123",
#         is_verified=True,
#     )


# @pytest.fixture
# def customer_client(api_client, customer) -> APIClient:
#     response = api_client.post("/api/accounts/login/", {
#         "email": customer.email,
#         "password": "StrongPass123",
#     }, format='json')
#     token = response.data["data"]["access"]
#     api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
#     return api_client


# @pytest.fixture
# def category(db) -> Category:
#     return Category.objects.create(name="Engine Parts")


# @pytest.fixture
# def product(db, category) -> Product:
#     return Product.objects.create(
#         name="Piston Ring Set",
#         category=category,
#         sku="ENG-PIS-001",
#         price=1500,
#         stock=10,
#     )


# @pytest.fixture
# def low_stock_product(db, category) -> Product:
#     return Product.objects.create(
#         name="Rare Sensor",
#         category=category,
#         sku="SEN-001",
#         price=2000,
#         stock=2,
#     )


# # ─── Cart Auto-Creation Tests ─────────────────────────────────────────────────

# @pytest.mark.django_db
# class TestCartCreation:

#     def test_cart_created_automatically_on_user_creation(self, customer):
#         assert Cart.objects.filter(user=customer).exists()

#     def test_new_cart_is_empty(self, customer):
#         assert customer.cart.is_empty is True
#         assert customer.cart.total_items == 0


# # ─── Cart Detail Tests ────────────────────────────────────────────────────────

# @pytest.mark.django_db
# class TestCartDetail:

#     def test_get_empty_cart(self, customer_client):
#         response = customer_client.get("/api/cart/")
#         assert response.status_code == 200
#         assert response.data["data"]["is_empty"] is True

#     def test_get_cart_unauthenticated_fails(self, api_client):
#         response = api_client.get("/api/cart/")
#         assert response.status_code == 401


# # ─── Add To Cart Tests ────────────────────────────────────────────────────────

# @pytest.mark.django_db
# class TestAddToCart:

#     def test_add_item_success(self, customer_client, product):
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id,
#             "quantity": 2,
#         }, format='json')
#         assert response.status_code == 201
#         assert response.data["data"]["total_items"] == 2

#     def test_add_item_default_quantity_is_one(self, customer_client, product):
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id,
#         }, format='json')
#         assert response.status_code == 201
#         assert response.data["data"]["total_items"] == 1

#     def test_add_same_product_twice_increases_quantity(self, customer_client, product):
#         customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 2,
#         }, format='json')
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 3,
#         }, format='json')
#         assert response.data["data"]["total_items"] == 5
#         assert CartItem.objects.filter(product=product).count() == 1

#     def test_add_item_exceeding_stock_fails(self, customer_client, low_stock_product):
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": low_stock_product.id,
#             "quantity": 10,
#         }, format='json')
#         assert response.status_code == 400
#         assert "quantity" in response.data["errors"]

#     def test_add_item_then_exceed_stock_on_second_add_fails(
#         self, customer_client, low_stock_product
#     ):
#         customer_client.post("/api/cart/items/", {
#             "product_id": low_stock_product.id, "quantity": 1,
#         }, format='json')
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": low_stock_product.id, "quantity": 5,
#         }, format='json')
#         assert response.status_code == 400

#     def test_add_nonexistent_product_fails(self, customer_client):
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": 9999, "quantity": 1,
#         }, format='json')
#         assert response.status_code == 400

#     def test_add_unavailable_product_fails(self, customer_client, product):
#         product.status = Product.Status.DISCONTINUED
#         product.save()
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 1,
#         }, format='json')
#         assert response.status_code == 400

#     def test_add_zero_quantity_fails(self, customer_client, product):
#         response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 0,
#         }, format='json')
#         assert response.status_code == 400

#     def test_add_item_unauthenticated_fails(self, api_client, product):
#         response = api_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 1,
#         }, format='json')
#         assert response.status_code == 401


# # ─── Update Cart Item Tests ────────────────────────────────────────────────────

# @pytest.mark.django_db
# class TestUpdateCartItem:

#     def test_update_quantity_success(self, customer_client, product):
#         add_response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 1,
#         }, format='json')
#         item_id = add_response.data["data"]["items"][0]["id"]

#         response = customer_client.put(f"/api/cart/items/{item_id}/", {
#             "quantity": 5,
#         }, format='json')
#         assert response.status_code == 200
#         assert response.data["data"]["total_items"] == 5

#     def test_update_quantity_exceeding_stock_fails(
#         self, customer_client, low_stock_product
#     ):
#         add_response = customer_client.post("/api/cart/items/", {
#             "product_id": low_stock_product.id, "quantity": 1,
#         }, format='json')
#         item_id = add_response.data["data"]["items"][0]["id"]

#         response = customer_client.put(f"/api/cart/items/{item_id}/", {
#             "quantity": 99,
#         }, format='json')
#         assert response.status_code == 400

#     def test_update_other_users_item_404(self, customer_client, product, api_client, db):
#         other_user = User.objects.create_user(
#             email="other@test.com", full_name="Other User",
#             password="Pass12345", is_verified=True,
#         )
#         other_cart = other_user.cart
#         other_item = CartItem.objects.create(
#             cart=other_cart, product=product, quantity=1,
#         )

#         response = customer_client.put(f"/api/cart/items/{other_item.id}/", {
#             "quantity": 2,
#         }, format='json')
#         assert response.status_code == 404

#     def test_remove_item_success(self, customer_client, product):
#         add_response = customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 1,
#         }, format='json')
#         item_id = add_response.data["data"]["items"][0]["id"]

#         response = customer_client.delete(f"/api/cart/items/{item_id}/")
#         assert response.status_code == 200
#         assert response.data["data"]["is_empty"] is True

#     def test_remove_nonexistent_item_404(self, customer_client):
#         response = customer_client.delete("/api/cart/items/9999/")
#         assert response.status_code == 404


# # ─── Clear Cart Tests ─────────────────────────────────────────────────────────

# @pytest.mark.django_db
# class TestClearCart:

#     def test_clear_cart_success(self, customer_client, product, low_stock_product):
#         customer_client.post("/api/cart/items/", {
#             "product_id": product.id, "quantity": 1,
#         }, format='json')
#         customer_client.post("/api/cart/items/", {
#             "product_id": low_stock_product.id, "quantity": 1,
#         }, format='json')

#         response = customer_client.delete("/api/cart/clear/")
#         assert response.status_code == 200
#         assert response.data["data"]["is_empty"] is True

#     def test_clear_empty_cart_does_not_error(self, customer_client):
#         response = customer_client.delete("/api/cart/clear/")
#         assert response.status_code == 200


# # ─── Model Tests ────────────────────────────────────────────────────────────

# @pytest.mark.django_db
# class TestCartModel:

#     def test_total_price_calculation(self, customer, product):
#         CartItem.objects.create(cart=customer.cart, product=product, quantity=2)
#         assert customer.cart.total_price == 3000.0

#     def test_total_price_uses_discount_price_when_set(self, customer, category):
#         discounted = Product.objects.create(
#             name="Sale Item", category=category, sku="SALE-001",
#             price=1000, discount_price=700, stock=5,
#         )
#         CartItem.objects.create(cart=customer.cart, product=discounted, quantity=2)
#         assert customer.cart.total_price == 1400.0

#     def test_cart_item_subtotal(self, customer, product):
#         item = CartItem.objects.create(cart=customer.cart, product=product, quantity=3)
#         assert item.subtotal == 4500.0

#     def test_cart_item_quantity_exceeding_stock_raises_on_save(self, customer, low_stock_product):
#         from django.core.exceptions import ValidationError
#         item = CartItem(cart=customer.cart, product=low_stock_product, quantity=10)
#         with pytest.raises(ValidationError):
#             item.save()

#     def test_unique_together_prevents_duplicate_product_rows(self, customer, product):
#         CartItem.objects.create(cart=customer.cart, product=product, quantity=1)
#         with pytest.raises(Exception):
#             CartItem.objects.create(cart=customer.cart, product=product, quantity=1)