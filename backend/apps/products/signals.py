from __future__ import annotations

import logging

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from apps.core.cache import two_level_cache
from .models import Product, ProductImage

logger = logging.getLogger("apps.products")


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