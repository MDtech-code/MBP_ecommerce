# apps/products/constants.py
from __future__ import annotations

"""
Product app cache key constants.

Defined here — not in views.py — so both views.py and signals.py
can import from one place without any circular dependency.

Why a separate file:
    signals.py needs these keys to know what to invalidate.
    views.py needs these keys to know what to read/write.
    If constants live in views.py → signals.py imports views.py
    → views.py imports models.py → models.py triggers signals.py
    → circular import. Django may raise ImportError or silently
    load a partial module — both are production bugs.

    constants.py imports nothing from this app — it is the
    bottom of the dependency graph. Safe to import from anywhere.
"""

# ─── Category cache keys ───────────────────────────────────────────────────
CATEGORIES_FLAT_CACHE_KEY = "products_categories_flat"
CATEGORIES_TREE_CACHE_KEY = "products_categories_tree"

CATEGORIES_L1_TTL = 86400        # 1 day
CATEGORIES_L2_TTL = 86400 * 7   # 1 week

# ─── Brand cache keys ──────────────────────────────────────────────────────
BRANDS_CACHE_KEY = "products_brands_list"

BRANDS_L1_TTL = 86400        # 1 day
BRANDS_L2_TTL = 86400 * 7   # 1 week

# ─── Bike model cache keys ─────────────────────────────────────────────────
# Why "all" suffix strategy:
#   brand=None  → products_bike_models_brand_all
#   brand=1     → products_bike_models_brand_1
#   Prefix delete clears ALL variants in one operation.
BIKE_MODELS_CACHE_PREFIX = "products_bike_models_brand"

BIKE_MODELS_L1_TTL = 120   # 2 minutes
BIKE_MODELS_L2_TTL = 600   # 10 minutes

# ─── Product list cache keys ───────────────────────────────────────────────
# Why prefix not exact key:
#   List has hundreds of variants — filter + sort + page combinations.
#   Prefix delete clears ALL variants in one operation.
PRODUCTS_LIST_CACHE_PREFIX = "products_list"

PRODUCTS_LIST_L1_TTL = 60    # 1 minute
PRODUCTS_LIST_L2_TTL = 180   # 3 minutes

# ─── Product detail cache keys ─────────────────────────────────────────────
# Why prefix not full key:
#   Full key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}"
#   Built at runtime in views.py and signals.py using slug.
PRODUCT_DETAIL_CACHE_PREFIX = "product_detail"

PRODUCT_DETAIL_L1_TTL = 60    # 1 minute
PRODUCT_DETAIL_L2_TTL = 300   # 5 minutes

# ─── Sorting config ────────────────────────────────────────────────────────
SORT_OPTIONS: dict[str, str] = {
    "featured":   "-is_featured",
    "newest":     "-created_at",
    "price_asc":  "price",
    "price_desc": "-price",
    "name_asc":   "name",
}
DEFAULT_SORT = "newest"