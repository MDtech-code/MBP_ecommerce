from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_delete,post_delete
from django.dispatch import receiver

from apps.core.cache import two_level_cache
from .models import Product, ProductImage,Category





from apps.products.views import CATEGORIES_CACHE_KEY

logger = logging.getLogger("apps.products")


@receiver(post_save, sender=Category)
def on_category_saved(sender, instance: Category, created: bool, **kwargs):
    """
    Fires after every INSERT or UPDATE on Category.

    Why post_save and not pre_save:
        pre_save fires before DB write — cache invalidated but DB not yet updated.
        Next request would re-cache the OLD data from DB.
        post_save fires after DB write — cache invalidated after truth is updated.

    Why we invalidate on every save (not just is_active changes):
        Name change    → cached name is stale
        Parent change  → cached hierarchy is stale
        Slug change    → cached slug is stale
        is_active=False→ deactivated category must disappear from list
    """
    action = "created" if created else "updated"
    logger.info(
        "Category %s — invalidating cache | id=%s name=%s",
        action,
        instance.pk,
        instance.name,
    )
    two_level_cache.delete(CATEGORIES_CACHE_KEY)


@receiver(post_delete, sender=Category)
def on_category_deleted(sender, instance: Category, **kwargs):
    """
    Fires after DELETE on Category.

    Why CASCADE matters here:
        Category.parent uses on_delete=CASCADE.
        Deleting a parent deletes all children — each child fires its own
        post_delete signal, so each deletion individually invalidates cache.
        This is correct but results in N invalidations for N children.
        Acceptable cost — deletions are rare admin actions.
    """
    logger.info(
        "Category deleted — invalidating cache | id=%s name=%s",
        instance.pk,
        instance.name,
    )
    two_level_cache.delete(CATEGORIES_CACHE_KEY)





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