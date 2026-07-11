# apps/products/tests/urls.py
"""
Product app URL constants — single source of truth for all test files.

Rules:
    - Every endpoint path defined once here
    - If a URL changes in urls.py, update here — all tests update automatically
    - Detail URLs that need slug are defined as format strings
    - Helper function provided for slug-based URLs to keep test code clean
"""
from __future__ import annotations

# ─── Base ─────────────────────────────────────────────────────────────────────
PRODUCTS_BASE = "/api/products"

# ─── Filter / Lookup endpoints ────────────────────────────────────────────────
CATEGORY_LIST_URL    = f"{PRODUCTS_BASE}/categories/"
BRAND_LIST_URL       = f"{PRODUCTS_BASE}/brands/"
BIKE_MODEL_LIST_URL  = f"{PRODUCTS_BASE}/bike-models/"

# ─── Product endpoints ────────────────────────────────────────────────────────
PRODUCT_LIST_URL = f"{PRODUCTS_BASE}/"

# ─── Slug-based detail URL helper ─────────────────────────────────────────────
def product_detail_url(slug: str) -> str:
    """
    Build the product detail URL for a given slug.

    Usage:
        url = product_detail_url("honda-cd70-brake-shoe")
        response = api_client.get(url)

    Why a function not an f-string constant:
        Slug is dynamic — different per test.
        A function makes the intent explicit and keeps test code readable.
    """
    return f"{PRODUCTS_BASE}/{slug}/"