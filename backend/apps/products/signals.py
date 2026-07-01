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
    PRODUCTS_LIST_CACHE_PREFIX
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






# ── Product cache invalidation ─────────────────────────────────────────────

def _invalidate_product_list_cache(instance: Product, reason: str) -> None:
    """
    Why delete by prefix not exact key:
        Product list has hundreds of cache variants:
            products_list_p1_ps12_snewest_cat_br_bk_...
            products_list_p1_ps12_snewest_catengine-parts_br_...
            products_list_p2_ps12_sprice_asc_...
        We cannot know which variants are warm at any time.
        Deleting by prefix clears ALL variants in one operation.

    Why this is safe:
        delete_pattern uses Redis SCAN — non-blocking even at scale.
        L1 clear is cheap — rebuilds on next request.
    """
    two_level_cache.delete(PRODUCTS_LIST_CACHE_PREFIX)
    logger.info(
        "Product list cache invalidated | reason=%s id=%s name=%s",
        reason,
        instance.pk,
        instance.name,
    )


def _invalidate_product_detail_cache(slug: str, reason: str) -> None:
    """
    Why accept slug not instance:
        post_delete: instance still has slug before deletion.
        pre_delete: we use post_delete now — slug still available.
        Accepting slug makes this callable from ProductImage signal too
        where we have instance.product.slug.
    """
    two_level_cache.delete(f"product_detail_{slug}")
    logger.info(
        "Product detail cache invalidated | reason=%s slug=%s",
        reason,
        slug,
    )


@receiver(post_save, sender=Product)
def on_product_saved(
    sender: type[Product],
    instance: Product,
    created: bool,
    **kwargs,
) -> None:
    """
    Why post_save not pre_save:
        We invalidate AFTER DB is updated.
        pre_save would clear cache before DB write —
        next request re-caches the OLD data.

    Why invalidate both list AND detail:
        List cache: shows name, price, discount, image — all can change.
        Detail cache: full product data — always stale after any save.
    """
    action = "created" if created else "updated"
    _invalidate_product_list_cache(instance, reason=action)
    _invalidate_product_detail_cache(instance.slug, reason=action)


@receiver(post_delete, sender=Product)
def on_product_deleted(
    sender: type[Product],
    instance: Product,
    **kwargs,
) -> None:
    """
    Why post_delete not pre_delete:
        pre_delete fires before DB deletion.
        If deletion fails after signal = cache cleared for nothing.
        Next request re-caches stale data thinking product still exists.
        post_delete fires only after successful DB deletion — always correct.
    """
    _invalidate_product_list_cache(instance, reason="deleted")
    _invalidate_product_detail_cache(instance.slug, reason="deleted")


@receiver(post_save, sender=ProductImage)
def on_product_image_saved(
    sender: type[ProductImage],
    instance: ProductImage,
    **kwargs,
) -> None:
    """
    Why invalidate list cache:
        primary_image is in the list serializer.
        If a new primary image is uploaded, every cached list page
        still shows the old image URL until TTL expires.
        Invalidating list cache forces fresh image on next request.

    Why invalidate detail cache:
        Detail response includes full image gallery.
        Any image change (add, update, reorder) must refresh detail.
    """
    _invalidate_product_list_cache(instance.product, reason="image_saved")
    _invalidate_product_detail_cache(instance.product.slug, reason="image_saved")


@receiver(post_delete, sender=ProductImage)
def on_product_image_deleted(
    sender: type[ProductImage],
    instance: ProductImage,
    **kwargs,
) -> None:
    """
    Why this was missing in original:
        Deleting an image = gallery changes.
        Without this, detail cache shows deleted image until TTL expires.
        List cache shows deleted primary image as broken URL.
    """
    _invalidate_product_list_cache(instance.product, reason="image_deleted")
    _invalidate_product_detail_cache(instance.product.slug, reason="image_deleted")