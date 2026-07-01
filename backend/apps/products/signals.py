from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_delete,post_delete
from django.dispatch import receiver

from apps.core.cache import two_level_cache
from .models import Product, ProductImage,Category,BikeModel,Brand





logger = logging.getLogger("apps.products")

from apps.products.views import (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
    BRANDS_CACHE_KEY,
    BIKE_MODELS_CACHE_PREFIX,
)

# ── Category invalidation ──────────────────────────────────────────────────

# Why a tuple:
#   Clean to iterate — adding a new cache key in the future = one line here
_CATEGORY_CACHE_KEYS = (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
)


def _invalidate_all_category_caches(instance: Category, reason: str) -> None:
    """
    Central invalidation — both flat and tree caches must be cleared
    together because any category change affects both representations.

    Why both:
        A name change → flat list stale + tree stale
        A parent change → flat list stale + tree structure broken
        An is_active change → flat list stale + tree missing/extra node
    """
    for key in _CATEGORY_CACHE_KEYS:
        two_level_cache.delete(key)
        logger.info(
            "Category cache invalidated | reason=%s key=%s id=%s name=%s",
            reason,
            key,
            instance.pk,
            instance.name,
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
    """
    Why only one cache key for brands:
        Brands have no filter variations — always one flat list.
        One key to invalidate, always.
    """
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
    """
    Why two keys invalidated:
        BikeModel list has two cache variants:
            1. "all"          → no brand filter
            2. brand-specific → ?brand=<id>

        When a bike model changes, both must be cleared:
            - "all" is stale because it includes this model
            - brand-specific is stale because it includes this model too

        Why use delete(prefix) for "all":
            BIKE_MODELS_CACHE_PREFIX = "products_bike_models_brand"
            delete_pattern("*products_bike_models_brand*") clears ALL
            bike model cache keys in one operation — both "all" and
            every brand-specific key.

            This is intentional: any bike model change is rare enough
            that clearing all bike model cache variants is acceptable.
            Benefit: no need to track which brand keys exist.
    """
    two_level_cache.delete(BIKE_MODELS_CACHE_PREFIX)
    logger.info(
        "BikeModel cache invalidated | reason=%s prefix=%s id=%s name=%s brand_id=%s",
        reason,
        BIKE_MODELS_CACHE_PREFIX,
        instance.pk,
        instance.name,
        instance.brand_id,
    )


@receiver(post_save, sender=BikeModel)
def on_bike_model_saved(sender, instance: BikeModel, created: bool, **kwargs):
    action = "created" if created else "updated"
    _invalidate_bike_model_caches(instance, reason=action)


@receiver(post_delete, sender=BikeModel)
def on_bike_model_deleted(sender, instance: BikeModel, **kwargs):
    _invalidate_bike_model_caches(instance, reason="deleted")

@receiver(post_save, sender=Product)
def invalidate_product_cache_on_save(
    sender: type[Product],
    instance: Product,
    created: bool,
    **kwargs,
) -> None:
    """
    Clear product list/detail caches whenever a product is
    created or updated, so customers always see fresh data.
    """
    action = "created" if created else "updated"
    two_level_cache.delete("products_list")
    two_level_cache.delete(f"product_detail_{instance.slug}")
    logger.info("Product %s: %s — cache invalidated", action, instance.name)


@receiver(pre_delete, sender=Product)
def invalidate_product_cache_on_delete(
    sender: type[Product],
    instance: Product,
    **kwargs,
) -> None:
    """Clear caches before a product is deleted."""
    two_level_cache.delete("products_list")
    two_level_cache.delete(f"product_detail_{instance.slug}")
    logger.info("Product deleted: %s — cache invalidated", instance.name)


@receiver(post_save, sender=ProductImage)
def invalidate_product_cache_on_image_change(
    sender: type[ProductImage],
    instance: ProductImage,
    **kwargs,
) -> None:
    """
    Clear product detail cache when an image is added or updated,
    since product detail response includes image gallery.
    """
    two_level_cache.delete(f"product_detail_{instance.product.slug}")
    logger.debug(
        "Product image changed for: %s — detail cache invalidated",
        instance.product.name,
    )