# SCHEMA_ISSUES.md

> **Version:** 1.0.0
> **Last Updated:** 2025-07-14
> **Purpose:** Tracks schema inconsistencies, design limitations, and
> improvement suggestions found during DATABASE_SCHEMA.md review.
> Each issue includes a safe migration path for already-migrated apps.
>
> **Severity Levels:**
> 🔴 High — Will block feature development
> 🟡 Medium — Should fix before production traffic
> 🟢 Low — Optional improvement

---

## Table of Contents


1. [Accounts App Issues](#1-accounts-app-issues) ✅
2. [Products App Issues](#2-products-app-issues) ✅
3. [Cart App Issues](#3-cart-app-issues) ✅
4. [Orders App Issues](#4-orders-app-issues) ✅
5. [Reviews App Issues](#5-reviews-app-issues) ✅
6. [Contact App Issues](#6-contact-app-issues) ✅
7. [Coupons App Issues](#7-coupons-app-issues) ✅
8. [Payments App Issues](#8-payments-app-issues) ✅
9. [Notifications App Issues](#9-notifications-app-issues) ✅
10. [Cross-App Issues](#10-cross-app-issues) *(built after all apps)*

---

## 1. Accounts App Issues

---

### ISSUE-A01 — No `updated_at` on `User` Model

**Severity:** 🟡 Medium
**Table:** `accounts_user`

**Problem:**
`User` has `date_joined` but no `updated_at`. There is no audit trail
for when email, role, or active status was last changed. `UserProfile`
correctly gets `updated_at` from `TimeStampedModel` but `User` itself
does not.

**Safe Migration Path:**
```python
# Add to User model in accounts/models.py
updated_at = models.DateTimeField(
    _("last updated"),
    auto_now=True,
)
```
```sql
-- What Django generates:
-- ALTER TABLE accounts_user ADD COLUMN updated_at TIMESTAMPTZ;
-- Django backfills current timestamp for all existing rows automatically.
-- No data loss. No downtime required.
```

---

### ISSUE-A02 — Single Address on `UserProfile` Blocks Multi-Address Shipping

**Severity:** 🔴 High
**Table:** `accounts_userprofile`

**Problem:**
`UserProfile` stores only one address. Pakistani ecommerce users
commonly ship to multiple locations (home, office, family). The
`orders` app will have no way to support address selection at
checkout without this being resolved first.

**Proposed New Table — `accounts_useraddress`:**

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BIGINT` | `PK` | — |
| `user_id` | `BIGINT` | `FK → accounts_user`, `NOT NULL`, `INDEX` | `CASCADE` on delete |
| `label` | `VARCHAR(50)` | `NOT NULL` | e.g. `Home`, `Office`, `Other` |
| `address_line1` | `VARCHAR(255)` | `NOT NULL` | — |
| `address_line2` | `VARCHAR(255)` | `NOT NULL` | Default `''` |
| `city` | `VARCHAR(100)` | `NOT NULL` | — |
| `province` | `VARCHAR(2)` | `NOT NULL` | Same Province choices as `UserProfile` |
| `postal_code` | `VARCHAR(10)` | `NOT NULL` | — |
| `country` | `VARCHAR(100)` | `NOT NULL` | Default `'Pakistan'` |
| `is_default` | `BOOLEAN` | `NOT NULL` | Default `FALSE` |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — |

**Safe Migration Path:**
```
Step 1 → Create UserAddress model (new table — zero risk to existing data)
Step 2 → Write data migration to copy UserProfile address fields
         into a new UserAddress row per user with is_default=True
Step 3 → Verify data copied correctly in staging environment
Step 4 → Remove address fields from UserProfile in a separate migration
Step 5 → Orders app FKs to UserAddress or snapshots address at order time
```

---

### ISSUE-A03 — `phone` Field Not Unique and Not Indexed

**Severity:** 🟡 Medium
**Table:** `accounts_userprofile`

**Problem:**
`phone` has no `unique=True` and no `db_index=True`. Two users can
register with the same phone number. If SMS OTP or COD verification
is added later, this causes ambiguous lookups and security issues.

**Safe Migration Path:**
```
Step 1 → Add db_index=True only first (safe — no validation on existing data)
Step 2 → Find duplicates before enforcing uniqueness:
```
```sql
SELECT phone, COUNT(*)
FROM accounts_userprofile
WHERE phone != ''
GROUP BY phone
HAVING COUNT(*) > 1;
```
```
Step 3 → Clean up any duplicate phone numbers via script or manually
Step 4 → Change field definition:
```
```python
# Use null=True to avoid unique constraint collision on empty string values
phone = models.CharField(
    max_length=15,
    null=True,
    blank=True,
    unique=True,
    db_index=True,
)
```

---

### ISSUE-A04 — `EmailVerificationToken` Has No `is_used` Flag

**Severity:** 🟡 Medium
**Table:** `accounts_emailverificationtoken`

**Problem:**
`PasswordResetToken` correctly uses `is_used=True` to prevent replay
attacks. `EmailVerificationToken` has no such flag. After a user
verifies their email the token stays valid in the database until it
expires — up to 24 hours. A captured token could be replayed within
that window.

**Safe Migration Path:**
```python
# Add field to EmailVerificationToken:
is_used = models.BooleanField(
    _("is used"),
    default=False,
    help_text=_("Token becomes invalid after successful verification.")
)

# Add method matching PasswordResetToken pattern:
def mark_used(self) -> None:
    self.is_used = True
    self.save(update_fields=["is_used"])
```
```
Update verification view logic:
  1. Check is_used before accepting token
  2. Call token.mark_used() after User.is_verified = True

Migration risk: None — new column with default=False,
no existing data affected.
```

---

### ISSUE-A05 — Missing Indexes on `role` and `last_login`

**Severity:** 🟢 Low
**Table:** `accounts_user`

**Problem:**
`role` has no `db_index`. Filtering all admins or all customers —
common in admin panels and Celery jobs — requires a full table scan.
`last_login` has no index either. Celery cleanup jobs targeting
inactive users will be slow as user count grows.

**Safe Migration Path:**
```python
# Add via Meta indexes — preferred over field-level db_index:
class Meta:
    indexes = [
        models.Index(fields=["role"], name="accounts_user_role_idx"),
        models.Index(fields=["last_login"], name="accounts_user_last_login_idx"),
    ]
# Migration risk: None — adding indexes never affects existing data.
```

---

### ISSUE-A06 — No Login Activity Tracking

**Severity:** 🟢 Low
**Table:** `accounts_userloginactivity` *(does not exist yet)*

**Problem:**
No record of login history, IP addresses, or failed attempts exists.
For a real-user Pakistani ecommerce platform this matters for fraud
detection on COD orders, new device login security emails, and
failed login rate limiting beyond throttle resets.

**Proposed New Table — `accounts_userloginactivity`:**

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BIGINT` | `PK` | — |
| `user_id` | `BIGINT` | `FK → accounts_user`, `NULL`, `INDEX` | `SET NULL` on delete — preserve logs even if user deleted |
| `ip_address` | `INET` | `NOT NULL` | Django `GenericIPAddressField` |
| `user_agent` | `TEXT` | `NOT NULL` | Browser / device string |
| `was_successful` | `BOOLEAN` | `NOT NULL` | Login success or failure |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Login attempt timestamp |

**Safe Migration Path:**
```
New table — zero risk to existing data.
Add Celery periodic task to purge records older than 90 days
to prevent unbounded table growth.
```

---

---

## 2. Products App Issues

---

### ISSUE-P01 — `Category` CASCADE Delete Will Silently Destroy Subcategory Trees

**Severity:** 🔴 High
**Table:** `products_category`

**Problem:**
`parent` FK is set to `on_delete=CASCADE`. Deleting a parent category
silently deletes all child subcategories and their children recursively.
In a motorbike parts store with deep hierarchies like
`Engine → Pistons → Piston Rings`, deleting `Engine` would cascade
delete every subcategory underneath it with no warning.
The products under those categories are protected by `PROTECT` on the
product side but the categories themselves vanish silently.

**Safe Migration Path:**
```python
# Change to PROTECT to prevent accidental deletion:
parent = models.ForeignKey(
    "self",
    on_delete=models.PROTECT,   # was CASCADE
    null=True,
    blank=True,
    related_name="subcategories",
)
# PROTECT raises ProtectedError if deletion is attempted while children exist.
# Admin must manually reassign or delete children first — intentional friction.
# Migration: Safe — FK constraint change only, no data affected.
```

---

### ISSUE-P02 — `BikeModel.year_start` / `year_end` Have No Range Validation

**Severity:** 🟡 Medium
**Table:** `products_bikemodel`

**Problem:**
`year_start` and `year_end` are plain `PositiveIntegerField` with no
upper or lower bound validators and no DB-level check that
`year_end >= year_start`. A data entry error like
`year_start=2025, year_end=2019` is accepted silently.

**Safe Migration Path:**
```python
from django.core.validators import MinValueValidator, MaxValueValidator
import datetime

CURRENT_YEAR = datetime.date.today().year

year_start = models.PositiveIntegerField(
    validators=[
        MinValueValidator(1960),
        MaxValueValidator(CURRENT_YEAR + 1),
    ]
)
year_end = models.PositiveIntegerField(
    null=True,
    blank=True,
    validators=[
        MinValueValidator(1960),
        MaxValueValidator(CURRENT_YEAR + 1),
    ]
)

# Add clean() method to BikeModel for cross-field validation:
def clean(self):
    from django.core.exceptions import ValidationError
    if self.year_end and self.year_end < self.year_start:
        raise ValidationError(
            {"year_end": "Production end year cannot be before start year."}
        )
```
```
Migration: Safe — validators are Python-level only.
No DB constraint added. No existing data affected.
```

---

### ISSUE-P03 — `Product.slug` Collision Risk on Duplicate Names

**Severity:** 🟡 Medium
**Table:** `products_product`

**Problem:**
`slug` is auto-generated via `slugify(name)` on first save only.
If two products have similar names like `Honda CB150F Oil Filter` and
`Honda CB150F Oil Filter (OEM)`, `slugify` produces `honda-cb150f-oil-filter`
for both. The second save raises an `IntegrityError` on the `UNIQUE`
constraint with no graceful fallback. Same issue exists for
`products_category`, `products_brand`, and `products_bikemodel` slugs.

**Safe Migration Path:**
```python
# Add a slug uniqueness helper — append SKU or short UUID on collision:
def save(self, *args, **kwargs) -> None:
    if not self.slug:
        base_slug = slugify(self.name)
        slug = base_slug
        counter = 1
        while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        self.slug = slug
    super().save(*args, **kwargs)

# Apply same pattern to Category, Brand, BikeModel save() methods.
# Migration: Safe — logic change only, no schema change required.
```

---

### ISSUE-P04 — `Product.stock` Has No Concurrency Protection

**Severity:** 🔴 High
**Table:** `products_product`

**Problem:**
`stock` is a plain `PositiveIntegerField`. When two users add the last
unit to cart simultaneously, both reads see `stock=1`, both pass the
availability check, and both orders proceed — resulting in overselling.
This is a critical issue for a real-user ecommerce platform.

**Safe Migration Path:**
```python
# Use select_for_update() in cart/order flow — NOT a model change:
from django.db import transaction

with transaction.atomic():
    product = Product.objects.select_for_update().get(pk=product_id)
    if product.stock >= quantity:
        product.stock -= quantity
        product.save(update_fields=["stock", "status"])
    else:
        raise InsufficientStockError()

# Additionally use F() expressions for stock decrements to avoid
# read-modify-write race conditions:
Product.objects.filter(pk=product_id).update(stock=F("stock") - quantity)
```
```
Migration: None required — this is an ORM usage pattern fix,
not a schema change. Must be enforced in cart and orders app logic.
```

---

### ISSUE-P05 — No `db_index` on `Product.is_featured`

**Severity:** 🟢 Low
**Table:** `products_product`

**Problem:**
Homepage and featured product sections will query
`Product.objects.filter(is_featured=True, status='available')`.
`is_featured` has no index. As catalog grows this becomes a
full table scan on every homepage load.

**Safe Migration Path:**
```python
# Add to Product Meta indexes:
class Meta:
    indexes = [
        models.Index(fields=["status"]),
        models.Index(fields=["category", "status"]),
        models.Index(fields=["is_featured", "status"]),  # add this
    ]
# Migration: Safe — adding index never affects existing data.
```

---

### ISSUE-P06 — `ProductImage` Primary Enforcement Is Not DB-Level

**Severity:** 🟢 Low
**Table:** `products_productimage`

**Problem:**
The "only one primary image per product" rule is enforced in Python
`save()` only. If images are bulk-created via `bulk_create()`,
`update()`, or direct SQL, the constraint is bypassed and multiple
primary images can exist per product. API responses that assume a
single primary will return inconsistent results.

**Safe Migration Path:**
```python
# Option 1 — Add a partial unique index via migration:
# Only one is_primary=TRUE allowed per product_id
from django.db.models import UniqueConstraint, Q

class Meta:
    constraints = [
        UniqueConstraint(
            fields=["product"],
            condition=Q(is_primary=True),
            name="unique_primary_image_per_product",
        )
    ]
# This is a DB-level partial unique index — enforced even on bulk ops.
# Migration: Safe — new constraint only. Fails only if bad data already exists.
# Run this first to check:
```
```sql
SELECT product_id, COUNT(*)
FROM products_productimage
WHERE is_primary = TRUE
GROUP BY product_id
HAVING COUNT(*) > 1;
```

---

### ISSUE-P07 — No Product Review or Rating Model

**Severity:** 🟢 Low
**Table:** *(does not exist yet)*

**Problem:**
No review or rating system exists. For a real-user Pakistani ecommerce
platform, customer reviews build trust and drive conversion especially
for motorbike parts where compatibility confidence matters.

**Proposed New Table — `products_productreview`:**

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BIGINT` | `PK` | — |
| `product_id` | `BIGINT` | `FK → products_product`, `NOT NULL`, `INDEX` | `CASCADE` on delete |
| `user_id` | `BIGINT` | `FK → accounts_user`, `NOT NULL`, `INDEX` | `SET NULL` on delete |
| `rating` | `SMALLINT` | `NOT NULL` | Values `1–5`. Add `CheckConstraint` |
| `comment` | `TEXT` | `NOT NULL` | Default `''` |
| `is_verified_purchase` | `BOOLEAN` | `NOT NULL` | Default `FALSE`. Set `TRUE` if user ordered this product |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | — |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL` | — |

```
Unique constraint: one review per user per product.
Migration: New table — zero risk to existing data.
```

---

## 3. Cart App Issues

---

### ISSUE-C01 — `CartItem` CASCADE on Product Delete Silently Destroys Cart Data

**Severity:** 🔴 High
**Table:** `cart_cartitem`

**Problem:**
`product` FK is set to `on_delete=CASCADE`. If an admin deletes or
discontinues a product that is currently sitting in active user carts,
all `CartItem` rows referencing that product are silently deleted.
Users lose cart contents with no notification. In Pakistani ecommerce
where users may save carts for days before purchasing, this is a
significant trust and UX problem.

**Safe Migration Path:**
```python
# Change to PROTECT to prevent product deletion while in active carts:
product = models.ForeignKey(
    Product,
    on_delete=models.PROTECT,   # was CASCADE
    related_name="cart_items",
)
# PROTECT raises ProtectedError — admin must remove product from all
# carts before deletion, or use Product.status = DISCONTINUED instead
# of hard deletion which is the correct production pattern.

# Better long-term pattern — never hard delete products:
# Use Product.status = DISCONTINUED and filter those out of cart display.
# Migration: Safe — FK constraint change only, no data affected.
```

---

### ISSUE-C02 — `CartItem.quantity` Stock Validation Is Not Concurrency Safe

**Severity:** 🔴 High
**Table:** `cart_cartitem`

**Problem:**
`clean()` validates `quantity <= product.stock` by reading
`self.product.stock` at validation time. Between that read and the
actual order placement, another user may purchase the remaining stock.
This is the same race condition noted in ISSUE-P04 — the cart layer
does not protect against it either. Two users can both pass
validation with `quantity=1` when `stock=1`.

**Safe Migration Path:**
```python
# At order placement — not cart save — use select_for_update():
from django.db import transaction

with transaction.atomic():
    product = Product.objects.select_for_update().get(pk=product_id)
    if product.stock >= requested_quantity:
        product.stock -= requested_quantity
        product.save(update_fields=["stock"])
    else:
        raise InsufficientStockError(product.name)

# Cart-level clean() is acceptable as a soft UX guard only.
# Hard stock enforcement must happen at order checkout — not cart add.
# No migration required — ORM pattern fix in orders/checkout logic.
```

---

### ISSUE-C03 — No Maximum Quantity Per Cart Item

**Severity:** 🟡 Medium
**Table:** `cart_cartitem`

**Problem:**
`quantity` has no upper bound beyond live stock. A user could add
`quantity=10000` if stock happens to be that high, or a bad actor
could probe stock levels by attempting large quantities and reading
the error message. No per-order quantity cap exists.

**Safe Migration Path:**
```python
from django.core.validators import MaxValueValidator

quantity = models.PositiveIntegerField(
    _("quantity"),
    default=1,
    validators=[MaxValueValidator(100)],   # tune to business rules
)

# Also update clean() to check both the validator cap and stock:
def clean(self) -> None:
    if self.quantity > 100:
        raise ValidationError({"quantity": _("Maximum 100 units per item.")})
    if self.quantity > self.product.stock:
        raise ValidationError({...})

# Migration: Safe — validator is Python-level only, no DB constraint added.
```

---

### ISSUE-C04 — Price Not Snapshotted at Cart Add Time

**Severity:** 🟡 Medium
**Table:** `cart_cartitem`

**Problem:**
`CartItem.subtotal` is computed live from `product.current_price`
on every access. If an admin changes the product price while a user
has it in their cart, the cart total silently changes. Users may
add a product at PKR 1,500 and find it is PKR 2,000 by checkout.
This causes trust issues and potential disputes for Pakistani COD orders.

**Safe Migration Path:**
```python
# Add price snapshot field to CartItem:
price_at_add = models.DecimalField(
    _("price at time of adding"),
    max_digits=10,
    decimal_places=2,
    help_text=_("Snapshotted from product.current_price at cart add time.")
)

# Set it in save() on first creation only:
def save(self, *args, **kwargs) -> None:
    if not self.pk:   # only on create
        self.price_at_add = self.product.current_price
    self.full_clean()
    super().save(*args, **kwargs)

# Update subtotal property to use snapshot:
@property
def subtotal(self) -> Decimal:
    return self.price_at_add * self.quantity
```
```
Migration: Safe — add field with a default for existing rows.
Existing CartItem rows get current product price as their snapshot.
ALTER TABLE cart_cartitem ADD COLUMN price_at_add NUMERIC(10,2);
```

---

### ISSUE-C05 — No Cart Expiry or Abandoned Cart Tracking

**Severity:** 🟢 Low
**Table:** `cart_cart`

**Problem:**
Carts live forever. There is no mechanism to identify abandoned carts,
send recovery emails, or clean up stale cart data. In Pakistani
ecommerce where COD abandonment rates are high, abandoned cart
recovery is a direct revenue opportunity.

**Safe Migration Path:**
```python
# Option 1 — Add expires_at to Cart for TTL-based cleanup:
expires_at = models.DateTimeField(
    _("expires at"),
    null=True,
    blank=True,
    help_text=_("Cart auto-expires after inactivity. Reset on each update.")
)

# Option 2 — Use Celery periodic task to identify abandoned carts:
# Definition: Cart with items, last updated > 24 hours ago, no order placed.
# Task queries: Cart.objects.filter(
#     updated_at__lt=timezone.now() - timedelta(hours=24),
#     items__isnull=False
# ).distinct()
# Then trigger abandoned cart email via Celery beat.

# No migration strictly required for Option 2 — uses existing updated_at.
# Option 1 requires adding expires_at column — safe, nullable field.
```

---

### ISSUE-C06 — Cross-App Alignment: `CartItem` References `Product` Directly

**Severity:** 🟡 Medium
**Table:** `cart_cartitem` ↔ `products_product`

**Problem:**
`CartItem.product` FK points directly to `Product`. When the `orders`
app is built, order line items will also need product references and
price snapshots. Without a shared pattern established now, the orders
app may duplicate cart logic inconsistently — different snapshot
strategies, different validation approaches, different field names.

**Recommendation:**
Define the order line item pattern now before building the orders app.
Cart and order line items should follow the same field naming:
`product_id`, `quantity`, `price_at_add` (or `unit_price`).
This makes cart-to-order conversion logic clean and symmetrical.
Document this decision in `api_standards.md` under line item conventions.

---


## 4. Orders App Issues

---

### ISSUE-O01 — `placed_at` Duplicates `created_at` from `TimeStampedModel`

**Severity:** 🟢 Low
**Table:** `orders_order`

**Problem:**
`Order` extends `TimeStampedModel` which provides `created_at`
with `auto_now_add=True`. The model also defines `placed_at` with
`auto_now_add=True`. Both fields will always hold the exact same
timestamp value — they are redundant. This adds an unnecessary
column to the table and creates confusion about which field to
use in queries and API responses.

**Safe Migration Path:**
```python
# Option 1 — Remove placed_at, use created_at as the order timestamp:
# Rename created_at → placed_at in API serializer output only
# No schema change needed — just serializer field aliasing

# Option 2 — Keep placed_at, stop extending TimeStampedModel:
# If you want placed_at as the explicit business name, drop TimeStampedModel
# and define only placed_at + updated_at manually
# This is acceptable since Order has its own lifecycle timestamps anyway

# Recommended: Option 1 — remove placed_at, alias created_at in serializer.
# Migration: Remove the field — safe since it holds no unique data.
# Run after verifying no existing queries reference placed_at directly.
```

---

### ISSUE-O02 — `order_number` Has No Generation Strategy Defined

**Severity:** 🔴 High
**Table:** `orders_order`

**Problem:**
`order_number` is `unique` and required but has no `default` and no
auto-generation logic in `save()` or the model. Nothing in the model
defines how `MBP-20240001` format is generated. If the checkout view
forgets to pass `order_number`, the database raises an `IntegrityError`
with a confusing message. In concurrent checkouts, two requests could
generate the same number before either saves.

**Safe Migration Path:**
```python
# Add generation in Order.save() using date + zero-padded sequence:
import uuid
from django.utils import timezone

def generate_order_number() -> str:
    date_str = timezone.now().strftime("%Y%m%d")
    unique_suffix = str(uuid.uuid4().int)[:6]
    return f"MBP-{date_str}-{unique_suffix}"

def save(self, *args, **kwargs) -> None:
    if not self.order_number:
        self.order_number = generate_order_number()
    super().save(*args, **kwargs)

# For guaranteed sequential numbers use a DB sequence:
# CREATE SEQUENCE order_number_seq START 1000;
# Then: SELECT nextval('order_number_seq') in a transaction
# This is the safest approach for concurrent checkouts.
# No migration needed for the UUID approach — logic only.
```

---

### ISSUE-O03 — `total_price` Is Not Validated Against `subtotal + shipping_fee`

**Severity:** 🟡 Medium
**Table:** `orders_order`

**Problem:**
`subtotal`, `shipping_fee`, and `total_price` are all stored
separately with no constraint or `clean()` validation that
`total_price == subtotal + shipping_fee`. A bug in checkout logic
could write an inconsistent record where these three values do not
add up. Financial records with internal inconsistencies are
extremely difficult to reconcile for COD accounting.

**Safe Migration Path:**
```python
# Add clean() to Order model:
from django.core.exceptions import ValidationError

def clean(self) -> None:
    expected_total = self.subtotal + self.shipping_fee
    if self.total_price != expected_total:
        raise ValidationError({
            "total_price": _(
                "total_price (%(total)s) must equal "
                "subtotal (%(sub)s) + shipping_fee (%(ship)s)."
            ) % {
                "total": self.total_price,
                "sub": self.subtotal,
                "ship": self.shipping_fee,
            }
        })

# Or derive total_price as a property and remove the stored field:
# @property
# def total_price(self) -> Decimal:
#     return self.subtotal + self.shipping_fee
# Removing stored total_price simplifies schema but loses queryability.
# Recommended: Keep stored field + add clean() validation.
# No migration required — clean() is Python-level only.
```

---

### ISSUE-O04 — `OrderStatusLog.from_status` / `to_status` Are Free Text

**Severity:** 🟡 Medium
**Table:** `orders_orderstatuslog`

**Problem:**
`from_status` and `to_status` are plain `CharField` with no
`choices` constraint. Any string can be written as a status value
in the log including typos like `"shiped"` or `"cancled"`.
This breaks audit trail integrity and makes log queries unreliable.
The model docstring says it is an immutable audit trace — free text
fields undermine that guarantee.

**Safe Migration Path:**
```python
# Add choices matching Order.Status to both fields:
from_status = models.CharField(
    _("previous status"),
    max_length=20,
    choices=Order.Status.choices,   # reuse Order.Status enum
)
to_status = models.CharField(
    _("new status"),
    max_length=20,
    choices=Order.Status.choices,
)

# Also add clean() to validate transition is not a no-op:
def clean(self) -> None:
    if self.from_status == self.to_status:
        raise ValidationError(
            "Status transition must be between two different statuses."
        )

# Migration: Safe — adding choices is metadata only, no DB constraint added.
# No existing data affected.
```

---

### ISSUE-O05 — No `refunded_at` Timestamp for Refund Lifecycle

**Severity:** 🟡 Medium
**Table:** `orders_order`

**Problem:**
`Order.Status` includes `REFUNDED` and `PaymentStatus` includes
`REFUNDED` but there is no `refunded_at` timestamp field to record
when the refund occurred. Every other major status transition has a
dedicated timestamp (`confirmed_at`, `shipped_at`, `delivered_at`,
`cancelled_at`) but refund — which is the most financially sensitive
state — has none. This makes refund reconciliation and reporting
impossible without parsing the `OrderStatusLog`.

**Safe Migration Path:**
```python
# Add alongside other lifecycle timestamps in Order model:
refunded_at = models.DateTimeField(
    _("refunded at"),
    null=True,
    blank=True,
)

# Set it in the order status transition logic:
# if new_status == Order.Status.REFUNDED:
#     order.refunded_at = timezone.now()

# Migration: Safe — nullable field, no existing data affected.
# ALTER TABLE orders_order ADD COLUMN refunded_at TIMESTAMPTZ NULL;
```

---

### ISSUE-O06 — `OrderItem.subtotal` Is Stored But Should Be Validated

**Severity:** 🟡 Medium
**Table:** `orders_orderitem`

**Problem:**
`OrderItem.subtotal` is stored as `unit_price × quantity` but there
is no `clean()` or `save()` logic that enforces this calculation.
A bug in checkout serializer could write `unit_price=500`,
`quantity=2`, `subtotal=800` — mathematically wrong but accepted
silently. Since these are financial snapshots used for accounting
and COD reconciliation, silent corruption here is serious.

**Safe Migration Path:**
```python
# Add clean() to OrderItem:
def clean(self) -> None:
    expected = self.unit_price * self.quantity
    if self.subtotal != expected:
        raise ValidationError({
            "subtotal": _(
                "subtotal (%(sub)s) must equal "
                "unit_price (%(price)s) × quantity (%(qty)s)."
            ) % {
                "sub": self.subtotal,
                "price": self.unit_price,
                "qty": self.quantity,
            }
        })

# Or compute and set in save() instead of accepting from caller:
def save(self, *args, **kwargs) -> None:
    self.subtotal = self.unit_price * self.quantity
    super().save(*args, **kwargs)

# Recommended: compute in save() — removes human error entirely.
# No migration required — logic change only.
```

---

### ISSUE-O07 — No Discount Amount Captured in Order Financial Snapshot

**Severity:** 🟡 Medium
**Table:** `orders_order` / `orders_orderitem`

**Problem:**
`OrderItem.unit_price` snapshots `product.current_price` which already
applies the discount. But there is no record of what the original price
was or how much discount was applied. For business reporting — total
discounts given, discount impact on revenue — this data is permanently
lost once the order is placed. Pakistani ecommerce businesses running
seasonal promotions on Eid or Independence Day need this for analytics.

**Safe Migration Path:**
```python
# Add to OrderItem model:
original_price = models.DecimalField(
    _("original price snapshot"),
    max_digits=10,
    decimal_places=2,
    help_text=_("product.price at order time — before any discount.")
)
discount_amount = models.DecimalField(
    _("discount amount"),
    max_digits=10,
    decimal_places=2,
    default=0,
    help_text=_("original_price - unit_price per unit.")
)

# At order placement:
# item.original_price = product.price          (always the base price)
# item.unit_price     = product.current_price  (after discount)
# item.discount_amount = original_price - unit_price

# Migration: Safe — new nullable fields, no existing data affected.
```

---

### ISSUE-O08 — Cross-App Alignment: Cart-to-Order Conversion Pattern

**Severity:** 🟡 Medium
**Tables:** `cart_cartitem` ↔ `orders_orderitem`

**Problem:**
`CartItem` has no `price_at_add` snapshot (noted in ISSUE-C04).
`OrderItem` has `unit_price` snapshot. When converting a cart to an
order the checkout logic must use `product.current_price` at that
exact moment — but if the price changed between cart-add and checkout,
the user sees a different price than expected with no warning.
The cart-to-order conversion has no defined atomicity boundary.

**Recommendation:**
```
The entire cart-to-order conversion must run inside a single
atomic transaction:

  with transaction.atomic():
    1. Lock all products via select_for_update()
    2. Validate stock for each CartItem
    3. Create Order record
    4. Create OrderItem records — snapshot prices at this exact moment
    5. Decrement product.stock for each item
    6. Clear CartItems
    7. Trigger confirmation email via Celery (outside transaction)

This sequence must be implemented in the orders app checkout service.
Defining it here ensures cart and orders apps are aligned on the
conversion contract before implementation begins.
```

---


### ISSUE-R01 — `Review` CASCADE on User Delete Destroys Review History

**Severity:** 🟡 Medium
**Table:** `reviews_review`

**Problem:**
`user` FK is `on_delete=CASCADE`. If a user account is deleted,
all their reviews are silently deleted with it. Product rating
averages can shift significantly if a user who left many reviews
is removed. Other users who found those reviews helpful lose that
content permanently. For a motorbike parts store where technical
compatibility reviews carry real value, this is a meaningful loss.

**Safe Migration Path:**
```python
# Change to SET_NULL — preserve reviews even after user deletion:
user = models.ForeignKey(
    settings.AUTH_USER_MODEL,
    on_delete=models.SET_NULL,   # was CASCADE
    null=True,
    blank=True,
    related_name="reviews",
)

# Display deleted user reviews as "Verified Customer" or "Anonymous"
# in the frontend — common pattern used by Amazon, Daraz etc.

# Migration: Safe — FK constraint change + add null=True to column.
# ALTER TABLE reviews_review ALTER COLUMN user_id DROP NOT NULL;
# Existing rows unaffected — all have valid user_id values.
```

---

### ISSUE-R02 — `is_approved=True` by Default Bypasses Moderation

**Severity:** 🟡 Medium
**Table:** `reviews_review`

**Problem:**
`is_approved` defaults to `TRUE`. Every submitted review is
immediately publicly visible without any admin moderation step.
In a Pakistani ecommerce context where competitor sabotage reviews,
spam, and fake negative reviews are common, auto-approving all
content exposes the platform to reputation damage from day one
of real user traffic.

**Safe Migration Path:**
```python
# Change default to FALSE — require explicit approval:
is_approved = models.BooleanField(
    _("moderation approval flag"),
    default=False,   # was True
    help_text=_(
        "Review is hidden from public until approved by moderator."
    )
)

# Options for moderation workflow:
# Option A — Manual: Admin reviews queue in Django admin and approves
# Option B — Auto-approve verified purchase reviews only:
#   if order_item_id is not None:
#       review.is_approved = True  # trusted — confirmed buyer
#   else:
#       review.is_approved = False  # holds for manual review

# Migration: Safe — default value change only.
# Existing approved reviews are unaffected.
# New reviews after migration will require approval.
```

---

### ISSUE-R03 — `order_item_id` Does Not Enforce Product Match

**Severity:** 🔴 High
**Table:** `reviews_review`

**Problem:**
`Review` links to both `product_id` and `order_item_id` but there
is no constraint or `clean()` validation that
`order_item.product == review.product`. A malicious or buggy request
could submit a review for `Product A` while citing an `OrderItem`
for `Product B` as the verified purchase proof. This means
fake verified purchase badges can be attached to any product
using any historical order item.

**Safe Migration Path:**
```python
# Add clean() to Review model:
from django.core.exceptions import ValidationError

def clean(self) -> None:
    if self.order_item_id and self.product_id:
        if self.order_item.product_id != self.product_id:
            raise ValidationError({
                "order_item": _(
                    "The linked order item does not belong to "
                    "the product being reviewed."
                )
            })

# Also validate that the order_item belongs to the reviewing user:
def clean(self) -> None:
    if self.order_item_id and self.user_id:
        if self.order_item.order.user_id != self.user_id:
            raise ValidationError({
                "order_item": _(
                    "The linked order item does not belong to "
                    "the reviewing user."
                )
            })

# Both checks should run together in a single clean() method.
# No migration required — Python-level validation only.
```

---

### ISSUE-R04 — Rating Has No DB-Level Constraint

**Severity:** 🟢 Low
**Table:** `reviews_review`

**Problem:**
`rating` uses `MinValueValidator(1)` and `MaxValueValidator(5)`
which are Python-level validators only. They run during form
validation and `full_clean()` but not on direct ORM `.save()`,
`bulk_create()`, or raw SQL. A `rating=0` or `rating=99` can
be written directly to the database bypassing all validation.
Rating aggregates used for product score calculations would
then produce incorrect averages.

**Safe Migration Path:**
```python
# Add DB-level CheckConstraint alongside existing validators:
class Meta:
    constraints = [
        models.CheckConstraint(
            check=models.Q(rating__gte=1) & models.Q(rating__lte=5),
            name="reviews_review_rating_range",
        )
    ]

# This generates:
# ALTER TABLE reviews_review
# ADD CONSTRAINT reviews_review_rating_range
# CHECK (rating >= 1 AND rating <= 5);

# Migration: Safe — new constraint only.
# Fails only if invalid rating data already exists.
# Run this first to verify clean data:
```
```sql
SELECT COUNT(*) FROM reviews_review
WHERE rating < 1 OR rating > 5;
```

---

### ISSUE-R05 — No Cached Average Rating on Product

**Severity:** 🟡 Medium
**Tables:** `reviews_review` ↔ `products_product`

**Problem:**
Product listing pages and search results need to display star ratings.
Every page load would require:
```sql
SELECT AVG(rating), COUNT(*)
FROM reviews_review
WHERE product_id = X AND is_approved = TRUE
```
As reviews grow this aggregate query runs on every product card
render. With 1000 products on a listing page this means 1000
aggregate queries or one large GROUP BY — neither is acceptable
for a production storefront. This was flagged as ISSUE-P07
suggestion — now confirmed necessary given the Review model exists.

**Safe Migration Path:**
```python
# Add two cached fields to Product model:
average_rating = models.DecimalField(
    _("average rating"),
    max_digits=3,
    decimal_places=2,
    default=0,
    help_text=_("Cached average. Updated via signal on review save/delete.")
)
review_count = models.PositiveIntegerField(
    _("review count"),
    default=0,
    help_text=_("Cached count of approved reviews.")
)

# Update via Django signal on Review post_save and post_delete:
from django.db.models import Avg, Count
from django.db.models.signals import post_save, post_delete

def update_product_rating(sender, instance, **kwargs):
    product = instance.product
    result = Review.objects.filter(
        product=product,
        is_approved=True,
    ).aggregate(avg=Avg("rating"), count=Count("id"))
    product.average_rating = result["avg"] or 0
    product.review_count = result["count"] or 0
    product.save(update_fields=["average_rating", "review_count"])

post_save.connect(update_product_rating, sender=Review)
post_delete.connect(update_product_rating, sender=Review)

# Migration: Safe — new fields on Product with defaults.
# No existing data affected.
```

---

### ISSUE-R06 — Cross-App Alignment: `Review` Linked to `OrderItem` Not `Order`

**Severity:** 🟢 Low
**Tables:** `reviews_review` ↔ `orders_orderitem`

**Problem:**
`Review.order_item` links to `OrderItem` directly rather than `Order`.
This is architecturally correct — a user reviews a specific product
from a specific purchase, not the whole order. However it introduces
a subtle query complexity: to check if a user has purchased a product
the query must traverse `OrderItem → Order → user` rather than a
simpler `Order → user` check. This is fine at small scale but worth
documenting as the join pattern to use consistently across the codebase.

**Recommendation:**
```python
# Canonical verified purchase check — use this pattern everywhere:
has_purchased = OrderItem.objects.filter(
    product=product,
    order__user=request.user,
    order__status=Order.Status.DELIVERED,  # only count completed orders
).exists()

# Note: filter on status=DELIVERED not just any order status.
# A CANCELLED or PENDING order should not count as a verified purchase.
# Document this in api_standards.md under review submission rules.
```


## 6. Contact App Issues

---

### ISSUE-CT01 — No Validation That `resolved_by` Is a Staff or Admin User

**Severity:** 🟡 Medium
**Table:** `contact_contactmessage`

**Problem:**
`resolved_by` is a plain FK to `User` with no constraint that the
resolver actually has staff or admin role. A regular customer account
could be set as the resolver through a buggy API call or direct ORM
write. This corrupts the audit trail — resolution records should only
ever reference admin or staff accounts.

**Safe Migration Path:**
```python
# Add clean() validation to ContactMessage:
from django.core.exceptions import ValidationError

def clean(self) -> None:
    if self.resolved_by_id:
        if not self.resolved_by.is_staff and not self.resolved_by.is_admin:
            raise ValidationError({
                "resolved_by": _(
                    "Only staff or admin users can be assigned "
                    "as ticket resolvers."
                )
            })

# Also enforce in the admin view and API serializer — belt and braces.
# No migration required — Python-level validation only.
```

---

### ISSUE-CT02 — Resolution Fields Can Be Set Inconsistently

**Severity:** 🟡 Medium
**Table:** `contact_contactmessage`

**Problem:**
`is_resolved`, `resolved_by`, and `resolved_at` are three separate
fields with no constraint tying them together. All of the following
broken states are currently possible and silently accepted:

- `is_resolved=TRUE` but `resolved_by=NULL` and `resolved_at=NULL`
- `is_resolved=FALSE` but `resolved_by` set to an admin
- `resolved_at` set but `is_resolved=FALSE`

For a support ticket system these inconsistent states make admin
reporting and SLA tracking unreliable.

**Safe Migration Path:**
```python
# Add clean() to enforce resolution field consistency:
def clean(self) -> None:
    if self.is_resolved:
        if not self.resolved_by_id:
            raise ValidationError({
                "resolved_by": _(
                    "A resolver must be assigned when marking "
                    "a ticket as resolved."
                )
            })
        if not self.resolved_at:
            raise ValidationError({
                "resolved_at": _(
                    "A resolution timestamp must be set when "
                    "marking a ticket as resolved."
                )
            })
    else:
        # If not resolved, resolution fields must be empty
        if self.resolved_by_id or self.resolved_at:
            raise ValidationError(
                "Resolution fields must be cleared for unresolved tickets."
            )

# Add a resolve() helper method to ContactMessage:
def resolve(self, admin_user) -> None:
    from django.utils import timezone
    self.is_resolved = True
    self.resolved_by = admin_user
    self.resolved_at = timezone.now()
    self.full_clean()
    self.save(update_fields=["is_resolved", "resolved_by", "resolved_at"])

# No migration required — Python-level validation only.
```

---

### ISSUE-CT03 — No Rate Limiting or Spam Protection at Schema Level

**Severity:** 🟡 Medium
**Table:** `contact_contactmessage`

**Problem:**
Anonymous visitors can submit unlimited contact messages with no
throttle at the schema or model level. The contact form is a common
spam and abuse vector. A single IP could flood the inbox with
thousands of messages. No field tracks submission IP address so
even basic abuse analysis is impossible after the fact.

**Safe Migration Path:**
```python
# Add IP capture field to ContactMessage:
ip_address = models.GenericIPAddressField(
    _("submission IP address"),
    null=True,
    blank=True,
    help_text=_("Captured at submission time for abuse tracking.")
)

# Populate in the contact form view:
# message.ip_address = request.META.get("REMOTE_ADDR")

# Add API throttle in core/throttles.py for the contact endpoint:
# class ContactFormThrottle(AnonRateThrottle):
#     rate = "5/hour"  # tune to business needs

# Add DB-level index for abuse queries:
class Meta:
    indexes = [
        models.Index(fields=["is_resolved"]),
        models.Index(fields=["ip_address"]),   # fast abuse lookups
    ]

# Migration: Safe — new nullable field, no existing data affected.
```

---

### ISSUE-CT04 — No Admin Reply Tracking

**Severity:** 🟢 Low
**Table:** `contact_contactmessage`

**Problem:**
The model tracks whether a ticket is resolved and by whom but has
no record of what the admin actually replied. There is no way to
review what response was sent to a customer or audit response
quality. For a growing Pakistani ecommerce platform where customer
trust is built through support quality, this is a meaningful gap.

**Proposed New Table — `contact_contactreply`:**

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `BIGINT` | `PK` | — |
| `message_id` | `BIGINT` | `FK → contact_contactmessage`, `NOT NULL`, `INDEX` | `CASCADE` on delete |
| `replied_by_id` | `BIGINT` | `FK → accounts_user`, `NULL`, `INDEX` | `SET NULL` on delete — preserve reply history |
| `body` | `TEXT` | `NOT NULL` | Admin reply content |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL` | Reply timestamp |

```
Migration: New table — zero risk to existing data.
One message can have multiple reply threads.
Final reply should trigger is_resolved=TRUE via signal or view logic.
```

---

### ISSUE-CT05 — Cross-App Alignment: Authenticated User `name` and `email` Not Auto-Filled

**Severity:** 🟢 Low
**Table:** `contact_contactmessage`

**Problem:**
When `user_id` is set (authenticated submission), `name` and `email`
are still separate required fields. The form must be pre-filled from
`user.full_name` and `user.email` at the view layer — but nothing in
the model enforces or validates that they match. An authenticated user
could submit with a completely different name and email, creating
a confusing support record where `user_id` points to one person
but `name`/`email` describes another.

**Recommendation:**
```python
# Add clean() cross-field check for authenticated submissions:
def clean(self) -> None:
    if self.user_id and self.email:
        if self.email != self.user.email:
            raise ValidationError({
                "email": _(
                    "Reply email must match the authenticated "
                    "user account email."
                )
            })

# Or simplify the model — for authenticated users do not store
# name and email at all, derive them from user FK at read time:
# @property
# def sender_name(self):
#     return self.user.full_name if self.user_id else self.name
# @property
# def sender_email(self):
#     return self.user.email if self.user_id else self.email

# No migration required for clean() approach.
# Field removal would require a migration — evaluate carefully.
```

---


## 7. Coupons App Issues

---

### ISSUE-CPN01 — Coupon `code` Has No Case Normalisation

**Severity:** 🔴 High
**Table:** `coupons_coupon`

**Problem:**
`code` is stored and looked up as-is with no case normalisation.
A user typing `eidmubarak2026` will not match `EIDMUBARAK2026`
even though they are the same coupon. Since `unique=True` is
case-sensitive in PostgreSQL by default, an admin could also
accidentally create both `EID2026` and `eid2026` as separate
coupons — a silent duplicate that splits usage counts.

**Safe Migration Path:**
```python
# Override save() to always uppercase the code before storing:
def save(self, *args, **kwargs) -> None:
    self.code = self.code.strip().upper()
    super().save(*args, **kwargs)

# Normalise at lookup time in the redemption view:
coupon = Coupon.objects.get(code=submitted_code.strip().upper())

# For DB-level case-insensitive uniqueness use a functional index:
# CREATE UNIQUE INDEX coupons_coupon_code_ci_idx
# ON coupons_coupon (UPPER(code));
# Then remove the standard unique=True and manage via this index.

# Simplest path: add save() normalisation — no migration required.
# Existing codes already uppercase — no data affected.
```

---

### ISSUE-CPN02 — `total_used` Counter Is Not Concurrency Safe

**Severity:** 🔴 High
**Table:** `coupons_coupon`

**Problem:**
`total_used` is incremented by application code after each
redemption. Under concurrent checkouts two requests can both
read `total_used=99` against a `usage_limit_total=100`, both
pass the limit check, and both increment — resulting in
`total_used=101` and one over-redemption. For promotional
coupons on high-traffic events like Eid sales this will
be exploited.

**Safe Migration Path:**
```python
# Use F() expression for atomic increment — never read-modify-write:
from django.db.models import F

# At redemption — inside atomic transaction:
with transaction.atomic():
    coupon = Coupon.objects.select_for_update().get(pk=coupon_id)

    # Re-check limit after acquiring lock:
    if (coupon.usage_limit_total is not None and
            coupon.total_used >= coupon.usage_limit_total):
        raise CouponLimitExceeded()

    # Atomic increment:
    Coupon.objects.filter(pk=coupon_id).update(
        total_used=F("total_used") + 1
    )
    CouponUsage.objects.create(...)

# No migration required — ORM pattern fix in redemption logic.
```

---

### ISSUE-CPN03 — `CouponUsage.order_id` Is a String Not a Real FK

**Severity:** 🔴 High
**Table:** `coupons_couponusage`

**Problem:**
`order_id` is defined as `CharField(100)` described as a
"reference to the Order model". This is a soft reference —
there is no actual FK constraint to `orders_order`. The database
has no way to verify the referenced order exists, enforce
referential integrity, or cascade correctly. A typo, a deleted
order, or a UUID format mismatch leaves orphaned `CouponUsage`
rows pointing to non-existent orders with no error raised.

**Safe Migration Path:**
```python
# Replace CharField with a real ForeignKey to orders_order:
from apps.orders.models import Order

order = models.ForeignKey(
    Order,
    on_delete=models.PROTECT,   # preserve usage record if order deleted
    related_name="coupon_usages",
    verbose_name=_("order"),
)

# This also resolves the unique_together on (coupon, user, order_id)
# which should become (coupon, user, order) with the FK.

# Migration: Safe — new table not yet migrated.
# Add the FK before first migrate run.
# Also add coupon_discount fields to Order model (see ISSUE-CPN05).
```

---

### ISSUE-CPN04 — `CouponUsage` Guest Tracking by Phone Is Bypassable

**Severity:** 🟡 Medium
**Table:** `coupons_couponusage`

**Problem:**
Guest coupon usage is tracked by `phone_number` only. A guest
can bypass the per-user limit by submitting a slightly different
phone format — `03001234567` vs `+923001234567` — which are the
same number but stored as different strings. The same phone
validator from `accounts_userprofile` is not applied here,
so format consistency is not enforced.

**Safe Migration Path:**
```python
# Apply the same phone validator used in accounts app:
from django.core.validators import RegexValidator

phone_validator = RegexValidator(
    regex=r"^\+?92\d{10}$|^0\d{10}$",
    message=_("Enter a valid Pakistani phone number.")
)

phone_number = models.CharField(
    max_length=15,
    db_index=True,
    validators=[phone_validator],
)

# Normalise format in save() — always store in +92 format:
def save(self, *args, **kwargs) -> None:
    if self.phone_number.startswith("0"):
        self.phone_number = "+92" + self.phone_number[1:]
    super().save(*args, **kwargs)

# No migration required — not yet migrated.
# Add normalisation before first migrate run.
```

---

### ISSUE-CPN05 — `Order` Model Has No Coupon Relationship

**Severity:** 🔴 High
**Tables:** `orders_order` ↔ `coupons_coupon`

**Problem:**
`Order` stores `subtotal`, `shipping_fee`, and `total_price` but
has no reference to which coupon was applied or what discount
was given. `CouponUsage` tracks the usage but an order record
itself cannot answer "was a coupon used on this order and what
was the discount?". Admin order views, customer order history,
and financial reporting all need this on the order directly.

**Safe Migration Path:**
```python
# Add to Order model in orders/models.py:
coupon = models.ForeignKey(
    "coupons.Coupon",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="orders",
    verbose_name=_("applied coupon"),
)
discount_amount = models.DecimalField(
    _("coupon discount amount"),
    max_digits=10,
    decimal_places=2,
    default=Decimal("0.00"),
    help_text=_("PKR discount applied via coupon at checkout.")
)

# Update total_price formula in Order.clean():
# total_price = subtotal - discount_amount + shipping_fee

# Migration: Safe — orders app not yet migrated.
# Add fields before first migrate run.
```

---

### ISSUE-CPN06 — `PERCENTAGE` Coupon Has No Upper Bound on `discount_value`

**Severity:** 🟡 Medium
**Table:** `coupons_coupon`

**Problem:**
`discount_value` has `MinValueValidator(0)` but no
`MaxValueValidator`. For `PERCENTAGE` type coupons a value of
`150` is accepted — a 150% discount that would produce a
negative order total. There is no `clean()` that validates
`discount_value <= 100` when `discount_type == PERCENTAGE`.

**Safe Migration Path:**
```python
# Add clean() to Coupon model:
def clean(self) -> None:
    if self.discount_type == self.DiscountType.PERCENTAGE:
        if self.discount_value > Decimal("100.00"):
            raise ValidationError({
                "discount_value": _(
                    "Percentage discount cannot exceed 100%%."
                )
            })
    if self.valid_until <= self.valid_from:
        raise ValidationError({
            "valid_until": _(
                "Expiry date must be after the activation date."
            )
        })

# Second check also catches valid_from >= valid_until which is
# another silent data error currently not validated anywhere.
# No migration required — Python-level validation only.
```

---

### ISSUE-CPN07 — `FREE_SHIPPING` Type Makes `discount_value` Meaningless

**Severity:** 🟢 Low
**Table:** `coupons_coupon`

**Problem:**
When `discount_type = FREE_SHIPPING`, `discount_value` has no
meaning — shipping is zeroed regardless of what value is stored.
Yet `discount_value` is `NOT NULL` with `MinValueValidator(0)`
so an admin must enter a value (typically `0`) even though it
is ignored. This is confusing in the Django admin and could
lead to accidental misreads of coupon data.

**Safe Migration Path:**
```python
# Add clean() rule to enforce discount_value=0 for FREE_SHIPPING:
def clean(self) -> None:
    if self.discount_type == self.DiscountType.FREE_SHIPPING:
        if self.discount_value != Decimal("0.00"):
            raise ValidationError({
                "discount_value": _(
                    "Discount value must be 0 for Free Shipping coupons."
                )
            })

# Or auto-correct in save():
def save(self, *args, **kwargs) -> None:
    self.code = self.code.strip().upper()
    if self.discount_type == self.DiscountType.FREE_SHIPPING:
        self.discount_value = Decimal("0.00")
    super().save(*args, **kwargs)

# No migration required — Python-level logic only.
```

---




## 8. Payments App Issues

---

### ISSUE-PAY01 — `PaymentTransaction.order_id` Is a String Not a Real FK

**Severity:** 🔴 High
**Table:** `payments_paymenttransaction`

**Problem:**
`order_id` is `CharField(100)` described as a reference to
`orders_order`. This is the exact same soft-reference anti-pattern
as `CouponUsage.order_id` flagged in ISSUE-CPN03. There is no
FK constraint, no referential integrity, and no cascade behaviour.
A payment transaction can reference a non-existent order ID with
no error. For financial records this is a critical audit gap —
payments must be provably tied to real orders.
This pattern now appears in both `coupons` and `payments` apps —
confirming it is a systemic design decision that needs correction
before first migration.

**Safe Migration Path:**
```python
# Replace CharField with a real ForeignKey to orders_order:
from apps.orders.models import Order

order = models.ForeignKey(
    Order,
    on_delete=models.PROTECT,
    related_name="payment_transactions",
    verbose_name=_("order"),
)

# PROTECT ensures payment records are never orphaned by order deletion.
# One order can have multiple PaymentTransaction rows:
#   - Initial attempt (PENDING)
#   - Retry after failure (PENDING → FAILED → new PENDING)
#   - Refund transaction (REFUNDED)

# Migration: Safe — not yet migrated.
# Add FK before first migrate run.
# Also update indexes — order_id BTREE becomes a proper FK index.
```

---

### ISSUE-PAY02 — No `PaymentTransaction` to `PaymentTransaction` Refund Link

**Severity:** 🟡 Medium
**Table:** `payments_paymenttransaction`

**Problem:**
`Status` includes `REFUNDED` and `PARTIALLY_REFUNDED` but there is
no field linking a refund transaction back to the original `SUCCESS`
transaction it is refunding. This means you cannot answer:
- "Which original payment does this refund correspond to?"
- "How much of this payment has already been partially refunded?"
- "Is this a duplicate refund attempt?"
Without this link, refund reconciliation requires scanning all
transactions for the same `order_id` and inferring the relationship
from amounts and timestamps — fragile and error-prone.

**Safe Migration Path:**
```python
# Add self-referencing FK for refund linkage:
original_transaction = models.ForeignKey(
    "self",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="refund_transactions",
    verbose_name=_("original transaction"),
    help_text=_("Set on refund transactions — points to the SUCCESS transaction being refunded.")
)

# Refund flow:
# original = PaymentTransaction.objects.get(order=order, status=SUCCESS)
# refund = PaymentTransaction.objects.create(
#     order=order,
#     original_transaction=original,
#     status=REFUNDED,
#     amount_pkr=refund_amount,
#     gateway=original.gateway,
# )

# Migration: Safe — not yet migrated. Add before first migrate run.
```

---

### ISSUE-PAY03 — `WebhookLog.gateway` Is Free Text With No Choices Constraint

**Severity:** 🟡 Medium
**Table:** `payments_webhooklog`

**Problem:**
`WebhookLog.gateway` is a plain `CharField(50)` with no `choices`
constraint while `PaymentTransaction.gateway` uses a controlled
`Gateway.TextChoices` enum. The same gateway can appear as
`"JAZZCASH"`, `"jazzcash"`, `"JazzCash"`, or `"jazz_cash"` in
webhook logs — making JOIN queries between `WebhookLog` and
`PaymentTransaction` by gateway unreliable and breaking any
dashboard that aggregates webhook success rates by gateway.

**Safe Migration Path:**
```python
# Reuse PaymentTransaction.Gateway choices on WebhookLog:
gateway = models.CharField(
    max_length=20,           # match PaymentTransaction field length
    choices=PaymentTransaction.Gateway.choices,
    db_index=True,
)

# For courier webhooks (PostEx, TCS, Leopards) that do not map
# to payment gateways, extend Gateway choices to include them:
class Gateway(models.TextChoices):
    COD = 'COD', _('Cash on Delivery')
    SAFEPAY = 'SAFEPAY', _('Safepay')
    PAYFAST = 'PAYFAST', _('PayFast')
    JAZZCASH = 'JAZZCASH', _('JazzCash')
    EASYPAISA = 'EASYPAISA', _('Easypaisa')
    RAAST = 'RAAST', _('Raast')
    XPAY = 'XPAY', _('XPay by PostEx')
    POSTEX = 'POSTEX', _('PostEx Courier')     # extend here
    LEOPARDS = 'LEOPARDS', _('Leopards Courier')

# Move Gateway enum to apps/common/choices/gateway.py
# so both models import from one source of truth.
# Migration: Safe — not yet migrated. Apply before first migrate run.
```

---

### ISSUE-PAY04 — `WebhookLog` Has `updated_at` But Is Meant to Be Immutable

**Severity:** 🟢 Low
**Table:** `payments_webhooklog`

**Problem:**
`WebhookLog` extends `TimeStampedModel` which adds `updated_at`
with `auto_now=True`. The model docstring explicitly states it is
an immutable audit log. Having `updated_at` auto-updating on every
save contradicts immutability — any accidental `.save()` call
silently updates the timestamp, creating a false impression that
the record was intentionally modified. The same issue exists in
`orders_orderstatuslog` which correctly does not extend
`TimeStampedModel` for this reason.

**Safe Migration Path:**
```python
# Option 1 — Stop extending TimeStampedModel, define only created_at:
class WebhookLog(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    # No updated_at — immutable by design

# Option 2 — Keep TimeStampedModel but override save() to block updates:
def save(self, *args, **kwargs) -> None:
    if self.pk:
        raise ValueError(
            "WebhookLog records are immutable and cannot be updated."
        )
    super().save(*args, **kwargs)

# Recommended: Option 1 — consistent with OrderStatusLog pattern.
# Migration: Safe — not yet migrated. Apply before first migrate run.
```

---

### ISSUE-PAY05 — No `PaymentTransaction` Timestamp for Status Transitions

**Severity:** 🟡 Medium
**Table:** `payments_paymenttransaction`

**Problem:**
`PaymentTransaction` tracks `created_at` (initiation) and
`updated_at` (last change) but has no dedicated timestamp for
when the transaction reached its terminal state (`SUCCESS`,
`FAILED`, `REFUNDED`). For payment reconciliation and SLA
reporting you need to know exactly when a payment was confirmed —
not just when the record was last touched. `updated_at` changes
on any field save and is not a reliable proxy for confirmation time.

**Safe Migration Path:**
```python
# Add terminal state timestamp:
completed_at = models.DateTimeField(
    _("completed at"),
    null=True,
    blank=True,
    help_text=_(
        "Timestamp when transaction reached a terminal state "
        "(SUCCESS, FAILED, REFUNDED, PARTIALLY_REFUNDED)."
    )
)

# Set in status transition logic:
TERMINAL_STATUSES = {
    PaymentTransaction.Status.SUCCESS,
    PaymentTransaction.Status.FAILED,
    PaymentTransaction.Status.REFUNDED,
    PaymentTransaction.Status.PARTIALLY_REFUNDED,
}

if new_status in TERMINAL_STATUSES and not transaction.completed_at:
    transaction.completed_at = timezone.now()

# Migration: Safe — not yet migrated. Add before first migrate run.
```

---

### ISSUE-PAY06 — Cross-App: `Order.payment_status` and `PaymentTransaction.status` Can Diverge

**Severity:** 🔴 High
**Tables:** `orders_order` ↔ `payments_paymenttransaction`

**Problem:**
`Order` has its own `payment_status` field (`pending`, `paid`,
`failed`, `refunded`). `PaymentTransaction` has its own `status`
field (`PENDING`, `SUCCESS`, `FAILED`, `REFUNDED`,
`PARTIALLY_REFUNDED`). These two fields can silently diverge:
- A `PaymentTransaction` marked `SUCCESS` while `Order.payment_status`
  stays `pending` due to a webhook processing failure
- A `PaymentTransaction` marked `REFUNDED` while `Order.payment_status`
  stays `paid`
There is no DB constraint or application-level invariant enforcing
their consistency. Financial dashboards reading `Order.payment_status`
will show stale data while the truth lives in `PaymentTransaction`.

**Safe Migration Path:**
```python
# Define a single source of truth: PaymentTransaction.status
# Derive Order.payment_status from it — never store independently.

# Option 1 — Remove Order.payment_status, compute it as a property:
# @property
# def payment_status(self):
#     latest = self.payment_transactions.order_by("-created_at").first()
#     return latest.status if latest else PaymentTransaction.Status.PENDING

# Option 2 — Keep Order.payment_status but always update it
# inside the same atomic transaction that updates PaymentTransaction:
with transaction.atomic():
    txn.status = PaymentTransaction.Status.SUCCESS
    txn.save(update_fields=["status"])
    txn.order.payment_status = Order.PaymentStatus.PAID
    txn.order.save(update_fields=["payment_status"])

# Also align status value naming — Order uses lowercase ('paid')
# while PaymentTransaction uses uppercase ('SUCCESS').
# Standardise to one convention across both models.
# Recommended: Option 2 for queryability + strict atomic update rule.
# Document this invariant in api_standards.md.
```

---

## 9. Notifications App Issues

---

### ISSUE-NOTIF01 — No Channel-Recipient Consistency Validation

**Severity:** 🔴 High
**Table:** `notifications_notification`

**Problem:**
`recipient_phone`, `recipient_email`, and `user_id` are all
nullable with no `clean()` or DB constraint enforcing that the
correct recipient field is populated for the selected channel.
Current silent failure states:
- `channel=WHATSAPP` with `recipient_phone=NULL` — message sent to nobody
- `channel=EMAIL` with `recipient_email=NULL` — email dispatch crashes at runtime
- `channel=IN_APP` with `user_id=NULL` — notification invisible to all users
- `channel=SMS` with only `recipient_email` set — wrong field populated

At scale these produce silent no-delivery failures with no
validation error — just `is_sent=FALSE` and a cryptic `failure_reason`.

**Safe Migration Path:**
```python
# Add clean() to Notification model:
from django.core.exceptions import ValidationError

def clean(self) -> None:
    if self.channel in (self.Channel.WHATSAPP, self.Channel.SMS):
        if not self.recipient_phone:
            raise ValidationError({
                "recipient_phone": _(
                    "Phone number is required for "
                    "WhatsApp and SMS notifications."
                )
            })
    if self.channel == self.Channel.EMAIL:
        if not self.recipient_email:
            raise ValidationError({
                "recipient_email": _(
                    "Email address is required for "
                    "Email notifications."
                )
            })
    if self.channel == self.Channel.IN_APP:
        if not self.user_id:
            raise ValidationError({
                "user": _(
                    "A user must be linked for "
                    "In-App notifications."
                )
            })

# No migration required — Python-level validation only.
```

---

### ISSUE-NOTIF02 — `is_sent` and `sent_at` Can Be Inconsistent

**Severity:** 🟡 Medium
**Table:** `notifications_notification`

**Problem:**
`is_sent` and `sent_at` are two separate fields with no constraint
tying them together. The following broken states are silently accepted:
- `is_sent=TRUE` with `sent_at=NULL` — sent but no timestamp
- `is_sent=FALSE` with `sent_at` populated — timestamp set but flagged unsent

This is the same three-field inconsistency pattern seen in
`contact_contactmessage` resolution fields (ISSUE-CT02) and
`orders_order` lifecycle timestamps (ISSUE-O05).
For notification delivery SLA reporting `sent_at` must be
trustworthy — it cannot be set independently of `is_sent`.

**Safe Migration Path:**
```python
# Add consistency check to clean():
def clean(self) -> None:
    # ... channel checks above ...
    if self.is_sent and not self.sent_at:
        raise ValidationError({
            "sent_at": _(
                "sent_at must be set when is_sent is True."
            )
        })
    if not self.is_sent and self.sent_at:
        raise ValidationError({
            "sent_at": _(
                "sent_at must be empty when is_sent is False."
            )
        })

# Add a mark_sent() helper method:
def mark_sent(self) -> None:
    from django.utils import timezone
    self.is_sent = True
    self.sent_at = timezone.now()
    self.save(update_fields=["is_sent", "sent_at"])

# No migration required — Python-level validation only.
```

---

### ISSUE-NOTIF03 — `WhatsAppCODVerification.order_id` Is a String Not a Real FK

**Severity:** 🔴 High
**Table:** `notifications_whatsappcodverification`

**Problem:**
`order_id` is `CharField(100)` — the fourth occurrence of this
soft-reference anti-pattern across the codebase. Previously
identified in `coupons_couponusage` (ISSUE-CPN03) and
`payments_paymenttransaction` (ISSUE-PAY01) and
`notifications_whatsappcodverification`. Every app that references
`orders_order` is using a string instead of a FK.
This is now confirmed as a systemic pattern requiring correction
across all three apps before their first migration run.

**Safe Migration Path:**
```python
# Replace CharField with a real ForeignKey:
from apps.orders.models import Order

order = models.OneToOneField(   # unique=True already set — OneToOne is cleaner
    Order,
    on_delete=models.PROTECT,
    related_name="whatsapp_cod_verification",
    verbose_name=_("order"),
)

# OneToOneField is correct here — unique=True was already on order_id
# meaning one verification record per order.
# PROTECT ensures verification history is not lost if order is somehow deleted.
# Migration: Safe — not yet migrated. Add before first migrate run.
```

---

### ISSUE-NOTIF04 — `is_read` Flag Applies Only to `IN_APP` But Exists on All Rows

**Severity:** 🟢 Low
**Table:** `notifications_notification`

**Problem:**
`is_read` is meaningful only for `channel=IN_APP` notifications.
For `WHATSAPP`, `SMS`, and `EMAIL` rows `is_read` defaults `FALSE`
and never changes — it is stored but meaningless on millions of
outbound notification rows. This adds noise to the table and
makes unread count queries (`is_read=FALSE`) return incorrect
results if not filtered by `channel=IN_APP`.

**Safe Migration Path:**
```python
# Option 1 — Always filter by channel in unread count queries:
unread_count = Notification.objects.filter(
    user=request.user,
    channel=Notification.Channel.IN_APP,
    is_read=False,
).count()

# Option 2 — Split IN_APP notifications into a separate model:
# class InAppNotification(TimeStampedModel):
#     user = FK → User
#     title, body, context_data
#     is_read, read_at
# Keeps the main Notification table clean for outbound dispatch logs.

# Option 3 — Add partial index for performance:
class Meta:
    indexes = [
        models.Index(
            fields=["user", "is_read"],
            condition=models.Q(channel="IN_APP"),
            name="notif_inapp_unread_idx",
        )
    ]
# Recommended short-term: Option 1 — query discipline.
# Long-term: Option 2 — separate model as volume grows.
# No migration required for Option 1 or 3.
```

---

### ISSUE-NOTIF05 — `WhatsAppCODVerification` Has No Link to `Notification` Record

**Severity:** 🟢 Low
**Tables:** `notifications_whatsappcodverification` ↔ `notifications_notification`

**Problem:**
`WhatsAppCODVerification` tracks the COD confirmation flow but has
no FK to the `Notification` record that was created when the
WhatsApp message was sent. To audit "which WhatsApp message triggered
this verification flow" you must query across both tables by
`order_id` and `created_at` proximity — fragile and slow.
The two models describe the same event from different angles with
no formal link between them.

**Safe Migration Path:**
```python
# Add optional FK to the originating Notification:
notification = models.OneToOneField(
    "notifications.Notification",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
    related_name="cod_verification",
    verbose_name=_("originating notification"),
)

# Set at creation time in the COD verification Celery task:
# notif = Notification.objects.create(
#     channel=Notification.Channel.WHATSAPP,
#     notification_type=Notification.Type.COD_VERIFICATION,
#     ...
# )
# WhatsAppCODVerification.objects.create(
#     order=order,
#     notification=notif,
#     ...
# )

# Migration: Safe — not yet migrated. Add before first migrate run.
```

---

### ISSUE-NOTIF06 — No Celery Retry Count Tracking on Failed Notifications

**Severity:** 🟢 Low
**Table:** `notifications_notification`

**Problem:**
`is_sent=FALSE` and `failure_reason` record that a notification
failed but there is no `retry_count` field. Celery retry tasks
have no way to know how many times a notification has already
been attempted — they may retry indefinitely or the retry limit
may be lost after a worker restart. For WhatsApp and SMS
notifications that fail due to transient gateway errors, a
capped retry with backoff is standard production practice.

**Safe Migration Path:**
```python
# Add retry tracking fields to Notification:
retry_count = models.PositiveSmallIntegerField(
    _("retry count"),
    default=0,
    help_text=_("Number of dispatch attempts made.")
)
max_retries = models.PositiveSmallIntegerField(
    _("max retries"),
    default=3,
    help_text=_("Maximum dispatch attempts before marking permanently failed.")
)

# Celery task pattern:
# if notification.retry_count >= notification.max_retries:
#     notification.failure_reason = "Max retries exceeded"
#     notification.save(update_fields=["failure_reason"])
#     return  # stop retrying
# notification.retry_count += 1
# notification.save(update_fields=["retry_count"])
# raise self.retry(countdown=2 ** notification.retry_count)

# Migration: Safe — not yet migrated. Add before first migrate run.
```

---