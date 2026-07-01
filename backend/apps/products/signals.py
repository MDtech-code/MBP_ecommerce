from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_delete,post_delete
from django.dispatch import receiver

from apps.core.cache import two_level_cache
from .models import Product, ProductImage,Category




logger = logging.getLogger("apps.products")

from apps.products.views import (
    CATEGORIES_FLAT_CACHE_KEY,
    CATEGORIES_TREE_CACHE_KEY,
)



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