"""
Seed: Cart items for customer users.
Run AFTER seed_products.py.

Cart is created manually in seed_users() (mirroring register_user() service).
We just add CartItems here.
"""

import os
import sys
import django
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from apps.cart.models import Cart, CartItem
from apps.products.models import Product
from seed.data import CART_DATA   # ← fixed import path (was: from data import)

User = get_user_model()

# ── CONFIG ────────────────────────────────────────────────────────────────────
TARGET_DB = "test_db"    # ← change to "default" for production
# ─────────────────────────────────────────────────────────────────────────────


def run():
    print("=" * 65)
    print(f"  SEED CART  →  database: '{TARGET_DB}'")
    print("=" * 65)

    for email, items in CART_DATA.items():
        print(f"\n  Customer: {email}")

        try:
            user = User.objects.using(TARGET_DB).get(email=email)
        except User.DoesNotExist:
            print(f"  [SKIP] User '{email}' not found.")
            continue

        # Cart was created in seed_users() (service-style, no signals).
        # get_or_create is a safety net in case seed_users() was skipped.
        cart, cart_created = Cart.objects.using(TARGET_DB).get_or_create(
            user=user
        )
        if cart_created:
            print(f"  [NEW]  Cart created (seed_users missed?) for {email}")
        else:
            print(f"  [OK]   Cart found for {email}")

        for sku, quantity in items:
            try:
                product = Product.objects.using(TARGET_DB).get(sku=sku)
            except Product.DoesNotExist:
                print(f"    [SKIP] SKU '{sku}' not found.")
                continue

            # Respect stock limits
            if product.stock == 0:
                print(f"    [SKIP] '{product.name}' — out of stock.")
                continue

            if quantity > product.stock:
                print(
                    f"    [WARN] '{product.name}' — want {quantity}, "
                    f"have {product.stock}. Adjusting."
                )
                quantity = product.stock

            # Update if already in cart, else create
            existing = CartItem.objects.using(TARGET_DB).filter(
                cart=cart, product=product
            ).first()

            if existing:
                existing.quantity = quantity
                try:
                    existing.full_clean()
                    existing.save(using=TARGET_DB)
                    print(f"    [UPD]  qty={quantity} × '{product.name}'")
                except Exception as e:
                    print(f"    [ERR]  '{product.name}': {e}")
            else:
                try:
                    item = CartItem(
                        cart=cart,
                        product=product,
                        quantity=quantity,
                    )
                    item.full_clean()
                    item.save(using=TARGET_DB)
                    print(f"    [ADD]  qty={quantity} × '{product.name}'")
                except Exception as e:
                    print(f"    [ERR]  '{product.name}': {e}")

        item_count = CartItem.objects.using(TARGET_DB).filter(
            cart=cart
        ).count()
        print(f"  Summary: {item_count} line item(s) in cart.")

    print(f"\n  Cart seed complete ✓  (db='{TARGET_DB}')")


if __name__ == "__main__":
    run()
