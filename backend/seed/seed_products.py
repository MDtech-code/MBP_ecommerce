"""
Seed: Categories, Brands, Bike Models, Products, Specifications, Coupons, Users.
TARGET: test_db first, then default (production).

Users situation:
    - admin@gmail.com → already exists as admin (DO NOT recreate)
    - customer1@gmail.com     → missing, will be created
    - customer2@gmail.com  → missing, will be created

NOTE: Profile + Cart are created by register_user() service, NOT signals.
      seed_users() handles this manually for seeded users.
"""

import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files import File
from django.contrib.auth import get_user_model
from django.utils.text import slugify

from apps.accounts.models import UserProfile
from apps.cart.models import Cart
from apps.products.models import (
    Category, Brand, BikeModel, Product, ProductImage, ProductSpecification
)
from apps.coupons.models import Coupon

from .data import (
    USERS_DATA, CATEGORIES_DATA, BRANDS_DATA,
    BIKE_MODELS_DATA, PRODUCTS_DATA, COUPONS_DATA,
)

User = get_user_model()

# ── CONFIG ────────────────────────────────────────────────────────────────────
TARGET_DB   = "default"              # ← change to "default" for production
ADMIN_EMAIL = "admin@gmail.com"
IMAGES_DIR  = BASE_DIR / "seed" / "images"

IMAGE_MAP = {
    "battery": IMAGES_DIR / "battries.png",
    "brake":   IMAGES_DIR / "brake.png",
    "chain":   IMAGES_DIR / "chain.png",
    "tyre":    IMAGES_DIR / "tyre.png",
    "engine":  IMAGES_DIR / "engine.png",
    "light":   IMAGES_DIR / "light.png",
    "oil":     IMAGES_DIR / "oil.png",
}
# ─────────────────────────────────────────────────────────────────────────────


def attach_image(
    product: Product,
    image_key: str,
    is_primary: bool = True,
    order: int = 0,
):
    img_path = IMAGE_MAP.get(image_key)
    if not img_path or not img_path.exists():
        print(f"  [WARN] Image not found: {img_path}")
        return
    with open(img_path, "rb") as f:
        pi = ProductImage(
            product=product,
            is_primary=is_primary,
            order=order,
        )
        pi.image.save(img_path.name, File(f), save=False)
        pi.save(using=TARGET_DB)
    print(f"  [IMG]  '{img_path.name}' → '{product.name}'")


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

def seed_users():
    print("\n[0/6] Seeding Users …")

    # Fetch existing admin — must already exist
    try:
        admin_user = User.objects.using(TARGET_DB).get(email=ADMIN_EMAIL)
        print(f"  [=]   Admin found: {admin_user.email}")
    except User.DoesNotExist:
        print(f"  [ERR] Admin '{ADMIN_EMAIL}' not found in '{TARGET_DB}'!")
        sys.exit(1)

    user_map = {ADMIN_EMAIL: admin_user}

    for data in USERS_DATA:
        existing = User.objects.using(TARGET_DB).filter(
            email=data["email"]
        ).first()

        if existing:
            print(f"  [=]   User exists: {existing.email}")
            user_map[data["email"]] = existing
            continue

        # Build and save user
        user = User(
            email=        data["email"],
            full_name=    data["full_name"],
            role=         data["role"],
            is_staff=     data["is_staff"],
            is_superuser= data["is_superuser"],
            is_verified=  data["is_verified"],
            is_active=    data["is_active"],
        )
        user.set_password(data["password"])
        user.save(using=TARGET_DB)
        print(f"  [+]   User created: {user.email}")

        # Profile + Cart are created by register_user() service in production.
        # Signals are gone — we create manually here to mirror service behaviour.
        UserProfile.objects.using(TARGET_DB).get_or_create(user=user)
        print(f"        UserProfile created ✅")

        Cart.objects.using(TARGET_DB).get_or_create(user=user)
        print(f"        Cart created ✅")

        user_map[data["email"]] = user

    print(f"  Done. {len(user_map)} users ready.")
    return user_map


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

