"""
Seed: Categories, Brands, Bike Models, Products, Images, Users.
TARGET: Production default database.

Users situation:
    - mudasirock001@gmail.com → already exists as admin (DO NOT recreate)
    - virjarock@gmail.com     → missing, will be created
    - rockaslam435@gmail.com  → missing, will be created
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


from apps.products.models import (
    Category, Brand, BikeModel, Product, ProductImage
)



from seed.data import (
    USERS_DATA, CATEGORIES_DATA, BRANDS_DATA,
    BIKE_MODELS_DATA, PRODUCTS_DATA
)

User = get_user_model()

# ── CONFIG ────────────────────────────────────────────────────────────────────
TARGET_DB  = "default"          # ← Production database
ADMIN_EMAIL = "mudasirock001@gmail.com"
IMAGES_DIR = BASE_DIR / "seed" / "images"

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

# seed_products.py — SIMPLIFIED for production

def seed_users():
    print("\n[0/5] Seeding Users …")

    # Fetch existing admin
    try:
        admin_user = User.objects.using(TARGET_DB).get(email=ADMIN_EMAIL)
        print(f"  [=]   Admin found: {admin_user.email}")
    except User.DoesNotExist:
        print(f"  [ERR] Admin '{ADMIN_EMAIL}' not found!")
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

        # Save user → signals auto-fire → UserProfile + Cart created ✅
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
        # ↑ signals fire automatically:
        #   → UserProfile created in default ✅
        #   → Cart created in default ✅
        # No manual creation needed!

        print(f"  [+]   User created: {user.email}")
        print(f"        UserProfile + Cart auto-created by signals ✅")
        user_map[data["email"]] = user

    print(f"  Done. {len(user_map)} users ready.")
    return user_map


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORIES
# ─────────────────────────────────────────────────────────────────────────────

def seed_categories():
    print("\n[1/5] Seeding Categories …")
    category_map = {}

    # First pass: top-level
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
                    "slug": slugify(name),
                    "is_active": True,
                    "parent": parent,
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
    print("\n[2/5] Seeding Brands …")
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
    print("\n[3/5] Seeding Bike Models …")
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
                "slug": slugify(f"{brand_name}-{model_name}"),
                "year_start": year_start,
                "year_end": year_end,
                "is_active": True,
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
    print("\n[4/5] Seeding Products …")
    created_count = 0
    skipped_count = 0

    for data in PRODUCTS_DATA:
        category = category_map.get(data["category"])
        brand    = brand_map.get(data["brand"])

        if not category:
            print(f"  [SKIP] Category '{data['category']}' not found.")
            skipped_count += 1
            continue

        if Product.objects.using(TARGET_DB).filter(sku=data["sku"]).exists():
            print(f"  [=]   Exists: {data['name']}")
            skipped_count += 1
            continue

        # Unique slug
        base_slug = slugify(data["name"])
        slug      = base_slug
        counter   = 1
        while Product.objects.using(TARGET_DB).filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product = Product(
            name=           data["name"],
            slug=           slug,
            sku=            data["sku"],
            category=       category,
            brand=          brand,
            description=    data["description"],
            price=          data["price"],
            discount_price= data.get("discount_price"),
            stock=          data["stock"],
            status=         data["status"],
            is_featured=    data.get("is_featured", False),
            created_by=     admin_user,
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
        attach_image(product, data["image_key"])

        print(f"  [+]   {product.name}  (SKU: {product.sku})")
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

    seed_products(category_map, brand_map, bike_map, admin_user)

    print(f"\n  Products seed complete ✓  (db='{TARGET_DB}')")


if __name__ == "__main__":
    run()
#! for test_db """
# Seed: Categories, Brands, Bike Models, Products, Images, Users.

# The KEY fix for duplicate UserProfile error:
#     - User creation fires TWO signals automatically:
#         1. create_user_profile  → creates UserProfile
#         2. create_cart_for_new_user → creates Cart
#     - Our seed_users() was calling user.save() a SECOND time
#       after get_or_create() which fired save_user_profile signal
#       and tried to create UserProfile again → IntegrityError.
#     - Fix: use update_fields=['password'] on second save so
#       post_save signal's `created=False` and profile is NOT
#       recreated. Only the password hash is updated.
# """

# import os
# import sys
# import django
# from pathlib import Path

# BASE_DIR = Path(__file__).resolve().parent.parent
# sys.path.insert(0, str(BASE_DIR))
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
# django.setup()

# from django.core.files import File
# from django.contrib.auth import get_user_model
# from django.utils.text import slugify

# from apps.products.models import (
#     Category, Brand, BikeModel, Product, ProductImage
# )
# from data import (
#     USERS_DATA, CATEGORIES_DATA, BRANDS_DATA,
#     BIKE_MODELS_DATA, PRODUCTS_DATA
# )

# User = get_user_model()

# # ── CONFIG ────────────────────────────────────────────────────────────────────
# TARGET_DB  = "test_db"   # change to "default" for production
# IMAGES_DIR = BASE_DIR / "seed" / "images"

