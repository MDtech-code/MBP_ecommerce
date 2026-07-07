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
10. [Logistics App](#10-logistics-app) ✅
11. [Analytics App](#11-analytics-app) ✅
12. [Recommendations App](#12-recommendations-app) ✅
13. [Cross-App Relationships](#13-cross-app-relationships) ✅


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

---

## 10. Logistics App

**App Label:** `logistics`
**Purpose:** Manages outbound shipments from warehouse to customer across
multiple Pakistani courier partners. Tracks full shipment lifecycle
including RTO and loss events. Handles COD financial reconciliation
via courier settlement records. `CourierPartner` is a shared enum
imported by the analytics app.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### Shared Enum — `CourierPartner`

Defined as a module-level `TextChoices` class in `logistics/models.py`.
Not a DB table — imported directly by `Shipment`, `CourierSettlement`,
and `analytics.CourierPerformanceMetric`.

| Display | DB Value |
|---|---|
| PostEx | `POSTEX` |
| TCS Courier | `TCS` |
| Leopards Courier | `LEOPARDS` |
| Trax Logistics | `TRAX` |
| InstaWorld | `INSTAWORLD` |
| Movex | `MOVEX` |
| In-House Fleet | `SELF_DELIVERY` |

> **Architectural Note:** `CourierPartner` is a plain `TextChoices`
> class — not a Django model. It produces no DB table. It is a shared
> enum imported across `logistics` and `analytics` apps.
> See ISSUE-LOG03 for centralisation recommendation.

---

### 10.1 `logistics_shipment`

A single physical shipment for an order dispatched via a courier
partner. One shipment per order enforced via `unique=True` on
`order_id`. Tracks full courier lifecycle from label creation
through delivery or RTO. Stores raw courier API response for
debugging and webhook reconciliation.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `order_id` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Soft reference to `orders_order`. See ISSUE-LOG01 |
| `courier` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | — | See `CourierPartner` enum above |
| `tracking_number` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Airway Bill (AWB) number assigned by courier |
| `status` | `CharField(25)` | `VARCHAR(25)` | `NOT NULL`, `INDEX` | `'LABEL_CREATED'` | See Shipment Status choices below |
| `is_cod` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `TRUE` | COD flag — determines if courier collects cash on delivery |
| `cod_amount` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | `0.00` | PKR amount courier must collect. `0.00` for prepaid orders |
| `shipping_cost_pkr` | `DecimalField(8,2)` | `NUMERIC(8,2)` | `NOT NULL` | — | Courier fee charged to seller per shipment |
| `destination_city` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | — | Delivery city e.g. `Lahore`, `Karachi`, `Rawalpindi` |
| `weight_kg` | `DecimalField(5,2)` | `NUMERIC(5,2)` | `NOT NULL` | `0.50` | Parcel weight. Used for courier rate calculation |
| `estimated_delivery_date` | `DateField` | `DATE` | `NULL` | `NULL` | Courier-provided estimated delivery date |
| `actual_delivery_date` | `DateTimeField` | `TIMESTAMPTZ` | `NULL` | `NULL` | Confirmed delivery timestamp from courier webhook |
| `raw_courier_response` | `JSONField` | `JSONB` | `NULL` | `NULL` | Raw courier API booking response for debugging |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `logistics_shipment_order_idx` | `order_id` | `UNIQUE BTREE` |
| `logistics_shipment_tracking_idx` | `tracking_number` | `UNIQUE BTREE` |
| `logistics_shipment_status_idx` | `status` | `BTREE` |
| `logistics_shipment_courier_status_idx` | `courier`, `status` | `BTREE` |
| `logistics_shipment_city_status_idx` | `destination_city`, `status` | `BTREE` |

**Shipment Status Choices:**

| Display | DB Value | Notes |
|---|---|---|
| Label Created / Booked | `LABEL_CREATED` | Initial state after courier booking API call |
| Picked Up by Courier | `PICKED_UP` | Courier collected parcel from warehouse |
| In Transit | `IN_TRANSIT` | Parcel moving between courier hubs |
| Out for Delivery | `OUT_FOR_DELIVERY` | Last-mile rider dispatched |
| Delivered | `DELIVERED` | Successfully delivered to customer |
| Return Requested | `RETURN_REQUESTED` | Customer or courier initiated return |
| Returned to Origin (In Transit) | `RTO_IN_TRANSIT` | Parcel returning to seller |
| Returned to Seller Warehouse | `RTO_DELIVERED` | RTO completed — parcel back at warehouse |
| Lost in Transit | `LOST` | Parcel confirmed lost by courier |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `logistics_shipment` → `orders_order` | Soft reference via `order_id` string | See ISSUE-LOG01 |
| `logistics_shipment` ↔ `logistics_couriersettlement` | Many-to-Many | Via junction table |

---

### 10.2 `logistics_couriersettlement`

Reconciles COD cash deposits received from courier partners
against delivered orders. Tracks the full financial lifecycle
of COD revenue — from courier collection to seller bank account.
Links to all `Shipment` records included in the settlement batch.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `courier` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | — | See `CourierPartner` enum above |
| `settlement_reference` | `CharField(100)` | `VARCHAR(100)` | `UNIQUE`, `NOT NULL` | — | Bank transfer ID or courier advice number |
| `total_cod_collected` | `DecimalField(12,2)` | `NUMERIC(12,2)` | `NOT NULL` | — | Total PKR collected from customers by courier |
| `total_shipping_deducted` | `DecimalField(10,2)` | `NUMERIC(10,2)` | `NOT NULL` | — | Courier shipping fees deducted from COD remittance |
| `net_payout_received` | `DecimalField(12,2)` | `NUMERIC(12,2)` | `NOT NULL` | — | Actual PKR deposited to seller bank account |
| `payout_date` | `DateField` | `DATE` | `NOT NULL` | — | Date bank deposit was received |
| `is_reconciled` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` after amounts verified against bank statement |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `logistics_settlement_ref_idx` | `settlement_reference` | `UNIQUE BTREE` |
| `logistics_settlement_courier_idx` | `courier` | `BTREE` |
| `logistics_settlement_payout_date_idx` | `payout_date` | `BTREE` |

**Junction Table — `logistics_couriersettlement_shipments_included`:**

| Column | DB Type | Constraints |
|---|---|---|
| `id` | `BIGINT` | `PK`, `NOT NULL` |
| `couriersettlement_id` | `BIGINT` | `FK → logistics_couriersettlement`, `NOT NULL`, `INDEX` |
| `shipment_id` | `BIGINT` | `FK → logistics_shipment`, `NOT NULL`, `INDEX` |

> Auto-generated by Django for `shipments_included` ManyToManyField.
> Pair `(couriersettlement_id, shipment_id)` is implicitly unique.

**Settlement Financial Validation** *(enforced at application layer)*:

```
Expected invariant:
  net_payout_received == total_cod_collected - total_shipping_deducted

Reconciliation flow:
  Settlement received from courier
  → create CourierSettlement record (is_reconciled=FALSE)
  → attach all Shipment records in this batch
  → verify net_payout_received matches bank statement
  → set is_reconciled=TRUE
```

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `logistics_couriersettlement` ↔ `logistics_shipment` | Many-to-Many | Via junction table |

---

## 11. Analytics App

**App Label:** `analytics`
**Purpose:** Stores pre-aggregated daily sales metrics and per-courier
performance metrics generated by nightly Celery jobs. Designed to
serve dashboard queries without touching live production order tables.
Depends on `logistics.CourierPartner` enum for courier choices.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 11.1 `analytics_dailysalessnapshot`

Pre-aggregated daily business metrics. One record per calendar day
enforced via `unique=True` on `date`. Generated by a nightly
Celery beat task that aggregates from `orders_order`,
`payments_paymenttransaction`, and `logistics_shipment` tables.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `date` | `DateField` | `DATE` | `UNIQUE`, `NOT NULL`, `INDEX` | — | Calendar date this snapshot covers |
| `total_orders` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Total orders placed on this date |
| `total_gmv_pkr` | `DecimalField(14,2)` | `NUMERIC(14,2)` | `NOT NULL` | `0.00` | Gross Merchandise Value — sum of all order totals |
| `net_revenue_pkr` | `DecimalField(14,2)` | `NUMERIC(14,2)` | `NOT NULL` | `0.00` | GMV minus discounts, refunds, and RTO losses |
| `cod_orders_count` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Orders paid via Cash on Delivery |
| `prepaid_orders_count` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Orders paid via online gateway |
| `total_discount_given_pkr` | `DecimalField(12,2)` | `NUMERIC(12,2)` | `NOT NULL` | `0.00` | Total coupon and promotional discounts applied |
| `rto_orders_count` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Orders returned to origin on this date |
| `rto_losses_pkr` | `DecimalField(12,2)` | `NUMERIC(12,2)` | `NOT NULL` | `0.00` | Wasted shipping fees due to RTO events |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel`. Snapshot generation timestamp |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel`. Last recalculation timestamp |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `analytics_dailysnapshot_date_idx` | `date` | `UNIQUE BTREE` |

**Snapshot Generation Contract:**

```
Celery beat task runs nightly at 00:05 PKT (UTC+5):
  → Aggregates previous day's orders, payments, shipments
  → Creates or updates DailySalesSnapshot for that date
  → Uses update_or_create(date=yesterday) — safe for reruns
  → Never reads from this table during aggregation — avoids deadlock
```

---

### 11.2 `analytics_courierperformancemetric`

Monthly per-courier per-city delivery performance metrics.
Used by the smart courier routing system to assign couriers
based on historical success rates — e.g. route Lahore orders
to Trax and rural Sindh orders to TCS based on tracked
delivery success rates and average delivery times.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `courier` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL` | — | See `CourierPartner` enum in logistics app |
| `city` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | — | Destination city name e.g. `Lahore`, `Karachi` |
| `month_year` | `CharField(7)` | `VARCHAR(7)` | `NOT NULL` | — | Format `YYYY-MM` e.g. `2026-07`. See ISSUE-ANA02 |
| `total_assigned` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Total shipments assigned to this courier in this city/month |
| `delivered_successfully` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Shipments reaching `DELIVERED` status |
| `rto_count` | `PositiveIntegerField` | `INTEGER` | `NOT NULL` | `0` | Shipments reaching `RTO_DELIVERED` status |
| `avg_delivery_time_hours` | `DecimalField(6,2)` | `NUMERIC(6,2)` | `NOT NULL` | `0.00` | Average hours from `PICKED_UP` to `DELIVERED` |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel` |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `analytics_couriermetric_city_courier_idx` | `city`, `courier` | `BTREE` |
| `analytics_couriermetric_unique` | `courier`, `city`, `month_year` | `UNIQUE BTREE` |

**Computed Properties** *(Python level — not stored in DB)*:

| Property | Returns | Notes |
|---|---|---|
| `delivery_success_rate` | `float` | `(delivered_successfully / total_assigned) × 100`. Returns `0.0` if `total_assigned == 0` |

**Relationships:**

| Relation | Type | Notes |
|---|---|---|
| `analytics_courierperformancemetric.courier` | Enum reference to `CourierPartner` | Not a FK — shares enum values only |

---


## 12. Recommendations App

**App Label:** `recommendations`
**Purpose:** Tracks high-throughput user interaction events for ML
pipeline ingestion. Stores pre-computed personalised product
recommendations per user generated by collaborative filtering
or embedding models. Designed for read-heavy frontend querying
and write-heavy event ingestion at separate throughput scales.
**Status:** 🟡 Not Yet Migrated — schema changes are low risk

---

### 12.1 `recommendations_userinteractionlog`

High-throughput append-only event log. Records every meaningful
user interaction with the product catalog. Feeds ML pipelines
for collaborative filtering and recommendation model training.
Supports both authenticated users and anonymous guest sessions.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NULL`, `FK`, `INDEX` | `NULL` | `CASCADE` on delete. `NULL` = anonymous guest session |
| `session_key` | `CharField(40)` | `VARCHAR(40)` | `NULL`, `INDEX` | `NULL` | Django session key for anonymous guest tracking |
| `event_type` | `CharField(20)` | `VARCHAR(20)` | `NOT NULL`, `INDEX` | — | See Event Type choices below |
| `product_id` | `CharField(100)` | `VARCHAR(100)` | `NULL`, `INDEX` | `NULL` | Soft reference to `products_product`. See ISSUE-REC01 |
| `search_query` | `CharField(255)` | `VARCHAR(255)` | `NULL` | `NULL` | Raw search string. Populated for `SEARCH_QUERY` events only |
| `metadata` | `JSONField` | `JSONB` | `NULL` | `NULL` | Arbitrary event context e.g. `{"time_spent_seconds": 45, "device": "mobile"}` |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel`. Event timestamp |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `rec_interactionlog_user_idx` | `user_id` | `BTREE` |
| `rec_interactionlog_session_idx` | `session_key` | `BTREE` |
| `rec_interactionlog_event_idx` | `event_type` | `BTREE` |
| `rec_interactionlog_product_event_idx` | `product_id`, `event_type` | `BTREE` |
| `rec_interactionlog_user_event_created_idx` | `user_id`, `event_type`, `created_at` DESC | `BTREE` |

**Event Type Choices:**

| Display | DB Value | `product_id` Required | `search_query` Required |
|---|---|---|---|
| Viewed Product Page | `VIEW_PRODUCT` | ✅ Yes | — |
| Added to Cart | `ADD_TO_CART` | ✅ Yes | — |
| Removed from Cart | `REMOVE_FROM_CART` | ✅ Yes | — |
| Added to Wishlist | `ADD_TO_WISHLIST` | ✅ Yes | — |
| Purchased Product | `PURCHASED` | ✅ Yes | — |
| Executed Search | `SEARCH_QUERY` | — | ✅ Yes |

**Append-Only Design Note:**

```
Rows are INSERT only — never updated after creation.
updated_at from TimeStampedModel is present but should never change.
ML pipelines consume via created_at range partitioning.
Celery purge task recommended: delete rows older than 365 days
to prevent unbounded table growth at high event volume.
```

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `recommendations_userinteractionlog` → `accounts_user` | Many-to-One | `CASCADE` |
| `recommendations_userinteractionlog` → `products_product` | Soft reference via `product_id` string | See ISSUE-REC01 |

---

### 12.2 `recommendations_personalizedrecommendation`

Pre-computed ML recommendation records per user. Generated by
offline model training jobs and stored for rapid frontend
querying. Tracks click-through on each recommendation to
feed back into model evaluation. One record per
user-product-model_version triplet enforced at DB level.

| Column | Django Field | DB Type | Constraints | Default | Notes |
|---|---|---|---|---|---|
| `id` | `AutoField` (PK) | `BIGINT` | `PK`, `NOT NULL`, `AUTO INCREMENT` | Auto | — |
| `user_id` | `ForeignKey → User` | `BIGINT` | `NOT NULL`, `FK`, `INDEX` | — | `CASCADE` on delete |
| `recommended_product_id` | `CharField(100)` | `VARCHAR(100)` | `NOT NULL`, `INDEX` | — | Soft reference to `products_product`. See ISSUE-REC01 |
| `score` | `FloatField` | `FLOAT8` | `NOT NULL` | — | ML model confidence score. Range `0.0–1.0`. See ISSUE-REC03 |
| `model_version` | `CharField(50)` | `VARCHAR(50)` | `NOT NULL` | — | Model identifier e.g. `collab-filtering-v2.1` |
| `is_clicked` | `BooleanField` | `BOOLEAN` | `NOT NULL` | `FALSE` | `TRUE` when user clicks this recommendation in frontend |
| `created_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now_add` | From `TimeStampedModel`. Recommendation generation timestamp |
| `updated_at` | `DateTimeField` | `TIMESTAMPTZ` | `NOT NULL` | `auto_now` | From `TimeStampedModel` |

**Indexes:**

| Index Name | Column(s) | Type |
|---|---|---|
| `rec_personalised_user_idx` | `user_id` | `BTREE` |
| `rec_personalised_product_idx` | `recommended_product_id` | `BTREE` |
| `rec_personalised_user_product_model_uniq` | `user_id`, `recommended_product_id`, `model_version` | `UNIQUE BTREE` |
| `rec_personalised_score_idx` | `score` DESC | `BTREE` |

**Relationships:**

| Relation | Type | On Delete |
|---|---|---|
| `recommendations_personalizedrecommendation` → `accounts_user` | Many-to-One | `CASCADE` |
| `recommendations_personalizedrecommendation` → `products_product` | Soft reference via `recommended_product_id` string | See ISSUE-REC01 |

---












## 13. Cross-App Relationships

> This section documents every relationship that crosses app boundaries.
> It is the authoritative reference for understanding how the full
> system connects. Read this before writing any query that joins
> across apps or before designing a new feature that touches
> multiple domains.

---

### 13.1 Full Entity Relationship Map

```
accounts_user
│
├── 1:1 ──► accounts_userprofile
│
├── 1:M ──► accounts_emailverificationtoken
├── 1:M ──► accounts_passwordresettoken
│
├── 1:1 ──► cart_cart
│               └── 1:M ──► cart_cartitem
│                               └── M:1 ──► products_product
│
├── 1:M ──► orders_order
│               ├── 1:M ──► orders_orderitem
│               │               └── M:1 ──► products_product
│               ├── 1:M ──► orders_orderstatuslog
│               ├── 1:1 ──► logistics_shipment
│               ├── 1:M ──► payments_paymenttransaction
│               ├── 1:1 ──► notifications_whatsappcodverification
│               ├── M:1 ──► coupons_coupon
│               │               └── 1:M ──► coupons_couponusage
│               └── 1:M ──► reviews_review (via orders_orderitem)
│
├── 1:M ──► reviews_review
│               └── M:1 ──► products_product
│
├── 1:M ──► contact_contactmessage
│
├── 1:M ──► notifications_notification
│
├── 1:M ──► recommendations_userinteractionlog
│               └── M:1 ──► products_product (soft ref → real FK)
│
└── 1:M ──► recommendations_personalizedrecommendation
                └── M:1 ──► products_product (soft ref → real FK)

products_product
│
├── 1:M ──► products_productimage
├── M:M ──► products_bikemodel
│               └── M:1 ──► products_brand
├── M:1 ──► products_category
├── M:1 ──► products_brand
└── M:1 ──► accounts_user (created_by)

logistics_couriersettlement
└── M:M ──► logistics_shipment

analytics_courierperformancemetric
└── (enum ref) ──► CourierPartner (shared from logistics app)

analytics_dailysalessnapshot
└── (aggregated from) ──► orders_order
                          payments_paymenttransaction
                          logistics_shipment
```

---

### 13.2 Cross-App FK Reference Table

Every foreign key that crosses an app boundary — in one place.

| From Table | From Column | To Table | Constraint | On Delete |
|---|---|---|---|---|
| `cart_cart` | `user_id` | `accounts_user` | `FK` | `CASCADE` |
| `cart_cartitem` | `cart_id` | `cart_cart` | `FK` | `CASCADE` |
| `cart_cartitem` | `product_id` | `products_product` | `FK` | `CASCADE` → see ISSUE-C01 |
| `orders_order` | `user_id` | `accounts_user` | `FK` | `PROTECT` |
| `orders_order` | `coupon_id` | `coupons_coupon` | `FK` | `SET NULL` → see ISSUE-CPN05 |
| `orders_orderitem` | `order_id` | `orders_order` | `FK` | `CASCADE` |
| `orders_orderitem` | `product_id` | `products_product` | `FK` | `PROTECT` |
| `orders_orderstatuslog` | `order_id` | `orders_order` | `FK` | `CASCADE` |
| `orders_orderstatuslog` | `changed_by_id` | `accounts_user` | `FK` | `SET NULL` |
| `reviews_review` | `product_id` | `products_product` | `FK` | `CASCADE` |
| `reviews_review` | `user_id` | `accounts_user` | `FK` | `CASCADE` → see ISSUE-R01 |
| `reviews_review` | `order_item_id` | `orders_orderitem` | `FK` | `SET NULL` |
| `payments_paymenttransaction` | `user_id` | `accounts_user` | `FK` | `SET NULL` |
| `payments_paymenttransaction` | `order_id` | `orders_order` | `FK` (pending) | `PROTECT` → see ISSUE-PAY01 |
| `coupons_couponusage` | `coupon_id` | `coupons_coupon` | `FK` | `PROTECT` |
| `coupons_couponusage` | `user_id` | `accounts_user` | `FK` | `CASCADE` |
| `coupons_couponusage` | `order_id` | `orders_order` | `FK` (pending) | `PROTECT` → see ISSUE-CPN03 |
| `contact_contactmessage` | `user_id` | `accounts_user` | `FK` | `SET NULL` |
| `contact_contactmessage` | `resolved_by_id` | `accounts_user` | `FK` | `SET NULL` |
| `notifications_notification` | `user_id` | `accounts_user` | `FK` | `CASCADE` |
| `notifications_whatsappcodverification` | `order_id` | `orders_order` | `FK` (pending) | `PROTECT` → see ISSUE-NOTIF03 |
| `logistics_shipment` | `order_id` | `orders_order` | `FK` (pending) | `PROTECT` → see ISSUE-LOG01 |
| `logistics_couriersettlement` | `shipments_included` | `logistics_shipment` | `M2M` | — |
| `recommendations_userinteractionlog` | `user_id` | `accounts_user` | `FK` | `CASCADE` → see ISSUE-REC02 |
| `recommendations_userinteractionlog` | `product_id` | `products_product` | `FK` (pending) | `SET NULL` → see ISSUE-REC01 |
| `recommendations_personalizedrecommendation` | `user_id` | `accounts_user` | `FK` | `CASCADE` |
| `recommendations_personalizedrecommendation` | `recommended_product_id` | `products_product` | `FK` (pending) | `CASCADE` → see ISSUE-REC01 |
| `products_product` | `category_id` | `products_category` | `FK` | `PROTECT` |
| `products_product` | `brand_id` | `products_brand` | `FK` | `SET NULL` |
| `products_product` | `created_by_id` | `accounts_user` | `FK` | `SET NULL` |
| `products_productimage` | `product_id` | `products_product` | `FK` | `CASCADE` |
| `products_bikemodel` | `brand_id` | `products_brand` | `FK` | `CASCADE` |
| `products_product` | `compatible_bikes` | `products_bikemodel` | `M2M` | — |

> **Legend:**
> `FK (pending)` = currently a `CharField` soft reference.
> Must be converted to real FK before first migration of that app.
> See referenced ISSUE for migration path.

---

### 13.3 The `orders_order` Hub — Central Dependency Map

`orders_order` is the most connected table in the system.
Every downstream app depends on it. This map shows the
complete blast radius of any change to `orders_order`.

```
orders_order (hub)
│
├── UPSTREAM dependencies (orders_order depends on these):
│   ├── accounts_user       (user_id FK — PROTECT)
│   ├── coupons_coupon      (coupon_id FK — SET NULL)
│   └── cart_cart           (source data at checkout — no FK after conversion)
│
└── DOWNSTREAM dependents (these depend on orders_order):
    ├── orders_orderitem            (CASCADE — deleted with order)
    ├── orders_orderstatuslog       (CASCADE — deleted with order)
    ├── payments_paymenttransaction (PROTECT — blocks order deletion)
    ├── coupons_couponusage         (PROTECT — blocks order deletion)
    ├── logistics_shipment          (PROTECT — blocks order deletion)
    ├── notifications_whatsappcodverification (PROTECT — blocks order deletion)
    └── reviews_review              (via orderitem — SET NULL)
```

> **Implication:** `orders_order` rows can never be hard deleted
> once any payment, coupon usage, or shipment record exists for them.
> The correct pattern is soft deletion via `status = CANCELLED`
> or `status = REFUNDED`. Hard deletion is permanently blocked
> by PROTECT constraints from multiple downstream apps.

---

### 13.4 The `products_product` Hub — Central Dependency Map

`products_product` is the second most connected table.

```
products_product (hub)
│
├── UPSTREAM dependencies:
│   ├── products_category   (category_id FK — PROTECT)
│   ├── products_brand      (brand_id FK — SET NULL)
│   └── accounts_user       (created_by_id FK — SET NULL)
│
└── DOWNSTREAM dependents:
    ├── products_productimage       (CASCADE — deleted with product)
    ├── products_product_compatible_bikes (M2M junction — CASCADE)
    ├── cart_cartitem               (CASCADE → should be PROTECT — ISSUE-C01)
    ├── orders_orderitem            (PROTECT — blocks product deletion)
    ├── reviews_review              (CASCADE — reviews deleted with product)
    ├── recommendations_userinteractionlog    (SET NULL — logs preserved)
    └── recommendations_personalizedrecommendation (CASCADE — stale recs removed)
```

> **Implication:** `products_product` cannot be hard deleted once
> it has any order history. Use `status = DISCONTINUED` for
> retiring products. Hard deletion blocked by `orders_orderitem`
> PROTECT constraint.

---

### 13.5 Soft-Reference Violations — Complete Project Map

Every `CharField` used as a fake FK across the entire codebase.
All must be converted to real FKs before their app's first
migration run.

| Table | Column | Should Reference | Real FK Type | Issue |
|---|---|---|---|---|
| `coupons_couponusage` | `order_id` | `orders_order` | `ForeignKey` | ISSUE-CPN03 |
| `payments_paymenttransaction` | `order_id` | `orders_order` | `ForeignKey` | ISSUE-PAY01 |
| `notifications_whatsappcodverification` | `order_id` | `orders_order` | `OneToOneField` | ISSUE-NOTIF03 |
| `logistics_shipment` | `order_id` | `orders_order` | `OneToOneField` | ISSUE-LOG01 |
| `recommendations_userinteractionlog` | `product_id` | `products_product` | `ForeignKey` | ISSUE-REC01 |
| `recommendations_personalizedrecommendation` | `recommended_product_id` | `products_product` | `ForeignKey` | ISSUE-REC01 |

> **Action required before running first migrations on any of these apps:**
> Convert all six soft references to real FKs.
> Failure to do this means six tables have no referential integrity
> and will silently accumulate orphaned rows pointing to
> non-existent orders and products.

---

### 13.6 Shared Enum — `CourierPartner` Usage Map

`CourierPartner` is defined in `apps/logistics/models.py` but
consumed across three apps. It must be moved to
`apps/common/choices/courier.py` before first migration.

| App | Model | Field | Current Import |
|---|---|---|---|
| `logistics` | `Shipment` | `courier` | Defined here |
| `logistics` | `CourierSettlement` | `courier` | Defined here |
| `analytics` | `CourierPerformanceMetric` | `courier` | Imported from `logistics` |
| `payments` | `WebhookLog` | `gateway` | Free text — should use this enum |

> See ISSUE-LOG03 and ISSUE-PAY03 for migration paths.

---

### 13.7 Append-Only Tables — Immutability Contract

These tables are designed as immutable audit logs or event streams.
They must never be updated after creation. All currently extend
`TimeStampedModel` incorrectly — each has an open issue.

| Table | Purpose | Issue | Correct Base |
|---|---|---|---|
| `orders_orderstatuslog` | Order state transition audit | *(correctly avoids TimeStampedModel)* | `models.Model` ✅ |
| `payments_webhooklog` | Gateway webhook audit | ISSUE-PAY04 | `models.Model` |
| `recommendations_userinteractionlog` | ML event stream | ISSUE-REC05 | `models.Model` |

> **Pattern rule:** Any model documented as immutable or append-only
> must not extend `TimeStampedModel`. Define only `created_at`
> with `auto_now_add=True`. Add a `save()` guard that raises
> `ValueError` on update attempts.

---

### 13.8 Boolean + Timestamp Paired Fields — Consistency Contract

A recurring pattern across the codebase where a boolean flag
and a timestamp must always be set together. All require a
`clean()` method and a helper method to set both atomically.

| Table | Boolean Field | Paired Timestamp | Issue |
|---|---|---|---|
| `accounts_passwordresettoken` | `is_used` | — *(no timestamp — acceptable)* | — |
| `accounts_emailverificationtoken` | `is_used` *(missing)* | — | ISSUE-A04 |
| `contact_contactmessage` | `is_resolved` | `resolved_at` | ISSUE-CT02 |
| `notifications_notification` | `is_sent` | `sent_at` | ISSUE-NOTIF02 |
| `recommendations_personalizedrecommendation` | `is_clicked` | `clicked_at` *(missing)* | ISSUE-REC04 |
| `logistics_couriersettlement` | `is_reconciled` | — *(no timestamp — gap)* | — |

> **Pattern rule:** Every boolean state flag that represents a
> point-in-time event must have a paired `_at` timestamp field.
> Both must be set atomically via a dedicated helper method.
> `clean()` must validate they are never set independently.

---

### 13.9 Race Condition Hotspots — Concurrency Risk Map

Locations where concurrent requests can produce data corruption
without explicit DB locking. All require `select_for_update()`
inside `transaction.atomic()`.

| Table | Field | Risk | Issue | Required Pattern |
|---|---|---|---|---|
| `products_product` | `stock` | Oversell on concurrent add-to-cart | ISSUE-P04 | `select_for_update()` at checkout |
| `cart_cartitem` | `quantity` | Stock validation race between cart save and order place | ISSUE-C02 | `select_for_update()` at checkout |
| `coupons_coupon` | `total_used` | Over-redemption on concurrent coupon use | ISSUE-CPN02 | `select_for_update()` + `F()` expression |

> **Atomic checkout transaction — the correct sequence:**
> ```
> with transaction.atomic():
>   1. select_for_update() on all products in cart
>   2. select_for_update() on coupon if applied
>   3. Validate stock for each CartItem
>   4. Validate coupon limits
>   5. Create Order
>   6. Create OrderItems — snapshot prices
>   7. Create CouponUsage — increment total_used via F()
>   8. Decrement product.stock via F() for each item
>   9. Clear CartItems
>   10. Create PaymentTransaction (PENDING)
>   11. Create Shipment (LABEL_CREATED)
> → Commit transaction
> 12. Send confirmation notification via Celery (outside transaction)
> 13. Trigger WhatsApp COD verification via Celery (outside transaction)
> ```

---

### 13.10 Financial Snapshot Integrity — Cross-App Invariants

Financial fields that must be consistent across multiple tables.
These invariants have no DB-level enforcement — they depend on
correct application logic.

| Invariant | Tables Involved | Issue |
|---|---|---|
| `Order.total_price == Order.subtotal - Order.discount_amount + Order.shipping_fee` | `orders_order` | ISSUE-O03, ISSUE-CPN05 |
| `OrderItem.subtotal == OrderItem.unit_price × OrderItem.quantity` | `orders_orderitem` | ISSUE-O06 |
| `Order.payment_status` must mirror latest `PaymentTransaction.status` | `orders_order`, `payments_paymenttransaction` | ISSUE-PAY06 |
| `CourierSettlement.net_payout_received == total_cod_collected - total_shipping_deducted` | `logistics_couriersettlement` | ISSUE-LOG02 |
| `DailySalesSnapshot.cod_orders_count + prepaid_orders_count == total_orders` | `analytics_dailysalessnapshot` | ISSUE-ANA01 |
| `Shipment.cod_amount == Order.total_price` for COD orders | `logistics_shipment`, `orders_order` | ISSUE-LOG04 |

---

### 13.11 Pre-Migration Checklist for Unmigrated Apps

Before running `makemigrations` and `migrate` on any unmigrated
app, complete this checklist in order.

**Step 1 — Fix all soft references:**
```
□ coupons_couponusage.order_id     → ForeignKey(Order, PROTECT)
□ payments_paymenttransaction.order_id → ForeignKey(Order, PROTECT)
□ notifications_whatsappcodverification.order_id → OneToOneField(Order, PROTECT)
□ logistics_shipment.order_id      → OneToOneField(Order, PROTECT)
□ recommendations_userinteractionlog.product_id → ForeignKey(Product, SET_NULL)
□ recommendations_personalizedrecommendation.recommended_product_id → ForeignKey(Product, CASCADE)
```

**Step 2 — Move shared enums to common:**
```
□ Move CourierPartner → apps/common/choices/courier.py
□ Update Gateway choices in payments to include courier names
□ Update all imports across logistics, analytics, payments
```

**Step 3 — Fix append-only models:**
```
□ payments_webhooklog    → stop extending TimeStampedModel
□ recommendations_userinteractionlog → stop extending TimeStampedModel
□ Both → add save() guard against updates
```

**Step 4 — Add missing fields before first migration:**
```
□ orders_order.coupon_id FK         (ISSUE-CPN05)
□ orders_order.discount_amount      (ISSUE-CPN05)
□ orders_order.refunded_at          (ISSUE-O05)
□ payments_paymenttransaction.original_transaction FK  (ISSUE-PAY02)
□ payments_paymenttransaction.completed_at  (ISSUE-PAY05)
□ recommendations_personalizedrecommendation.clicked_at (ISSUE-REC04)
□ recommendations_userinteractionlog → remove updated_at (ISSUE-REC05)
□ analytics_courierperformancemetric.month_year → DateField (ISSUE-ANA02)
□ coupons_coupon.save() → uppercase normalisation (ISSUE-CPN01)
```

**Step 5 — Add DB-level constraints before first migration:**
```
□ reviews_review rating CheckConstraint 1–5   (ISSUE-R04)
□ products_productimage partial UniqueConstraint on is_primary (ISSUE-P06)
□ recommendations_personalizedrecommendation score CheckConstraint 0–1 (ISSUE-REC03)
```

**Step 6 — Verify migrated apps before touching:**
```
□ accounts  ✅ migrated — all changes require safe migration path
□ products  ✅ migrated — all changes require safe migration path
□ cart      ✅ migrated — all changes require safe migration path
```