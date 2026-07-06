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
4. [Cross-App Issues](#4-cross-app-issues) *(built after all apps)*

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