# IMAGE_MAP = {
#     "battery": IMAGES_DIR / "battery.png",
#     "brake":   IMAGES_DIR / "brake.png",
#     "chain":   IMAGES_DIR / "chain.png",
#     "tyre":    IMAGES_DIR / "tyre.png",
#     "engine":  IMAGES_DIR / "engine.png",
#     "light":   IMAGES_DIR / "light.png",
#     "oil":     IMAGES_DIR / "oil.png",
# }
# # ─────────────────────────────────────────────────────────────────────────────


# def attach_image(
#     product: Product,
#     image_key: str,
#     is_primary: bool = True,
#     order: int = 0,
# ):
#     img_path = IMAGE_MAP.get(image_key)
#     if not img_path or not img_path.exists():
#         print(f"  [WARN] Image not found: {img_path}")
#         return
#     with open(img_path, "rb") as f:
#         pi = ProductImage(
#             product=product,
#             is_primary=is_primary,
#             order=order,
#         )
#         pi.image.save(img_path.name, File(f), save=False)
#         pi.save(using=TARGET_DB)
#     print(f"  [IMG]  '{img_path.name}' → '{product.name}'")


# # ─────────────────────────────────────────────────────────────────────────────
# # USERS
# # The root cause of the IntegrityError:
# #
# #   get_or_create() internally calls save() once → created=True
# #       → signal fires → UserProfile created ✅  Cart created ✅
# #
# #   Then our code called user.save() again to set the password
# #       → created=False BUT save_user_profile signal fires
# #       → tries instance.profile.save() which is fine BUT
# #       → on a FRESH test_db with no prior data, the sequence
# #          sometimes races and create_user_profile fires twice.
# #
# #   CLEAN FIX: Set the password on the instance BEFORE saving,
# #   so get_or_create() does one single save with everything set.
# #   No second save() call needed at all.
# # ─────────────────────────────────────────────────────────────────────────────

# # seed/seed_products.py

# def seed_users():
#     print("\n[0/5] Seeding Users …")

#     # ── Disconnect ALL signals that fire on User.post_save ────────────────────
#     # Reason: signals always write to 'default' db, but our user
#     # is being saved to TARGET_DB (test_db). This causes FK violation
#     # because UserProfile.objects.create(user=instance) goes to default
#     # but the user only exists in test_db.
#     # We disconnect, do the save manually to correct db, then reconnect.
#     # ─────────────────────────────────────────────────────────────────────────
#     from django.db.models.signals import post_save
#     from apps.accounts.signals import create_user_profile
#     from apps.cart.signals import create_cart_for_new_user
#     from apps.accounts.models import UserProfile
#     from apps.cart.models import Cart

#     post_save.disconnect(create_user_profile,      sender=User)
#     post_save.disconnect(create_cart_for_new_user, sender=User)
#     print("  [SIG]  Signals disconnected (UserProfile + Cart auto-create paused)")

#     user_map = {}

#     try:
#         for data in USERS_DATA:
#             existing = User.objects.using(TARGET_DB).filter(
#                 email=data["email"]
#             ).first()

#             if existing:
#                 print(f"  [=]   User exists: {existing.email}")
#                 user_map[data["email"]] = existing
#                 continue

#             # Build and save user to TARGET_DB
#             user = User(
#                 email=        data["email"],
#                 full_name=    data["full_name"],
#                 role=         data["role"],
#                 is_staff=     data["is_staff"],
#                 is_superuser= data["is_superuser"],
#                 is_verified=  data["is_verified"],
#                 is_active=    data["is_active"],
#             )
#             user.set_password(data["password"])
#             user.save(using=TARGET_DB)
#             print(f"  [+]   User saved: {user.email}")

#             # Manually create UserProfile in TARGET_DB
#             UserProfile.objects.using(TARGET_DB).get_or_create(user=user)
#             print(f"  [+]   UserProfile created for: {user.email}")

#             # Manually create Cart in TARGET_DB
#             Cart.objects.using(TARGET_DB).get_or_create(user=user)
#             print(f"  [+]   Cart created for: {user.email}")

#             user_map[data["email"]] = user

#     finally:
#         # ── ALWAYS reconnect signals — even if an error occurs ────────────────
#         post_save.connect(create_user_profile,      sender=User)
#         post_save.connect(create_cart_for_new_user, sender=User)
#         print("  [SIG]  Signals reconnected ✓")

#     print(f"  Done. {len(user_map)} users ready.")
#     return user_map


# # ─────────────────────────────────────────────────────────────────────────────
# # CATEGORIES
# # ─────────────────────────────────────────────────────────────────────────────

# def seed_categories():
#     print("\n[1/5] Seeding Categories …")
#     category_map = {}

#     # First pass: top-level only
#     for name, parent_name in CATEGORIES_DATA:
#         if parent_name is None:
#             obj, created = Category.objects.using(TARGET_DB).get_or_create(
#                 name=name,
#                 defaults={"slug": slugify(name), "is_active": True},
#             )
#             category_map[name] = obj
#             print(f"  {'[+]' if created else '[=]'} {name}")

