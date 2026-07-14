# signals.py
from __future__ import annotations

import logging

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from apps.core.cache import two_level_cache

# ── Import from constants — NOT from views ─────────────────────────────────
# Why: signals.py loads before views.py during Django startup.
# Importing from views.py here causes circular import.
# constants.py imports nothing from this app — safe from anywhere.
from apps.products.constants import (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
    BRANDS_CACHE_KEY,
    BIKE_MODELS_CACHE_PREFIX,
    PRODUCTS_LIST_CACHE_PREFIX,
    PRODUCT_DETAIL_CACHE_PREFIX,
)
from .models import Product, ProductImage, Category, BikeModel, Brand

logger = logging.getLogger("apps.products")


# ── Category invalidation ──────────────────────────────────────────────────

_CATEGORY_CACHE_KEYS = (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
)


def _invalidate_all_category_caches(instance: Category, reason: str) -> None:
    for key in _CATEGORY_CACHE_KEYS:
        two_level_cache.delete(key)
        logger.info(
            "Category cache invalidated | reason=%s key=%s id=%s name=%s",
            reason, key, instance.pk, instance.name,
        )


@receiver(post_save, sender=Category)
def on_category_saved(sender, instance: Category, created: bool, **kwargs):
    action = "created" if created else "updated"
    _invalidate_all_category_caches(instance, reason=action)


@receiver(post_delete, sender=Category)
def on_category_deleted(sender, instance: Category, **kwargs):
    _invalidate_all_category_caches(instance, reason="deleted")


# ── Brand invalidation ─────────────────────────────────────────────────────

def _invalidate_brand_cache(instance: Brand, reason: str) -> None:
    two_level_cache.delete(BRANDS_CACHE_KEY)
    logger.info(
        "Brand cache invalidated | reason=%s key=%s id=%s name=%s",
        reason, BRANDS_CACHE_KEY, instance.pk, instance.name,
    )


@receiver(post_save, sender=Brand)
def on_brand_saved(sender, instance: Brand, created: bool, **kwargs):
    action = "created" if created else "updated"
    _invalidate_brand_cache(instance, reason=action)


@receiver(post_delete, sender=Brand)
def on_brand_deleted(sender, instance: Brand, **kwargs):
    _invalidate_brand_cache(instance, reason="deleted")


# ── BikeModel invalidation ─────────────────────────────────────────────────

def _invalidate_bike_model_caches(instance: BikeModel, reason: str) -> None:
    two_level_cache.delete(BIKE_MODELS_CACHE_PREFIX)
    logger.info(
        "BikeModel cache invalidated | reason=%s prefix=%s id=%s name=%s brand_id=%s",
        reason, BIKE_MODELS_CACHE_PREFIX,
        instance.pk, instance.name, instance.brand_id,
    )


@receiver(post_save, sender=BikeModel)
def on_bike_model_saved(sender, instance: BikeModel, created: bool, **kwargs):
    action = "created" if created else "updated"
    _invalidate_bike_model_caches(instance, reason=action)


@receiver(post_delete, sender=BikeModel)
def on_bike_model_deleted(sender, instance: BikeModel, **kwargs):
    _invalidate_bike_model_caches(instance, reason="deleted")


# ── Product invalidation ───────────────────────────────────────────────────

def _invalidate_product_list_cache(instance: Product, reason: str) -> None:
    """
    Why delete by prefix:
        List cache has hundreds of variants — filter + sort + page.
        Prefix delete clears ALL variants in one operation.
    """
    two_level_cache.delete(PRODUCTS_LIST_CACHE_PREFIX)
    logger.info(
        "Product list cache invalidated | reason=%s id=%s name=%s",
        reason, instance.pk, instance.name,
    )


def _invalidate_product_detail_cache(slug: str, reason: str) -> None:
    """
    Why accept slug not instance:
        Called from both Product signals (instance.slug)
        and ProductImage signals (instance.product.slug).
        Slug string makes it reusable for both callers.

    Why exact key not prefix:
        Each product has its own detail cache key.
        Only THIS product's cache needs clearing.
        Other products stay warm — no unnecessary DB hits.
    """
    cache_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}"
    two_level_cache.delete(cache_key)
    logger.info(
        "Product detail cache invalidated | reason=%s slug=%s",
        reason, slug,
    )


@receiver(post_save, sender=Product)
def on_product_saved(sender, instance: Product, created: bool, **kwargs) -> None:
    action = "created" if created else "updated"
    _invalidate_product_list_cache(instance, reason=action)
    _invalidate_product_detail_cache(instance.slug, reason=action)


@receiver(post_delete, sender=Product)
def on_product_deleted(sender, instance: Product, **kwargs) -> None:
    _invalidate_product_list_cache(instance, reason="deleted")
    _invalidate_product_detail_cache(instance.slug, reason="deleted")


@receiver(post_save, sender=ProductImage)
def on_product_image_saved(sender, instance: ProductImage, **kwargs) -> None:
    _invalidate_product_list_cache(instance.product, reason="image_saved")
    _invalidate_product_detail_cache(instance.product.slug, reason="image_saved")


@receiver(post_delete, sender=ProductImage)
def on_product_image_deleted(sender, instance: ProductImage, **kwargs) -> None:
    _invalidate_product_list_cache(instance.product, reason="image_deleted")
    _invalidate_product_detail_cache(instance.product.slug, reason="image_deleted")
