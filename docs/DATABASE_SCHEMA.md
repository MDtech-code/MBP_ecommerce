# DATABASE_SCHEMA.md

> **Version:** 1.0.0
> **Last Updated:** 2025-07-14
> **Database:** PostgreSQL 18 (Local) / PostgreSQL 16 (Docker)
> **Convention:** All table names follow Django default `appname_modelname`
> pattern. Snake_case for all columns. UUID tokens use `uuid4`.

---

## Table of Contents

1. [Accounts App](#1-accounts-app) ✅
2. [Products App](#2-products-app) ✅
3. [Cart App](#3-cart-app) ✅
4. [Orders App](#4-orders-app) ✅
5. [Reviews App](#5-reviews-app) ✅
6. [Contact App](#6-contact-app) ✅
7. [Coupons App](#7-coupons-app) ✅
8. [Payments App](#8-payments-app) ✅
9. [Notifications App](#9-notifications-app) ✅
10. [Cross-App Relationships](#10-cross-app-relationships) *(built after all apps)*## 9. Notifications App

**App Label:** `notifications`
**Purpose:** Manages outbound customer notifications across WhatsApp,
SMS, Email, and In-App channels. Tracks send status and failure
reasons per notification. Provides a dedicated COD order verification
flow via WhatsApp Business API to reduce Return-to-Origin (RTO) rates —
a critical operational concern for Pakistani COD ecommerce.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 9.1 `notifications_notification`

A single outbound notification dispatched to a user or recipient
across any supported channel. In-App notifications are read via
the `is_read` flag. SMS and WhatsApp use `recipient_phone`.
Email uses `recipient_email`. `context_data` carries dynamic
template variables for message rendering.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `CASCADE` on delete. `NULL` = guest/anonymous recipient |
| `recipient_phone` | `CharField(15)` | `VARCHAR(15)` | `NULL` | `NULL` | Required for `SMS` and `WHATSAPP` channels. Format `+923XXXXXXXXX` |
| `recipient_email` | `EmailField` | `VARCHAR(254)` | `NULL` | `NULL` | Required for `EMAIL` channel |
| `channel` | `CharField(15)` | `VARCHAR(15)` | `NOT NULL` | — | See Channel choices below |
| `notification_type` | `CharField(25)` | `VARCHAR(25)` | `NOT NULL` | — | See Notification Type choices below |
| `title` | `CharField(150)` | `VARCHAR(150)` | `NOT NULL` | — | Notification headline or subject |
| `body` | `TextField` | `TEXT` | `NOT NULL` | — | Full notification message body |
| `context_data` | `JSONField` | `JSONB` | `NULL` | `NULL` | Dynamic template variables e.g. `{"order_id": "MBP-001", "awb": "TCS-99"}` |
| `is_sent` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` after successful dispatch to gateway |
| `sent_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Timestamp of successful dispatch |
| `is_read` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | Read state for `IN_APP` channel only |
| `failure_reason` | `TextField` | `TEXT` | `NOT NULL` | `''` | Gateway error detail on failed dispatch |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `notifications_notif_user_idx` | `user_id` | `BTREE` |
| `notifications_notif_user_read_idx` | `user_id`, `is_read` | `BTREE` |
| `notifications_notif_channel_sent_idx` | `channel`, `is_sent`, `created_at` | `BTREE` |

**Channel Choices:**

| Display | DB Value | Recipient Field Used |
|---|---|---|
| WhatsApp Business API | `WHATSAPP` | `recipient_phone` |
| SMS (Local Gateway) | `SMS` | `recipient_phone` |
| Email | `EMAIL` | `recipient_email` |
| In-App Push / Bell Icon | `IN_APP` | `user_id` |

**Notification Type Choices:**

| Display | DB Value | Typical Channel |
|---|---|---|
| COD Order Verification | `COD_VERIFICATION` | `WHATSAPP` |
| Order Placed | `ORDER_PLACED` | `EMAIL`, `WHATSAPP` |
| Order Shipped (AWB Attached) | `ORDER_SHIPPED` | `WHATSAPP`, `SMS` |
| Rider Out For Delivery | `OUT_FOR_DELIVERY` | `WHATSAPP`, `SMS` |
| Marketing / Discount Alert | `PROMOTIONAL` | `WHATSAPP`, `EMAIL` |
| System / Security Alert | `SYSTEM_ALERT` | `EMAIL`, `IN_APP` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `notifications_notification` → `accounts_user` | Many-to-One | `CASCADE` |

**Channel-Recipient Validation Logic** *(enforced at application layer)*:

```
channel == WHATSAPP or SMS  → recipient_phone must not be NULL
channel == EMAIL            → recipient_email must not be NULL
channel == IN_APP           → user_id must not be NULL
is_sent == TRUE             → sent_at must not be NULL
is_sent == FALSE            → sent_at must be NULL
```

---

### 9.2 `notifications_whatsappcodverification`

Tracks the lifecycle of an automated WhatsApp message sent to
verify a COD order before dispatch. Prevents RTO by confirming
customer intent before the order leaves the warehouse. One record
per order — enforced via `unique=True` on `order_id`.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `order_id` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Soft reference to `orders_order`. See ISSUE-NOTIF03 |
| `phone_number` | `CharField(15)` | `VARCHAR(15)` | `NOT NULL` | — | Customer WhatsApp number. Format `+923XXXXXXXXX` |
| `meta_message_id` | `CharField(150)` | `VARCHAR(150)` | `NULL` | `NULL` | WhatsApp Business API message ID for delivery tracking |
| `status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL`, `INDEX` | `'PENDING_REPLY'` | See Verification Status choices below |
| `customer_reply_text` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | `''` | Raw reply text received from customer via webhook |
| `verified_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Timestamp when customer confirmed or cancelled |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `notifications_wacodverif_order_idx` | `order_id` | `UNIQUE BTREE` |
| `notifications_wacodverif_status_idx` | `status` | `BTREE` |

**Verification Status Choices:**

| Display | DB Value | Notes |
|---|---|---|
| Message Sent - Awaiting Reply | `PENDING_REPLY` | Initial state after WhatsApp message dispatched |
| Customer Confirmed via WhatsApp | `CONFIRMED` | Order proceeds to fulfilment |
| Customer Cancelled via WhatsApp | `CANCELLED` | Order moves to `CANCELLED` status |
| No Response (Manual Call Required) | `TIMEOUT` | Celery task triggers after configurable window |

**Verification Lifecycle:**

```
COD order placed
→ WhatsApp message sent → record created (PENDING_REPLY)
→ Customer replies YES  → status = CONFIRMED, verified_at = now()
                        → Order.status → CONFIRMED
→ Customer replies NO   → status = CANCELLED, verified_at = now()
                        → Order.status → CANCELLED
→ No reply in window   → Celery beat task → status = TIMEOUT
                        → triggers manual call queue
```

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `notifications_whatsappcodverification` → `orders_order` | Soft reference via `order_id` string | See ISSUE-NOTIF03 |

---


---

## 1. Accounts App

**App Label:** `accounts`
**Purpose:** Manages user identity, authentication, email verification,
password reset, and extended profile data.
**Status:** ✅ Migrated

---

### 1.1 `accounts_user`

Custom user model. Replaces Django's default `auth_user`.
Uses **email** as the primary login identifier.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | Django default PK |
| `email` | `EmailField` | `VARCHAR(254)` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Primary login identifier |
| `full_name` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | — | Single field — intentional for Pakistani names |
| `role` | `CharField(2)` | `VARCHAR(2)` | `NOT NULL` | `'CU'` | See Role choices below |
| `password` | Inherited | `VARCHAR(128)` | `NOT NULL` | — | Hashed. Provided by `AbstractBaseUser` |
| `last_login` | Inherited | `TIMESTAMPTZ` | `NULL` | `NULL` | Provided by `AbstractBaseUser` |
| `is_active` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | Soft disable instead of deletion |
| `is_staff` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | Django admin access |
| `is_verified` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | Email verification status |
| `is_superuser` | Inherited | `BOOLEAN` | `NOT NULL` | `FALSE` | Provided by `PermissionsMixin` |
| `date_joined` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `timezone.now` | Account creation timestamp |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `accounts_user_email_idx` | `email` | `UNIQUE BTREE` |

**`Role` Enum Choices** *(defined in `apps.common.choices.role`)*:

| Display | DB Value |
|---|---|
| Customer | `CU` |
| Admin | `AD` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `accounts_user` → `accounts_userprofile` | One-to-One | `CASCADE` |
| `accounts_user` → `accounts_emailverificationtoken` | One-to-Many | `CASCADE` |
| `accounts_user` → `accounts_passwordresettoken` | One-to-Many | `CASCADE` |

---

### 1.2 `accounts_userprofile`

Extended personal information for a user.
Created automatically via Django signal on `User` post-save.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL` | Auto | — |
| `user_id` | `OneToOneField → User` | `BIGINT` | `UNIQUE`, `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `phone` | `CharField(15)` | `VARCHAR(15)` | `NOT NULL` | `''` | Pakistani format: `+923001234567` or `03001234567` |
| `date_of_birth` | `DateField` | `DATE` | `NULL` | `NULL` | Optional |
| `gender` | `CharField(1)` | `VARCHAR(1)` | `NOT NULL` | `''` | See Gender choices below |
| `avatar` | `ImageField` | `VARCHAR(255)` | `NULL` | `NULL` | Stored path. Uploads to `avatars/%Y/%m/` |
| `address_line1` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | `''` | Primary street address |
| `address_line2` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | `''` | Apartment / floor / area |
| `city` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | `''` | — |
| `province` | `CharField(2)` | `VARCHAR(2)` | `NOT NULL` | `''` | See Province choices below |
| `postal_code` | `CharField(10)` | `VARCHAR(10)` | `NOT NULL` | `''` | Pakistani 5-digit postal code |
| `country` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | `'Pakistan'` | Single-country ecommerce default |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**`Gender` Choices:**

| Display | DB Value |
|---|---|
| Male | `M` |
| Female | `F` |
| Other | `O` |
| Prefer not to say | `N` |

**`Province` Choices:**

| Display | DB Value |
|---|---|
| Punjab | `PB` |
| Sindh | `SD` |
| Khyber Pakhtunkhwa | `KP` |
| Balochistan | `BL` |
| Gilgit-Baltistan | `GB` |
| Azad Jammu & Kashmir | `AK` |
| Islamabad Capital Territory | `IC` |

**Computed Properties** *(Python level — not stored in DB)*:

| Property | Returns | Notes |
|---|---|---|
| `has_complete_address` | `bool` | True if `address_line1`, `city`, `province`, `postal_code` all non-empty |
| `full_address` | `str` | All address parts joined with `, ` |

---

### 1.3 `accounts_emailverificationtoken`

One-time token for email address verification.
Expires after **24 hours**. All previous tokens for a user
are deleted before a new one is created.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `token` | `UUIDField` | `UUID` | `UNIQUE`, `NOT NULL`, `INDEX` | `uuid4` | Non-editable. Used in verification URL |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | — |
| `expires_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | Set in `save()` | `created_at + 24 hours` |

**Indexes:**

| Index Name | Column | Type |
|---|---|---|
| `accounts_emailverif_token_idx` | `token` | `UNIQUE BTREE` |
| `accounts_emailverif_user_idx` | `user_id` | `BTREE` |

**Token Lifecycle:**

```
Register → token created → email sent → user clicks link
→ lookup by UUID → check expiry → User.is_verified = True
→ token deleted on next resend via create_for_user()
```

---

### 1.4 `accounts_passwordresettoken`

Single-use token for password reset.
Expires after **1 hour**. Marked `is_used=True` after consumption.
All previous tokens deleted when a new one is requested.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `token` | `UUIDField` | `UUID` | `UNIQUE`, `NOT NULL`, `INDEX` | `uuid4` | Non-editable |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | — |
| `expires_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | Set in `save()` | `created_at + 1 hour` |
| `is_used` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` after successful reset — prevents replay |

**Indexes:**

| Index Name | Column | Type |
|---|---|---|
| `accounts_pwreset_token_idx` | `token` | `UNIQUE BTREE` |
| `accounts_pwreset_user_idx` | `user_id` | `BTREE` |

**Token Lifecycle:**

```
Request reset → old tokens deleted → new token created → email sent
→ user clicks link → lookup by UUID → check is_used + expiry
→ password updated → mark_used() → is_used = TRUE
```

**Computed Properties** *(Python level — not stored in DB)*:

| Property | Logic |
|---|---|
| `is_expired` | `timezone.now() > expires_at` |
| `is_valid` | `NOT is_used AND NOT is_expired` |

---



---

## 2. Products App

**App Label:** `products`
**Purpose:** Manages motorbike parts catalog including categories, brands,
bike model compatibility, product listings, and image galleries.
**Status:** ✅ Migrated

---

### 2.1 `products_category`

Hierarchical product category with optional self-referencing parent.
Supports unlimited nesting depth (e.g. Engine → Pistons → Piston Rings).

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `name` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL` | — | Category display name |
| `slug` | `SlugField(120)` | `VARCHAR(120)` | `UNIQUE`, `NOT NULL` | Auto from `name` | Auto-generated via `slugify(name)` on first save |
| `parent_id` | `ForeignKey → self` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `CASCADE` on delete. `NULL` = root category |
| `is_active` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | Soft disable without deletion |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `products_category_name_idx` | `name` | `UNIQUE BTREE` |
| `products_category_slug_idx` | `slug` | `UNIQUE BTREE` |
| `products_category_parent_idx` | `parent_id` | `BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `products_category` → `products_category` (self) | Many-to-One | `CASCADE` |
| `products_category` → `products_product` | One-to-Many | `PROTECT` |

**Computed Properties** *(Python level — not stored in DB)*:

| Property | Returns | Notes |
|---|---|---|
| `is_subcategory` | `bool` | `True` if `parent_id` is not `NULL` |

---

### 2.2 `products_brand`

Motorbike part manufacturer or brand (Honda, Yamaha, Suzuki, etc.).

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `name` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL` | — | Brand display name |
| `slug` | `SlugField(120)` | `VARCHAR(120)` | `UNIQUE`, `NOT NULL` | Auto from `name` | Auto-generated via `slugify(name)` on first save |
| `logo` | `ImageField` | `VARCHAR(255)` | `NULL` | `NULL` | Stored path. Uploads to `brands/` |
| `is_active` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | Soft disable without deletion |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `products_brand_name_idx` | `name` | `UNIQUE BTREE` |
| `products_brand_slug_idx` | `slug` | `UNIQUE BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `products_brand` → `products_bikemodel` | One-to-Many | `CASCADE` |
| `products_brand` → `products_product` | One-to-Many | `SET NULL` |

---

### 2.3 `products_bikemodel`

Specific motorbike model used for product compatibility matching.
Core differentiator — customers filter parts by their exact bike.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `brand_id` | `ForeignKey → Brand` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `name` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | — | e.g. `CB150F`, `YBR125` |
| `slug` | `SlugField(150)` | `VARCHAR(150)` | `UNIQUE`, `NOT NULL` | Auto from `brand+name` | Auto-generated via `slugify(brand.name-name)` |
| `year_start` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | — | Production start year |
| `year_end` | `PositiveIntegerField` | `INTEGER` | `NULL` | `NULL` | Production end year. `NULL` = still in production |
| `is_active` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | Soft disable without deletion |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `products_bikemodel_slug_idx` | `slug` | `UNIQUE BTREE` |
| `products_bikemodel_brand_idx` | `brand_id` | `BTREE` |
| `products_bikemodel_brand_name_uniq` | `brand_id`, `name` | `UNIQUE BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `products_bikemodel` → `products_brand` | Many-to-One | `CASCADE` |
| `products_bikemodel` ↔ `products_product` | Many-to-Many | Via junction table |

**Computed Properties** *(Python level — not stored in DB)*:

| Property / Method | Returns | Notes |
|---|---|---|
| `display_name` | `str` | `"{brand.name} {name}"` |
| `covers_year(year)` | `bool` | True if bike was in production during given year |

---

### 2.4 `products_product`

Motorbike part product listing. Core catalog entity.
Compatibility with bike models handled via ManyToMany.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `name` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | — | Product display name |
| `slug` | `SlugField(280)` | `VARCHAR(280)` | `UNIQUE`, `NOT NULL` | Auto from `name` | Auto-generated via `slugify(name)` on first save |
| `category_id` | `ForeignKey → Category` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `PROTECT` on delete — category cannot be deleted while products exist |
| `brand_id` | `ForeignKey → Brand` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete. `NULL` = universal or aftermarket part |
| `description` | `TextField` | `TEXT` | `NOT NULL` | `''` | Full product description |
| `sku` | `CharField(50)` | `VARCHAR(50)` | `UNIQUE`, `NOT NULL` | — | Stock keeping unit — unique product code |
| `price` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | Base price. Min value `0` |
| `discount_price` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NULL` | `NULL` | Sale price. Min value `0`. `NULL` = no active discount |
| `stock` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Current stock quantity |
| `status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | `'available'` | See Status choices below |
| `is_featured` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | Flag for homepage / featured section |
| `created_by_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete. Admin who created listing |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `products_product_slug_idx` | `slug` | `UNIQUE BTREE` |
| `products_product_sku_idx` | `sku` | `UNIQUE BTREE` |
| `products_product_status_idx` | `status` | `BTREE` |
| `products_product_category_status_idx` | `category_id`, `status` | `BTREE` |

**`Status` Choices:**

| Display | DB Value |
|---|---|
| Available | `available` |
| Out of Stock | `out_of_stock` |
| Discontinued | `discontinued` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `products_product` → `products_category` | Many-to-One | `PROTECT` |
| `products_product` → `products_brand` | Many-to-One | `SET NULL` |
| `products_product` → `accounts_user` | Many-to-One | `SET NULL` |
| `products_product` ↔ `products_bikemodel` | Many-to-Many | Via `products_product_compatible_bikes` junction table |
| `products_product` → `products_productimage` | One-to-Many | `CASCADE` |

**Junction Table — `products_product_compatible_bikes`:**

| Column | DB Type | Constraints |
|---|---|---|
| `id` | `BIGINT` | `PK`, `NOT NULL` |
| `product_id` | `BIGINT` | `FK → products_product`, `NOT NULL`, `INDEX` |
| `bikemodel_id` | `BIGINT` | `FK → products_bikemodel`, `NOT NULL`, `INDEX` |

> Auto-generated by Django for the `compatible_bikes` ManyToManyField.
> Pair `(product_id, bikemodel_id)` is implicitly unique.

**Computed Properties** *(Python level — not stored in DB)*:

| Property / Method | Returns | Notes |
|---|---|---|
| `is_in_stock` | `bool` | `True` if `stock > 0` AND `status == available` |
| `current_price` | `Decimal` | Returns `discount_price` if set, else `price` |
| `has_discount` | `bool` | `True` if `discount_price` is not `NULL` and less than `price` |
| `discount_percentage` | `int` | Rounded percentage saved. `0` if no discount |
| `is_compatible_with(bike_model_id)` | `bool` | Queries `compatible_bikes` ManyToMany |

---

### 2.5 `products_productimage`

Product image gallery. Supports multiple images per product
with one marked as primary for listing thumbnails.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `product_id` | `ForeignKey → Product` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `image` | `ImageField` | `VARCHAR(255)` | `NOT NULL` | — | Stored path. Uploads to `products/%Y/%m/` |
| `is_primary` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | Only one `TRUE` allowed per product. Enforced in `save()` |
| `order` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Display sort order. Lower = shown first |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `products_productimage_product_idx` | `product_id` | `BTREE` |

**Primary Image Enforcement:**
```
On save() — if is_primary=True:
  UPDATE products_productimage SET is_primary=FALSE
  WHERE product_id = this.product_id
  AND id != this.id
```
> Enforced at Python/ORM level in `save()`. No DB-level constraint.

---



---

## 3. Cart App

**App Label:** `cart`
**Purpose:** Manages per-user shopping carts, line items, quantity
validation against live stock, and monetary subtotal calculations.
**Status:** ✅ Migrated

---

### 3.1 `cart_cart`

One cart per user. Created automatically via post_save signal
on User creation. Totals are computed properties — not stored in DB.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `user_id` | `OneToOneField → User` | `BIGINT` | `UNIQUE`, `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete. One cart per user enforced at DB level |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `cart_cart_user_idx` | `user_id` | `UNIQUE BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `cart_cart` → `accounts_user` | One-to-One | `CASCADE` |
| `cart_cart` → `cart_cartitem` | One-to-Many | `CASCADE` |

**Computed Properties** *(Python level — not stored in DB)*:

| Property | Returns | Notes |
|---|---|---|
| `total_items` | `int` | Sum of all `CartItem.quantity`. Requires `prefetch_related('items')` |
| `total_price` | `Decimal` | Sum of all `CartItem.subtotal`. Requires `prefetch_related('items__product')` |
| `is_empty` | `bool` | `True` if cart has no items. Uses prefetch cache — no extra query |

> **Query Note:** All three properties use `self.items.all()` and rely
> on prefetch cache. Callers must use `prefetch_related('items__product')`
> on the queryset to avoid N+1 queries.

---

### 3.2 `cart_cartitem`

A single product line in a cart with quantity.
One product can appear only once per cart — enforced at DB level
via `unique_together`. Adding the same product again must increase
quantity at the view layer rather than inserting a duplicate row.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `cart_id` | `ForeignKey → Cart` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `product_id` | `ForeignKey → Product` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `quantity` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `1` | Min `1` enforced by `PositiveIntegerField`. Max = live stock — validated in `clean()` |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `cart_cartitem_cart_idx` | `cart_id` | `BTREE` |
| `cart_cartitem_product_idx` | `product_id` | `BTREE` |
| `cart_cartitem_cart_product_uniq` | `cart_id`, `product_id` | `UNIQUE BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `cart_cartitem` → `cart_cart` | Many-to-One | `CASCADE` |
| `cart_cartitem` → `products_product` | Many-to-One | `CASCADE` |

**Validation Logic** *(Python level — enforced via `full_clean()` on every `save()`)*:

| Rule | Where Enforced | Notes |
|---|---|---|
| `quantity <= product.stock` | `clean()` → called in `save()` | Raises `ValidationError` if exceeded |
| One product per cart | `unique_together` at DB level | `IntegrityError` on duplicate insert |

**Computed Properties** *(Python level — not stored in DB)*:

| Property | Returns | Notes |
|---|---|---|
| `subtotal` | `Decimal` | `product.current_price × quantity`. Requires `select_related('product')` |

---


---

## 4. Orders App

**App Label:** `orders`
**Purpose:** Manages customer orders from placement through delivery.
Captures full address and pricing snapshots at order time to protect
historical accuracy against future data changes. Tracks order lifecycle
via status timestamps and an immutable audit log.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 4.1 `orders_order`

Core order record. Created from cart contents at checkout.
Stores a full snapshot of shipping address and financial totals
at the moment of order placement. Live product/user data changes
do not affect historical order records.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `PROTECT` on delete — user cannot be deleted while orders exist |
| `order_number` | `CharField(20)` | `VARCHAR(20)` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Human-readable order reference e.g. `MBP-20240001` |
| `status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | `'pending'` | See Order Status choices below |
| `payment_method` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | — | See Payment Method choices below |
| `payment_status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | `'pending'` | See Payment Status choices below |
| `subtotal` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | Sum of all line item subtotals before shipping |
| `shipping_fee` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | `0` | Shipping cost added at checkout |
| `total_price` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | `subtotal + shipping_fee` |
| `shipping_full_name` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | — | Recipient name snapshot |
| `shipping_phone` | `CharField(15)` | `VARCHAR(15)` | `NOT NULL` | — | Recipient phone snapshot |
| `shipping_address_line1` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | — | Street address snapshot |
| `shipping_address_line2` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | `''` | Apartment / floor snapshot |
| `shipping_city` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | — | City snapshot |
| `shipping_province` | `CharField(2)` | `VARCHAR(2)` | `NOT NULL` | — | Province code snapshot. Same choices as `accounts_userprofile.province` |
| `shipping_postal_code` | `CharField(10)` | `VARCHAR(10)` | `NOT NULL` | — | Postal code snapshot |
| `notes` | `TextField` | `TEXT` | `NOT NULL` | `''` | Customer delivery instructions |
| `placed_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | Order submission timestamp |
| `confirmed_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Set when status → `confirmed` |
| `shipped_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Set when status → `shipped` |
| `delivered_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Set when status → `delivered` |
| `cancelled_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Set when status → `cancelled` |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

> **Note on `placed_at` vs `created_at`:** Both are `auto_now_add`.
> `placed_at` is the business-facing order timestamp shown to customers.
> `created_at` is the technical record creation timestamp from `TimeStampedModel`.
> These will always hold the same value — see ISSUE-O01 in SCHEMA_ISSUES.md.

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `orders_order_order_number_idx` | `order_number` | `UNIQUE BTREE` |
| `orders_order_user_idx` | `user_id` | `BTREE` |
| `orders_order_status_idx` | `status` | `BTREE` |
| `orders_order_placed_at_idx` | `placed_at` | `BTREE` |

**Order Status Choices:**

| Display | DB Value | Timestamp Field Set |
|---|---|---|
| Pending | `pending` | `placed_at` |
| Confirmed | `confirmed` | `confirmed_at` |
| Processing | `processing` | — |
| Shipped | `shipped` | `shipped_at` |
| Delivered | `delivered` | `delivered_at` |
| Cancelled | `cancelled` | `cancelled_at` |
| Refunded | `refunded` | — |

**Payment Method Choices:**

| Display | DB Value |
|---|---|
| Cash on Delivery | `cash_on_delivery` |
| Bank Transfer | `bank_transfer` |

**Payment Status Choices:**

| Display | DB Value |
|---|---|
| Pending | `pending` |
| Paid | `paid` |
| Failed | `failed` |
| Refunded | `refunded` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `orders_order` → `accounts_user` | Many-to-One | `PROTECT` |
| `orders_order` → `orders_orderitem` | One-to-Many | `CASCADE` |
| `orders_order` → `orders_orderstatuslog` | One-to-Many | `CASCADE` |

---

### 4.2 `orders_orderitem`

Individual product line within an order. Fully snapshotted at order
placement time — product name, SKU, and unit price are copied from
the live product so historical orders remain accurate even if the
product is later renamed, repriced, or deleted.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `order_id` | `ForeignKey → Order` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `product_id` | `ForeignKey → Product` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `PROTECT` on delete — product cannot be hard deleted while in orders |
| `product_name` | `CharField(255)` | `VARCHAR(255)` | `NOT NULL` | — | Product name snapshot at order time |
| `product_sku` | `CharField(50)` | `VARCHAR(50)` | `NOT NULL` | — | SKU snapshot at order time |
| `unit_price` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | Price per unit snapshot at order time |
| `quantity` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | — | Units ordered |
| `subtotal` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | `unit_price × quantity` — snapshotted at order time |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `orders_orderitem_order_idx` | `order_id` | `BTREE` |
| `orders_orderitem_product_idx` | `product_id` | `BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `orders_orderitem` → `orders_order` | Many-to-One | `CASCADE` |
| `orders_orderitem` → `products_product` | Many-to-One | `PROTECT` |

**Snapshot Strategy:**

```
At order placement:
  product_name  ← product.name
  product_sku   ← product.sku
  unit_price    ← product.current_price   (discount_price if active, else price)
  subtotal      ← unit_price × quantity
```

> Once written these snapshot fields must never be updated.
> They represent the exact state of the transaction at purchase time.

---

### 4.3 `orders_orderstatuslog`

Immutable audit trail of every order status transition.
Records who made the change, when, and optionally why.
Rows are never updated or deleted — append-only by design.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `order_id` | `ForeignKey → Order` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `from_status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | — | Status before transition |
| `to_status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | — | Status after transition |
| `changed_by_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete — preserve log even if admin user deleted |
| `note` | `TextField` | `TEXT` | `NOT NULL` | `''` | Internal trace note — reason for transition |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | Transition timestamp — immutable |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `orders_orderstatuslog_order_idx` | `order_id` | `BTREE` |
| `orders_orderstatuslog_changed_by_idx` | `changed_by_id` | `BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `orders_orderstatuslog` → `orders_order` | Many-to-One | `CASCADE` |
| `orders_orderstatuslog` → `accounts_user` | Many-to-One | `SET NULL` |

**Immutability Rules:**
```
- Rows are INSERT only — no UPDATE, no DELETE
- No updated_at field — intentional, this model does not extend TimeStampedModel
- from_status + to_status must use valid Order.Status values
- Enforced at application layer — no DB trigger required at this scale
```

---


## 5. Reviews App

**App Label:** `reviews`
**Purpose:** Manages customer product reviews and star ratings.
Links reviews to verified purchase order items to distinguish
genuine buyers from unverified reviewers. Includes moderation
approval flow before public display.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 5.1 `reviews_review`

Customer product review with star rating, optional headline,
and review body. One review per user per product enforced at
DB level. Optionally linked to the exact `OrderItem` that
triggered the purchase to flag verified reviews.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `product_id` | `ForeignKey → Product` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete — reviews deleted if product hard deleted |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete — reviews deleted if user deleted |
| `order_item_id` | `ForeignKey → OrderItem` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete. `NULL` = unverified review. Non-null = verified purchase |
| `rating` | `SmallIntegerField` | `SMALLINT` | `NOT NULL` | — | Range `1–5`. Enforced via `MinValueValidator` / `MaxValueValidator` |
| `title` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | `''` | Optional review headline |
| `body` | `TextField` | `TEXT` | `NOT NULL` | `''` | Optional full review text |
| `is_approved` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | Moderation flag. `FALSE` = hidden from public display |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `reviews_review_product_idx` | `product_id` | `BTREE` |
| `reviews_review_user_idx` | `user_id` | `BTREE` |
| `reviews_review_order_item_idx` | `order_item_id` | `BTREE` |
| `reviews_review_rating_idx` | `rating` | `BTREE` |
| `reviews_review_product_user_uniq` | `product_id`, `user_id` | `UNIQUE BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `reviews_review` → `products_product` | Many-to-One | `CASCADE` |
| `reviews_review` → `accounts_user` | Many-to-One | `CASCADE` |
| `reviews_review` → `orders_orderitem` | Many-to-One | `SET NULL` |

**Verified Purchase Logic:**

```
order_item_id IS NOT NULL → verified purchase review
order_item_id IS NULL     → unverified / anonymous review

Verified check at submission:
  OrderItem.objects.filter(
      order__user=request.user,
      product=product,
  ).exists()
```

---

## 6. Contact App

**App Label:** `contact`
**Purpose:** Manages inbound customer support inquiries submitted via
the contact form. Supports both authenticated users and anonymous
visitors. Tracks resolution workflow — which admin resolved the
ticket and when.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 6.1 `contact_contactmessage`

A single customer support inquiry. Can be submitted by an
authenticated user or an anonymous visitor. Admin resolution
workflow tracked via `is_resolved`, `resolved_by`, and
`resolved_at` fields.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete. `NULL` = anonymous visitor submission |
| `name` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL` | — | Sender display name |
| `email` | `EmailField` | `VARCHAR(254)` | `NOT NULL` | — | Reply-to address for admin responses |
| `phone` | `CharField(15)` | `VARCHAR(15)` | `NOT NULL` | `''` | Optional contact number |
| `subject` | `CharField(200)` | `VARCHAR(200)` | `NOT NULL` | — | Inquiry subject title |
| `message` | `TextField` | `TEXT` | `NOT NULL` | — | Full inquiry message body |
| `is_resolved` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | Resolution status flag |
| `resolved_by_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete. Admin who closed the ticket |
| `resolved_at` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Timestamp when ticket was marked resolved |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel`. Inquiry submission time |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `contact_contactmessage_user_idx` | `user_id` | `BTREE` |
| `contact_contactmessage_resolved_by_idx` | `resolved_by_id` | `BTREE` |
| `contact_contactmessage_is_resolved_idx` | `is_resolved` | `BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `contact_contactmessage` → `accounts_user` (sender) | Many-to-One | `SET NULL` |
| `contact_contactmessage` → `accounts_user` (resolver) | Many-to-One | `SET NULL` |

**Resolution Workflow:**

```
Inquiry submitted → is_resolved=FALSE, resolved_by=NULL, resolved_at=NULL
Admin reviews → marks resolved
→ is_resolved=TRUE
→ resolved_by_id = admin user id
→ resolved_at = timezone.now()
```

---


## 7. Coupons App

**App Label:** `coupons`
**Purpose:** Manages discount coupons including percentage discounts,
fixed PKR amount discounts, and free shipping codes. Enforces global
usage limits, per-user usage limits, validity windows, and minimum
order thresholds. Tracks every coupon redemption against an order
for audit and limit enforcement.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 7.1 `coupons_coupon`

A single discount coupon with configurable type, value, validity
window, and usage limits. Supports both authenticated users and
guest checkouts tracked by phone number.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `code` | `CharField(50)` | `VARCHAR(50)` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Human-readable code e.g. `EIDMUBARAK2026`. Case handling — see ISSUE-CPN01 |
| `discount_type` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | `'FIXED_PKR'` | See Discount Type choices below |
| `discount_value` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | Percentage (0–100) or fixed PKR amount. Min `0.00` |
| `min_order_amount` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | `0.00` | Minimum cart subtotal in PKR required to apply coupon |
| `max_discount_amount` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NULL` | `NULL` | PKR cap on percentage discounts. `NULL` = no cap |
| `usage_limit_total` | `PositiveIntegerField` | `INTEGER` | `NULL` | `NULL` | Global usage cap. `NULL` = unlimited |
| `usage_limit_per_user` | `PositiveSmallIntegerField` | `SMALLINT` | `NOT NULL` | `1` | Max times one user can use this coupon |
| `total_used` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Running count of total redemptions. Incremented on each use |
| `valid_from` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | — | Coupon activation start datetime |
| `valid_until` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | — | Coupon expiry datetime |
| `is_active` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | Admin toggle to disable coupon without deletion |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `coupons_coupon_code_idx` | `code` | `UNIQUE BTREE` |
| `coupons_coupon_lookup_idx` | `code`, `is_active`, `valid_until` | `BTREE` |

**Discount Type Choices:**

| Display | DB Value | Behaviour |
|---|---|---|
| Percentage Discount | `PERCENTAGE` | `discount_value` treated as `%`. Capped by `max_discount_amount` if set |
| Fixed Amount (PKR) | `FIXED_PKR` | `discount_value` deducted directly from order subtotal |
| Free Shipping | `FREE_SHIPPING` | `shipping_fee` set to `0`. `discount_value` ignored |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `coupons_coupon` → `coupons_couponusage` | One-to-Many | `PROTECT` |

**Coupon Validity Logic** *(enforced at application layer)*:

```
A coupon is redeemable when ALL of the following are true:
  1. is_active = TRUE
  2. timezone.now() >= valid_from
  3. timezone.now() <= valid_until
  4. total_used < usage_limit_total  (if usage_limit_total is not NULL)
  5. user usage count < usage_limit_per_user
  6. cart subtotal >= min_order_amount
```

---

### 7.2 `coupons_couponusage`

Records every coupon redemption. Used to enforce both global
and per-user usage limits. Tracks guest checkouts by phone number
in addition to authenticated user FK. Links to order via
`order_id` string reference.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `coupon_id` | `ForeignKey → Coupon` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `PROTECT` on delete — coupon cannot be deleted while usage records exist |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `CASCADE` on delete. `NULL` = guest checkout |
| `phone_number` | `CharField(15)` | `VARCHAR(15)` | `NOT NULL`, `INDEX` | — | Pakistani phone number. Used to track guest coupon usage |
| `order_id` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL` | — | String reference to `orders_order`. See ISSUE-CPN03 |
| `discount_applied` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | Actual PKR discount amount applied to this order |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `coupons_couponusage_coupon_idx` | `coupon_id` | `BTREE` |
| `coupons_couponusage_user_idx` | `user_id` | `BTREE` |
| `coupons_couponusage_phone_idx` | `phone_number` | `BTREE` |
| `coupons_couponusage_order_uniq` | `order_id` | `UNIQUE BTREE` |
| `coupons_couponusage_coupon_user_order_uniq` | `coupon_id`, `user_id`, `order_id` | `UNIQUE BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `coupons_couponusage` → `coupons_coupon` | Many-to-One | `PROTECT` |
| `coupons_couponusage` → `accounts_user` | Many-to-One | `CASCADE` |

**Per-User Limit Enforcement Query:**

```python
# Check how many times a user has used a coupon before applying:
user_usage_count = CouponUsage.objects.filter(
    coupon=coupon,
    user=request.user,
).count()

if user_usage_count >= coupon.usage_limit_per_user:
    raise CouponLimitExceeded()
```

---

## 8. Payments App

**App Label:** `payments`
**Purpose:** Records every payment transaction attempt against an order
across multiple Pakistani payment gateways. Logs all inbound webhook
payloads from gateways for cryptographic verification, debugging, and
audit. Supports idempotency to prevent double-charging on retries.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 8.1 `payments_paymenttransaction`

A single payment attempt against an order. Multiple transactions
can exist per order — initial attempt, retry, refund. Gateway
transaction reference and idempotency key prevent duplicate
processing. COD orders generate a transaction record in `PENDING`
state that resolves to `SUCCESS` on delivery confirmation.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `order_id` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | — | Soft reference to `orders_order`. See ISSUE-PAY01 |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `SET NULL` on delete — preserve transaction records if user deleted |
| `gateway` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | `'COD'` | See Gateway choices below |
| `status` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL`, `INDEX` | `'PENDING'` | See Transaction Status choices below |
| `amount_pkr` | `DecimalField(12,2)` | `NUMERIC(12,2)` | `NOT NULL` | — | Transaction amount in PKR. Min `0.00` |
| `transaction_reference` | `CharField(150)` | `VARCHAR(150)` | `UNIQUE`, `NULL` | `NULL` | Gateway-assigned transaction ID. `NULL` for COD until confirmed |
| `idempotency_key` | `UUIDField` | `UUID` | `UNIQUE`, `NULL` | `NULL` | Client-generated key to prevent double-charging on retries |
| `error_message` | `TextField` | `TEXT` | `NOT NULL` | `''` | Gateway error detail on failed transactions |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel`. Transaction initiation time |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel`. Last status update time |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `payments_txn_order_idx` | `order_id` | `BTREE` |
| `payments_txn_user_idx` | `user_id` | `BTREE` |
| `payments_txn_status_idx` | `status` | `BTREE` |
| `payments_txn_transaction_ref_idx` | `transaction_reference` | `UNIQUE BTREE` |
| `payments_txn_idempotency_idx` | `idempotency_key` | `UNIQUE BTREE` |
| `payments_txn_order_status_idx` | `order_id`, `status` | `BTREE` |
| `payments_txn_gateway_status_idx` | `gateway`, `status` | `BTREE` |

**Gateway Choices:**

| Display | DB Value | Notes |
|---|---|---|
| Cash on Delivery | `COD` | Default. No online payment processing |
| Safepay | `SAFEPAY` | Card processing gateway |
| PayFast | `PAYFAST` | Pakistani payment gateway |
| JazzCash Mobile Wallet / Card | `JAZZCASH` | Mobile wallet and card |
| Easypaisa | `EASYPAISA` | Mobile wallet |
| Raast Instant Transfer | `RAAST` | SBP interbank instant transfer |
| XPay by PostEx | `XPAY` | PostEx integrated payment |

**Transaction Status Choices:**

| Display | DB Value | Notes |
|---|---|---|
| Pending | `PENDING` | Initial state. COD stays here until delivery |
| Authorized | `AUTHORIZED` | Payment authorised but not yet captured |
| Success | `SUCCESS` | Payment captured and confirmed |
| Failed | `FAILED` | Payment attempt failed |
| Refunded | `REFUNDED` | Full refund processed |
| Partially Refunded | `PARTIALLY_REFUNDED` | Partial refund processed |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `payments_paymenttransaction` → `accounts_user` | Many-to-One | `SET NULL` |
| `payments_paymenttransaction` → `orders_order` | Soft reference via `order_id` string | See ISSUE-PAY01 |

**Idempotency Flow:**

```
Client generates UUID idempotency_key before checkout request
→ Server checks: PaymentTransaction.objects.filter(
      idempotency_key=key).exists()
→ If exists: return existing transaction — do not charge again
→ If not: create new transaction and initiate gateway charge
```

---

### 8.2 `payments_webhooklog`

Immutable append-only audit log for all inbound webhook payloads
from payment gateways and courier services. Stores raw payload
and headers to enable cryptographic signature re-verification
and post-incident debugging. Rows are never updated or deleted.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `gateway` | `CharField(50)` | `VARCHAR(50)` | `NOT NULL`, `INDEX` | — | Gateway name e.g. `JAZZCASH`, `EASYPAISA`. Free text — see ISSUE-PAY03 |
| `payload` | `JSONField` | `JSONB` | `NOT NULL` | — | Raw JSON body from gateway webhook request |
| `headers` | `JSONField` | `JSONB` | `NOT NULL` | — | HTTP request headers. Used for HMAC signature verification |
| `ip_address` | `GenericIPAddressField` | `INET` | `NULL` | `NULL` | Webhook sender IP. Used for gateway IP allowlist verification |
| `is_verified` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` if HMAC signature matched gateway secret |
| `processed_successfully` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` if webhook triggered successful business logic |
| `exception_trace` | `TextField` | `TEXT` | `NOT NULL` | `''` | Full Python traceback if processing raised an exception |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel`. Webhook receipt timestamp |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `payments_webhooklog_gateway_idx` | `gateway` | `BTREE` |
| `payments_webhooklog_created_at_idx` | `created_at` | `BTREE` |

**Immutability Rules:**

```
- Rows are INSERT only — no UPDATE, no DELETE after creation
- updated_at exists via TimeStampedModel but should never change
- is_verified and processed_successfully are set once at processing time
- exception_trace captured at processing time — never overwritten
- Celery task to purge records older than 180 days recommended
  to prevent unbounded table growth
```

---