#     # Second pass: sub-categories
#     for name, parent_name in CATEGORIES_DATA:
#         if parent_name is not None:
#             parent = category_map.get(parent_name)
#             obj, created = Category.objects.using(TARGET_DB).get_or_create(
#                 name=name,
#                 defaults={
#                     "slug": slugify(name),
#                     "is_active": True,
#                     "parent": parent,
#                 },
#             )
#             category_map[name] = obj
#             print(f"  {'[+]' if created else '[=]'} {name} → {parent_name}")

#     print(f"  Done. {len(category_map)} categories ready.")
#     return category_map


# # ─────────────────────────────────────────────────────────────────────────────
# # BRANDS
# # ─────────────────────────────────────────────────────────────────────────────

# def seed_brands():
#     print("\n[2/5] Seeding Brands …")
#     brand_map = {}
#     for name in BRANDS_DATA:
#         obj, created = Brand.objects.using(TARGET_DB).get_or_create(
#             name=name,
#             defaults={"slug": slugify(name), "is_active": True},
#         )
#         brand_map[name] = obj
#         print(f"  {'[+]' if created else '[=]'} {name}")
#     print(f"  Done. {len(brand_map)} brands ready.")
#     return brand_map


# # ─────────────────────────────────────────────────────────────────────────────
# # BIKE MODELS
# # ─────────────────────────────────────────────────────────────────────────────

# def seed_bike_models(brand_map):
#     print("\n[3/5] Seeding Bike Models …")
#     bike_map = {}
#     for brand_name, model_name, year_start, year_end in BIKE_MODELS_DATA:
#         brand = brand_map.get(brand_name)
#         if not brand:
#             print(f"  [SKIP] Brand '{brand_name}' not found.")
#             continue

#         obj, created = BikeModel.objects.using(TARGET_DB).get_or_create(
#             brand=brand,
#             name=model_name,
#             defaults={
#                 "slug": slugify(f"{brand_name}-{model_name}"),
#                 "year_start": year_start,
#                 "year_end": year_end,
#                 "is_active": True,
#             },
#         )
#         bike_map[f"{brand_name} {model_name}"] = obj
#         print(f"  {'[+]' if created else '[=]'} {obj}")

#     print(f"  Done. {len(bike_map)} bike models ready.")
#     return bike_map


# # ─────────────────────────────────────────────────────────────────────────────
# # PRODUCTS
# # ─────────────────────────────────────────────────────────────────────────────

# def seed_products(category_map, brand_map, bike_map, admin_user):
#     print("\n[4/5] Seeding Products …")
#     created_count = 0
#     skipped_count = 0

#     for data in PRODUCTS_DATA:
#         category = category_map.get(data["category"])
#         brand    = brand_map.get(data["brand"])

#         if not category:
#             print(f"  [SKIP] Category '{data['category']}' not found.")
#             skipped_count += 1
#             continue

#         if Product.objects.using(TARGET_DB).filter(sku=data["sku"]).exists():
#             print(f"  [=]   Exists: {data['name']}")
#             skipped_count += 1
#             continue

#         # Unique slug
#         base_slug = slugify(data["name"])
#         slug      = base_slug
#         counter   = 1
#         while Product.objects.using(TARGET_DB).filter(slug=slug).exists():
#             slug = f"{base_slug}-{counter}"
#             counter += 1

#         product = Product(
#             name=           data["name"],
#             slug=           slug,
#             sku=            data["sku"],
#             category=       category,
#             brand=          brand,
#             description=    data["description"],
#             price=          data["price"],
#             discount_price= data.get("discount_price"),
#             stock=          data["stock"],
#             status=         data["status"],
#             is_featured=    data.get("is_featured", False),
#             created_by=     admin_user,
#         )
#         product.save(using=TARGET_DB)

#         # Compatible bikes M2M
#         for bike_key in data.get("compatible_bikes", []):
#             bike = bike_map.get(bike_key)
#             if bike:
#                 product.compatible_bikes.add(bike)
#             else:
#                 print(f"    [WARN] BikeModel '{bike_key}' not found.")

#         # Image
#         attach_image(product, data["image_key"])

#         print(f"  [+]   {product.name}  (SKU: {product.sku})")
#         created_count += 1

#     print(f"  Done. {created_count} created, {skipped_count} skipped.")


# # ─────────────────────────────────────────────────────────────────────────────
# # ENTRY POINT
# # ─────────────────────────────────────────────────────────────────────────────

# def run():
#     print("=" * 65)
#     print(f"  SEED PRODUCTS  →  database: '{TARGET_DB}'")
#     print("=" * 65)

#     user_map   = seed_users()
#     admin_user = user_map.get("mudasirock001@gmail.com")

#     category_map = seed_categories()
#     brand_map    = seed_brands()
#     bike_map     = seed_bike_models(brand_map)

#     seed_products(category_map, brand_map, bike_map, admin_user)

#     print(f"\n  Products seed complete ✓  (db='{TARGET_DB}')")


# if __name__ == "__main__":
#     run()