def seed_categories():
    print("\n[1/6] Seeding Categories …")
    category_map = {}

    # First pass: top-level only
    for name, parent_name in CATEGORIES_DATA:
        if parent_name is None:
            obj, created = Category.objects.using(TARGET_DB).get_or_create(
                name=name,
                defaults={"slug": slugify(name), "is_active": True},
            )
            category_map[name] = obj
            print(f"  {'[+]' if created else '[=]'} {name}")

    # Second pass: sub-categories
    for name, parent_name in CATEGORIES_DATA:
        if parent_name is not None:
            parent = category_map.get(parent_name)
            obj, created = Category.objects.using(TARGET_DB).get_or_create(
                name=name,
                defaults={
                    "slug":      slugify(name),
                    "is_active": True,
                    "parent":    parent,
                },
            )
            category_map[name] = obj
            print(f"  {'[+]' if created else '[=]'} {name} → {parent_name}")

    print(f"  Done. {len(category_map)} categories ready.")
    return category_map


# ─────────────────────────────────────────────────────────────────────────────
# BRANDS
# ─────────────────────────────────────────────────────────────────────────────

def seed_brands():
    print("\n[2/6] Seeding Brands …")
    brand_map = {}
    for name in BRANDS_DATA:
        obj, created = Brand.objects.using(TARGET_DB).get_or_create(
            name=name,
            defaults={"slug": slugify(name), "is_active": True},
        )
        brand_map[name] = obj
        print(f"  {'[+]' if created else '[=]'} {name}")
    print(f"  Done. {len(brand_map)} brands ready.")
    return brand_map


# ─────────────────────────────────────────────────────────────────────────────
# BIKE MODELS
# ─────────────────────────────────────────────────────────────────────────────

def seed_bike_models(brand_map):
    print("\n[3/6] Seeding Bike Models …")
    bike_map = {}
    for brand_name, model_name, year_start, year_end in BIKE_MODELS_DATA:
        brand = brand_map.get(brand_name)
        if not brand:
            print(f"  [SKIP] Brand '{brand_name}' not found.")
            continue

        obj, created = BikeModel.objects.using(TARGET_DB).get_or_create(
            brand=brand,
            name=model_name,
            defaults={
                "slug":       slugify(f"{brand_name}-{model_name}"),
                "year_start": year_start,
                "year_end":   year_end,
                "is_active":  True,
            },
        )
        bike_map[f"{brand_name} {model_name}"] = obj
        print(f"  {'[+]' if created else '[=]'} {obj}")

    print(f"  Done. {len(bike_map)} bike models ready.")
    return bike_map


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────────────────────────────────────

def seed_products(category_map, brand_map, bike_map, admin_user):
    print("\n[4/6] Seeding Products …")
    created_count = 0
    skipped_count = 0
    product_map   = {}   # sku → Product — returned for seed_specifications()

    for data in PRODUCTS_DATA:
        category = category_map.get(data["category"])
        brand    = brand_map.get(data.get("brand"))

        if not category:
            print(f"  [SKIP] Category '{data['category']}' not found.")
            skipped_count += 1
            continue

        existing = Product.objects.using(TARGET_DB).filter(
            sku=data["sku"]
        ).first()

        if existing:
            print(f"  [=]   Exists: {existing.name}")
            product_map[data["sku"]] = existing
            skipped_count += 1
            continue

        # Unique slug — Product.save() auto-generates but we pass explicit
        # to guarantee uniqueness in case of similar names
        base_slug = slugify(data["name"])
        slug      = base_slug
        counter   = 1
        while Product.objects.using(TARGET_DB).filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product = Product(
            name=                data["name"],
            slug=                slug,
            sku=                 data["sku"],
            category=            category,
            brand=               brand,
            description=         data.get("description", ""),
            price=               data["price"],
            discount_price=      data.get("discount_price"),
            stock=               data["stock"],
            status=              data["status"],
            is_featured=         data.get("is_featured", False),
            weight_grams=        data.get("weight_grams"),          # NEW
            low_stock_threshold= data.get("low_stock_threshold", 5), # NEW
            created_by=          admin_user,
        )
        product.save(using=TARGET_DB)

        # Compatible bikes M2M
        for bike_key in data.get("compatible_bikes", []):
            bike = bike_map.get(bike_key)
            if bike:
                product.compatible_bikes.add(bike)
            else:
                print(f"    [WARN] BikeModel '{bike_key}' not found.")

        # Image
        attach_image(product, data.get("image_key", ""))

        print(f"  [+]   {product.name}  (SKU: {product.sku})")
        product_map[data["sku"]] = product
        created_count += 1

    print(f"  Done. {created_count} created, {skipped_count} skipped.")
    return product_map


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SPECIFICATIONS  (NEW)
# ─────────────────────────────────────────────────────────────────────────────

