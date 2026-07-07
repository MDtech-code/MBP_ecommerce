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
5. [Cross-App Issues](#5-cross-app-issues) *(built after all apps)*

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