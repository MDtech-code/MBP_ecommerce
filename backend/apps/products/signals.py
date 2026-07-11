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
# from __future__ import annotations

# import logging

# from django.db.models.signals import post_save, pre_delete,post_delete
# from django.dispatch import receiver

# from apps.core.cache import two_level_cache
# from .models import Product, ProductImage,Category,BikeModel,Brand





# logger = logging.getLogger("apps.products")

# from apps.products.views import (
#     CATEGORIES_FLAT_CACHE_KEY,
#     CATEGORIES_TREE_CACHE_KEY,
#     BRANDS_CACHE_KEY,
#     BIKE_MODELS_CACHE_PREFIX,
#     PRODUCTS_LIST_CACHE_PREFIX,
#     PRODUCT_DETAIL_CACHE_PREFIX,    
# )

# # ── Category invalidation ──────────────────────────────────────────────────

# # Why a tuple:
# #   Clean to iterate — adding a new cache key in the future = one line here
# _CATEGORY_CACHE_KEYS = (
#     CATEGORIES_FLAT_CACHE_KEY,
#     CATEGORIES_TREE_CACHE_KEY,
# )


# def _invalidate_all_category_caches(instance: Category, reason: str) -> None:
#     """
#     Central invalidation — both flat and tree caches must be cleared
#     together because any category change affects both representations.

#     Why both:
#         A name change → flat list stale + tree stale
#         A parent change → flat list stale + tree structure broken
#         An is_active change → flat list stale + tree missing/extra node
#     """
#     for key in _CATEGORY_CACHE_KEYS:
#         two_level_cache.delete(key)
#         logger.info(
#             "Category cache invalidated | reason=%s key=%s id=%s name=%s",
#             reason,
#             key,
#             instance.pk,
#             instance.name,
#         )


# @receiver(post_save, sender=Category)
# def on_category_saved(sender, instance: Category, created: bool, **kwargs):
#     action = "created" if created else "updated"
#     _invalidate_all_category_caches(instance, reason=action)


# @receiver(post_delete, sender=Category)
# def on_category_deleted(sender, instance: Category, **kwargs):
#     _invalidate_all_category_caches(instance, reason="deleted")




# # ── Brand invalidation ─────────────────────────────────────────────────────

# def _invalidate_brand_cache(instance: Brand, reason: str) -> None:
#     """
#     Why only one cache key for brands:
#         Brands have no filter variations — always one flat list.
#         One key to invalidate, always.
#     """
#     two_level_cache.delete(BRANDS_CACHE_KEY)
#     logger.info(
#         "Brand cache invalidated | reason=%s key=%s id=%s name=%s",
#         reason, BRANDS_CACHE_KEY, instance.pk, instance.name,
#     )


# @receiver(post_save, sender=Brand)
# def on_brand_saved(sender, instance: Brand, created: bool, **kwargs):
#     action = "created" if created else "updated"
#     _invalidate_brand_cache(instance, reason=action)


# @receiver(post_delete, sender=Brand)
# def on_brand_deleted(sender, instance: Brand, **kwargs):
#     _invalidate_brand_cache(instance, reason="deleted")


# # ── BikeModel invalidation ─────────────────────────────────────────────────

# def _invalidate_bike_model_caches(instance: BikeModel, reason: str) -> None:
#     """
#     Why two keys invalidated:
#         BikeModel list has two cache variants:
#             1. "all"          → no brand filter
#             2. brand-specific → ?brand=<id>

#         When a bike model changes, both must be cleared:
#             - "all" is stale because it includes this model
#             - brand-specific is stale because it includes this model too

#         Why use delete(prefix) for "all":
#             BIKE_MODELS_CACHE_PREFIX = "products_bike_models_brand"
#             delete_pattern("*products_bike_models_brand*") clears ALL
#             bike model cache keys in one operation — both "all" and
#             every brand-specific key.

#             This is intentional: any bike model change is rare enough
#             that clearing all bike model cache variants is acceptable.
#             Benefit: no need to track which brand keys exist.
#     """
#     two_level_cache.delete(BIKE_MODELS_CACHE_PREFIX)
#     logger.info(
#         "BikeModel cache invalidated | reason=%s prefix=%s id=%s name=%s brand_id=%s",
#         reason,
#         BIKE_MODELS_CACHE_PREFIX,
#         instance.pk,
#         instance.name,
#         instance.brand_id,
#     )


