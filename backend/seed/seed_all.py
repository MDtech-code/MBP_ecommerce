"""
Master seed runner.

Step 1 (test):   TARGET_DB = "test_db"  in seed_products.py + seed_cart.py
Step 2 (prod):   TARGET_DB = "default"  in seed_products.py + seed_cart.py
                 Also remove seed_users() call — real users already exist.
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

    print("\n>>> PHASE 1: Products, Categories, Brands, Bike Models, Users")
    run_products()

    print("\n>>> PHASE 2: Cart Items")
    run_cart()

    print("\n" + "=" * 65)
    print("  ALL SEEDS COMPLETED SUCCESSFULLY ✓")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()