def seed_specifications(product_map):
    """
    Creates ProductSpecification rows for products that declare a
    'specifications' list in their PRODUCTS_DATA entry.

    Expected format in data.py per product:
        "specifications": [
            {"name": "Material",     "value": "Steel",   "unit": "",   "display_order": 0},
            {"name": "Thread Size",  "value": "M20×1.5", "unit": "mm", "display_order": 1},
        ]

    Skips specs that already exist (idempotent via get_or_create on name+product).
    """
    print("\n[5/6] Seeding Product Specifications …")
    created_count = 0
    skipped_count = 0

    for data in PRODUCTS_DATA:
        specs = data.get("specifications", [])
        if not specs:
            continue

        product = product_map.get(data["sku"])
        if not product:
            print(f"  [SKIP] Product SKU '{data['sku']}' not in product_map.")
            continue

        for spec in specs:
            obj, created = ProductSpecification.objects.using(
                TARGET_DB
            ).get_or_create(
                product=product,
                name=spec["name"],
                defaults={
                    "value":         spec["value"],
                    "unit":          spec.get("unit", ""),
                    "display_order": spec.get("display_order", 0),
                },
            )

            if created:
                print(f"  [+]   {product.name} — {obj.name}: {obj.value}")
                created_count += 1
            else:
                skipped_count += 1

    print(f"  Done. {created_count} specs created, {skipped_count} skipped.")


# ─────────────────────────────────────────────────────────────────────────────
# COUPONS  (NEW)
# ─────────────────────────────────────────────────────────────────────────────

def seed_coupons():
    """
    Creates Coupon records from COUPONS_DATA.
    All codes stored uppercase (Coupon.save() enforces this too).
    Idempotent — skips existing codes.
    """
    print("\n[6/6] Seeding Coupons …")
    created_count = 0
    skipped_count = 0

    for data in COUPONS_DATA:
        code = data["code"].strip().upper()

        if Coupon.objects.using(TARGET_DB).filter(code=code).exists():
            print(f"  [=]   Exists: {code}")
            skipped_count += 1
            continue

        coupon = Coupon(
            code=                 code,
            discount_type=        data["discount_type"],
            discount_value=       data["discount_value"],
            min_order_amount=     data.get("min_order_amount", "0.00"),
            max_discount_amount=  data.get("max_discount_amount"),
            usage_limit_total=    data.get("usage_limit_total"),
            usage_limit_per_user= data.get("usage_limit_per_user", 1),
            valid_from=           data["valid_from"],
            valid_until=          data["valid_until"],
            is_active=            data.get("is_active", True),
        )
        # Coupon.save() calls full_clean() — validation happens automatically
        coupon.save(using=TARGET_DB)
        print(f"  [+]   {coupon.code}  ({coupon.get_discount_type_display()})")
        created_count += 1

    print(f"  Done. {created_count} created, {skipped_count} skipped.")


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def run():
    print("=" * 65)
    print(f"  SEED PRODUCTS  →  database: '{TARGET_DB}'")
    print("=" * 65)

    user_map   = seed_users()
    admin_user = user_map.get(ADMIN_EMAIL)

    category_map = seed_categories()
    brand_map    = seed_brands()
    bike_map     = seed_bike_models(brand_map)
    product_map  = seed_products(category_map, brand_map, bike_map, admin_user)

    seed_specifications(product_map)
    seed_coupons()

    print(f"\n  Products seed complete ✓  (db='{TARGET_DB}')")


if __name__ == "__main__":
    run()