# @receiver(post_save, sender=BikeModel)
# def on_bike_model_saved(sender, instance: BikeModel, created: bool, **kwargs):
#     action = "created" if created else "updated"
#     _invalidate_bike_model_caches(instance, reason=action)


# @receiver(post_delete, sender=BikeModel)
# def on_bike_model_deleted(sender, instance: BikeModel, **kwargs):
#     _invalidate_bike_model_caches(instance, reason="deleted")






# # ── Product cache invalidation ─────────────────────────────────────────────

# # ── Product signals ────────────────────────────────────────────────────────────

# def _invalidate_product_list_cache(instance: Product, reason: str) -> None:
#     """
#     Why delete by prefix:
#         List cache has hundreds of variants based on filter+sort+page.
#         Prefix delete clears ALL variants in one operation.
#     """
#     two_level_cache.delete(PRODUCTS_LIST_CACHE_PREFIX)
#     logger.info(
#         "Product list cache invalidated | reason=%s id=%s name=%s",
#         reason, instance.pk, instance.name,
#     )


# def _invalidate_product_detail_cache(slug: str, reason: str) -> None:
#     """
#     Why accept slug not instance:
#         Called from both Product signals (instance.slug)
#         and ProductImage signals (instance.product.slug).
#         Accepting slug string makes it reusable for both callers.

#     Why exact key not prefix:
#         Each product has its own detail cache key.
#         product_detail_honda-cd70-brake-shoe-set
#         We only need to clear THIS product's cache.
#         Other products' caches stay warm — no unnecessary DB hits.
#     """
#     cache_key = f"{PRODUCT_DETAIL_CACHE_PREFIX}_{slug}"
#     two_level_cache.delete(cache_key)
#     logger.info(
#         "Product detail cache invalidated | reason=%s slug=%s",
#         reason, slug,
#     )


# @receiver(post_save, sender=Product)
# def on_product_saved(
#     sender,
#     instance: Product,
#     created: bool,
#     **kwargs,
# ) -> None:
#     """
#     Why invalidate both list AND detail:
#         List cache: shows name, price, discount, primary_image — all can change.
#         Detail cache: full product data — always stale after any field change.

#     Why post_save not pre_save:
#         Invalidate AFTER DB write — next request caches fresh data.
#         pre_save would clear cache before DB is updated.
#     """
#     action = "created" if created else "updated"
#     _invalidate_product_list_cache(instance, reason=action)
#     _invalidate_product_detail_cache(instance.slug, reason=action)


# @receiver(post_delete, sender=Product)
# def on_product_deleted(
#     sender,
#     instance: Product,
#     **kwargs,
# ) -> None:
#     """
#     Why post_delete not pre_delete:
#         post_delete fires only after successful DB deletion.
#         pre_delete fires before — if deletion fails, cache was cleared for nothing
#         and next request re-caches the product that still exists.
#     """
#     _invalidate_product_list_cache(instance, reason="deleted")
#     _invalidate_product_detail_cache(instance.slug, reason="deleted")


# @receiver(post_save, sender=ProductImage)
# def on_product_image_saved(
#     sender,
#     instance: ProductImage,
#     **kwargs,
# ) -> None:
#     """
#     Why invalidate list cache:
#         primary_image is in the list serializer response.
#         New primary image uploaded → all cached list pages show old image URL.

#     Why invalidate detail cache:
#         Detail response includes full image gallery.
#         Any image add / update / reorder → gallery is stale.
#     """
#     _invalidate_product_list_cache(instance.product, reason="image_saved")
#     _invalidate_product_detail_cache(instance.product.slug, reason="image_saved")


# @receiver(post_delete, sender=ProductImage)
# def on_product_image_deleted(
#     sender,
#     instance: ProductImage,
#     **kwargs,
# ) -> None:
#     """
#     Why both caches:
#         Deleted image may have been the primary → list card shows broken URL.
#         Detail gallery must not show deleted image.
#     """
#     _invalidate_product_list_cache(instance.product, reason="image_deleted")
#     _invalidate_product_detail_cache(instance.product.slug, reason="image_deleted")