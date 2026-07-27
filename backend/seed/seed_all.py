"""
Master seed runner.

Step 1 (test):   TARGET_DB = "test_db"  in seed_products.py + seed_cart.py
Step 2 (prod):   TARGET_DB = "default"  in seed_products.py + seed_cart.py

What each phase does:
    PHASE 1 — seed_products.py
        [0/6] Users          → creates User + UserProfile + Cart manually
                                (register_user() service pattern, no signals)
        [1/6] Categories     → top-level then subcategories
        [2/6] Brands
        [3/6] Bike Models
        [4/6] Products       → with weight_grams, low_stock_threshold,
                                compatible_bikes M2M, images
        [5/6] Specifications → ProductSpecification rows per product
        [6/6] Coupons        → 5 Pakistan festival coupons

    PHASE 2 — seed_cart.py
        Cart items for customer users (Cart itself created in Phase 1)
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from seed.seed_products import run as run_products
from seed.seed_cart import run as run_cart


def main():
    print("\n" + "=" * 65)
    print("  PAKISTAN MOTORBIKE PARTS — DATABASE SEEDER")
    print("=" * 65)

    print("\n>>> PHASE 1: Users, Categories, Brands, Bike Models, Products, Specs, Coupons")
    run_products()

    print("\n>>> PHASE 2: Cart Items")
    run_cart()

    print("\n" + "=" * 65)
    print("  ALL SEEDS COMPLETED SUCCESSFULLY ✓")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
