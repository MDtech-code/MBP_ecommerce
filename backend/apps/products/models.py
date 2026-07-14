from __future__ import annotations

import logging
from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.products")


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY
# ─────────────────────────────────────────────────────────────────────────────

class Category(TimeStampedModel):
    """
    Product category with optional self-referencing parent
    for subcategories (e.g. Engine > Pistons > Piston Rings).

    on_delete=PROTECT prevents silent cascade deletion of entire
    category subtrees. Use CategoryService.safe_delete() instead.
    """

    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=120, unique=True, blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcategories",
        verbose_name=_("parent category"),
    )
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        verbose_name        = _("category")
        verbose_name_plural = _("categories")
        ordering            = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_subcategory(self) -> bool:
        return self.parent_id is not None


# ─────────────────────────────────────────────────────────────────────────────
# BRAND
# ─────────────────────────────────────────────────────────────────────────────

class Brand(TimeStampedModel):
    """
    Motorbike part manufacturer or brand (Honda, Yamaha, Suzuki, etc.)
    """

    name = models.CharField(_("name"), max_length=100, unique=True)
    slug = models.SlugField(_("slug"), max_length=120, unique=True, blank=True)
    logo = models.ImageField(_("logo"), upload_to="brands/", null=True, blank=True)
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        verbose_name        = _("brand")
        verbose_name_plural = _("brands")
        ordering            = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


# ─────────────────────────────────────────────────────────────────────────────
# BIKE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class BikeModel(TimeStampedModel):
    """
    Specific motorbike model used for product compatibility matching.
    Core feature: customers filter parts by their exact bike model.
    """

    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="bike_models",
        verbose_name=_("brand"),
    )
    name = models.CharField(
        _("model name"),
        max_length=100,
        help_text=_("e.g. CB150F, YBR125"),
    )
    slug = models.SlugField(_("slug"), max_length=150, unique=True, blank=True)
    year_start = models.PositiveIntegerField(_("production start year"))
    year_end = models.PositiveIntegerField(
        _("production end year"),
        null=True,
        blank=True,
        help_text=_("Leave blank if still in production."),
    )
    is_active = models.BooleanField(_("is active"), default=True)

    class Meta:
        verbose_name        = _("bike model")
        verbose_name_plural = _("bike models")
        ordering            = ["brand__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["brand", "name"],
                name="unique_bike_model_per_brand",
            )
        ]

    def __str__(self) -> str:
        year_range = f"{self.year_start}–{self.year_end or 'present'}"
        return f"{self.brand.name} {self.name} ({year_range})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.name}")
        super().save(*args, **kwargs)

    def clean(self) -> None:
        from django.core.exceptions import ValidationError
        if self.year_end is not None and self.year_end < self.year_start:
            raise ValidationError({
                "year_end": _(
                    "Production end year (%(end)s) cannot be before "
                    "start year (%(start)s)."
                ) % {"end": self.year_end, "start": self.year_start}
            })

    @property
    def display_name(self) -> str:
        return f"{self.brand.name} {self.name}"

    def covers_year(self, year: int) -> bool:
        """
        True if this bike model was in production during the given year.

        Examples:
            BikeModel(year_start=2015, year_end=2020).covers_year(2018) → True
            BikeModel(year_start=2015, year_end=2020).covers_year(2022) → False
            BikeModel(year_start=2015, year_end=None).covers_year(2024)  → True
        """
        if self.year_end is None:
            return year >= self.year_start
        return self.year_start <= year <= self.year_end


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT QUERYSET + MANAGER
# ─────────────────────────────────────────────────────────────────────────────

class ProductQuerySet(models.QuerySet):

    def active(self) -> "ProductQuerySet":
        """Available products with stock > 0."""
        return self.filter(
            status=Product.Status.AVAILABLE,
            stock__gt=0,
        )

    def compatible_with_bike(self, bike_model_id: int) -> "ProductQuerySet":
        """
        Filter products compatible with a specific bike model.
        Single JOIN query — safe to use in listing views.

        Usage:
            Product.objects.compatible_with_bike(bike_id)
                           .active()
                           .select_related('brand', 'category')
        """
        return self.filter(compatible_bikes__id=bike_model_id)

    def low_stock(self) -> "ProductQuerySet":
        """
        Products where stock is at or below their individual threshold.
        Uses F() expression — no Python-level iteration.
        """
        from django.db.models import F
        return self.filter(
            low_stock_threshold__gt=0,
            stock__lte=F("low_stock_threshold"),
        )


class ProductManager(models.Manager):

    def get_queryset(self) -> ProductQuerySet:
        return ProductQuerySet(self.model, using=self._db)

    def active(self) -> ProductQuerySet:
        return self.get_queryset().active()

    def compatible_with_bike(self, bike_model_id: int) -> ProductQuerySet:
        return self.get_queryset().compatible_with_bike(bike_model_id)

    def low_stock(self) -> ProductQuerySet:
        return self.get_queryset().low_stock()


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT
# ─────────────────────────────────────────────────────────────────────────────

class Product(TimeStampedModel):
    """
    Motorbike part product.

    Design decisions:
    - compatible_bikes M2M → core "fits my bike" feature
    - weight_grams → programmatic shipping cost calculation
    - low_stock_threshold → triggers LowStockAlert via post_save signal
    - All price properties computed — Decimal precision preserved
    - status + stock together determine is_in_stock
    - Slug includes SKU suffix to guarantee uniqueness across similar names
    """

    class Status(models.TextChoices):
        AVAILABLE    = "available",    _("Available")
        OUT_OF_STOCK = "out_of_stock", _("Out of Stock")
        DISCONTINUED = "discontinued", _("Discontinued")

    name = models.CharField(_("name"), max_length=255)
    slug = models.SlugField(_("slug"), max_length=280, unique=True, blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("category"),
    )
    brand = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("brand"),
        help_text=_("Leave blank if part is universal/aftermarket."),
    )
    compatible_bikes = models.ManyToManyField(
        BikeModel,
        related_name="compatible_products",
        blank=True,
        verbose_name=_("compatible bike models"),
        help_text=_("Select which bike models this part fits."),
    )
    description = models.TextField(_("description"), blank=True, default="")
    sku = models.CharField(
        _("SKU"),
        max_length=50,
        unique=True,
        help_text=_("Stock keeping unit — unique product code."),
    )
    price = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_price = models.DecimalField(
        _("discount price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    stock = models.PositiveIntegerField(_("stock quantity"), default=0)
    weight_grams = models.PositiveIntegerField(
        _("weight (grams)"),
        null=True,
        blank=True,
        help_text=_(
            "Product weight for shipping cost calculation. "
            "Also add as ProductSpecification for display on product page."
        ),
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    is_featured = models.BooleanField(_("is featured"), default=False)
    low_stock_threshold = models.PositiveIntegerField(
        _("low stock threshold"),
        default=5,
        help_text=_(
            "Admin alert triggered when stock falls to or below this number. "
            "Set to 0 to disable alerts for this product."
        ),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products_created",
        verbose_name=_("created by"),
    )

    objects = ProductManager()

    class Meta:
        verbose_name        = _("product")
        verbose_name_plural = _("products")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category",    "status"]),
            models.Index(fields=["brand",       "status"]),
            models.Index(fields=["is_featured", "status"]),
            models.Index(fields=["stock",       "status"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            base_slug = slugify(self.name)
            sku_slug  = slugify(self.sku) if self.sku else ""
            self.slug = f"{base_slug}-{sku_slug}" if sku_slug else base_slug
        super().save(*args, **kwargs)
        logger.debug("Product saved: %s (sku=%s)", self.name, self.sku)

    # ─── Stock Properties ─────────────────────────────────────────────

    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0 and self.status == self.Status.AVAILABLE

    @property
    def is_low_stock(self) -> bool:
        """
        True when stock is at or below threshold and threshold > 0.
        Used by post_save signal to decide whether to create LowStockAlert.
        """
        return self.low_stock_threshold > 0 and self.stock <= self.low_stock_threshold

    # ─── Price Properties ─────────────────────────────────────────────

    @property
    def current_price(self) -> Decimal:
        """Return discount price if active, otherwise regular price."""
        return self.discount_price if self.discount_price else self.price

    @property
    def has_discount(self) -> bool:
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def discount_percentage(self) -> int:
        """Discount percentage rounded to nearest integer. 0 if no discount."""
        if not self.has_discount:
            return 0
        return round((1 - (self.discount_price / self.price)) * 100)

    # ─── Compatibility ────────────────────────────────────────────────

    def is_compatible_with(self, bike_model_id: int) -> bool:
        """
        Check if this product fits a specific bike model.

        ⚠️  Fires a DB query on every call.
        For filtering a PRODUCT LIST by bike, use the QuerySet method:
            Product.objects.compatible_with_bike(bike_model_id)

        Safe for single-product detail views where compatible_bikes
        is already prefetched.
        """
        return self.compatible_bikes.filter(id=bike_model_id).exists()


# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT IMAGE
# ─────────────────────────────────────────────────────────────────────────────

class ProductImage(TimeStampedModel):
    """
    Product image gallery. One product can have multiple images,
    with one marked as primary for listing thumbnails.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("product"),
    )
    image = models.ImageField(_("image"), upload_to="products/%Y/%m/")
    is_primary = models.BooleanField(_("is primary"), default=False)
    order = models.PositiveIntegerField(_("display order"), default=0)

    class Meta:
        verbose_name        = _("product image")
        verbose_name_plural = _("product images")
        ordering            = ["order", "created_at"]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs) -> None:
        if self.is_primary:
            self._set_as_sole_primary(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _set_as_sole_primary(self, *args, **kwargs) -> None:
        """
        Atomically sets this image as the sole primary image for its product.
        Uses select_for_update() to prevent concurrent uploads both winning
        the primary slot simultaneously.
        """
        with transaction.atomic():
            list(
                ProductImage.objects.select_for_update().filter(
                    product_id=self.product_id
                )
            )
            ProductImage.objects.filter(
                product_id=self.product_id,
                is_primary=True,
            ).exclude(pk=self.pk).update(is_primary=False)

            super().save(*args, **kwargs)

            logger.debug(
                "Primary image set atomically: product=%s image=%s",
                self.product_id,
                self.pk,
            )

# ─────────────────────────────────────────────────────────────────────────────
# PRODUCT SPECIFICATION
# ─────────────────────────────────────────────────────────────────────────────

class ProductSpecification(TimeStampedModel):
    """
    Flexible key-value specification pairs for a product.

    Why not fixed fields on Product:
    - Oil filter specs differ from brake pad specs differ from chain specs
    - Admin adds any spec type without code deployment
    - Frontend renders as generic key-value table for all product types

    Examples:
        Oil Filter: Material=Steel, Thread=M20×1.5, Height=65mm
        Brake Pad:  Material=Semi-metallic, Thickness=12mm, Position=Front
        Chain:      Links=116, Pitch=525, Tensile Strength=8500kg
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="specifications",
        verbose_name=_("product"),
    )
    name = models.CharField(
        _("specification name"),
        max_length=100,
        help_text=_("e.g. Material, Weight, Thread Size, Position"),
    )
    value = models.CharField(
        _("specification value"),
        max_length=255,
        help_text=_("e.g. OEM Steel, 250g, M20×1.5, Front"),
    )
    unit = models.CharField(
        _("unit"),
        max_length=20,
        blank=True,
        default="",
        help_text=_(
            "Optional unit e.g. mm, kg, g. "
            "Leave blank if value already includes unit."
        ),
    )
    display_order = models.PositiveSmallIntegerField(
        _("display order"),
        default=0,
        help_text=_("Controls order specs appear on product page."),
    )

    class Meta:
        verbose_name        = _("product specification")
        verbose_name_plural = _("product specifications")
        ordering            = ["display_order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "name"],
                name="unique_spec_name_per_product",
            )
        ]

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        logger.debug(
            "ProductSpecification saved: product=%s name=%s value=%s",
            self.product_id, self.name, self.value,
        )

    def __str__(self) -> str:
        unit_str = f" {self.unit}" if self.unit else ""
        return f"{self.product.name} — {self.name}: {self.value}{unit_str}"


# ─────────────────────────────────────────────────────────────────────────────
# STOCK RESERVATION
# ─────────────────────────────────────────────────────────────────────────────

class StockReservation(TimeStampedModel):
    """
    Temporarily locks stock during active checkout session.

    Prevents overselling when multiple customers checkout the same
    product simultaneously — critical during Eid/flash sale traffic.

    Flow:
        Customer starts checkout →
        StockReservation created →
        Product.stock logically reduced for other customers →
        Order confirmed → reservation deleted, stock permanently decremented →
        Checkout abandoned/expired → Celery task restores stock

    Celery beat task runs every 5 minutes:
        StockReservation.objects.filter(expires_at__lt=now()).delete()
        post_delete signal restores Product.stock for each deleted reservation.
    """

    RESERVATION_MINUTES = 15

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="reservations",
        verbose_name=_("product"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="stock_reservations",
        verbose_name=_("user"),
    )
    session_key = models.CharField(
        _("session key"),
        max_length=40,
        blank=True,
        default="",
        db_index=True,
        help_text=_("Fallback identifier if user logs out mid-checkout."),
    )
    quantity   = models.PositiveIntegerField(_("reserved quantity"))
    expires_at = models.DateTimeField(_("expires at"), db_index=True)

    class Meta:
        verbose_name        = _("stock reservation")
        verbose_name_plural = _("stock reservations")
        constraints = [
            models.UniqueConstraint(
                fields=["product", "user"],
                name="unique_reservation_per_user_product",
            )
        ]
        indexes = [
            models.Index(fields=["product",    "expires_at"]),
            models.Index(fields=["user",       "expires_at"]),
            models.Index(fields=["expires_at"]),
        ]

    def save(self, *args, **kwargs) -> None:
        if not self.expires_at:
            self.expires_at = (
                timezone.now() + timedelta(minutes=self.RESERVATION_MINUTES)
            )
        super().save(*args, **kwargs)
        logger.debug(
            "StockReservation: product=%s user=%s qty=%s expires=%s",
            self.product_id, self.user_id, self.quantity, self.expires_at,
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    def __str__(self) -> str:
        return (
            f"Reserve {self.quantity}× {self.product.name} "
            f"for {self.user.email} until {self.expires_at}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# LOW STOCK ALERT
# ─────────────────────────────────────────────────────────────────────────────

class LowStockAlert(TimeStampedModel):
    """
    Alert record created when Product.stock <= Product.low_stock_threshold.

    Created by post_save signal on Product whenever stock changes.
    Admin resolves by restocking and marking is_resolved=True.

    Partial immutability:
    - product_id, stock_at_alert, threshold_at_alert → immutable after creation
    - is_resolved, resolved_at → mutable (resolution workflow only)
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="low_stock_alerts",
        verbose_name=_("product"),
    )
    stock_at_alert = models.PositiveIntegerField(
        _("stock at alert time"),
        help_text=_("Product.stock value when alert was triggered."),
    )
    threshold_at_alert = models.PositiveIntegerField(
        _("threshold at alert time"),
        help_text=_(
            "Product.low_stock_threshold when alert was triggered. "
            "Snapshotted in case threshold is later changed."
        ),
    )
    is_resolved = models.BooleanField(
        _("resolved"),
        default=False,
        help_text=_("Mark True after restocking product."),
    )
    resolved_at = models.DateTimeField(_("resolved at"), null=True, blank=True)

    class Meta:
        verbose_name        = _("low stock alert")
        verbose_name_plural = _("low stock alerts")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["product",     "is_resolved"]),
            models.Index(fields=["is_resolved", "created_at"]),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            # Guard immutable fields without an extra SELECT.
            # Callers MUST use update_fields when updating resolution status:
            #   alert.is_resolved = True
            #   alert.save(update_fields=["is_resolved", "resolved_at"])
            update_fields = kwargs.get("update_fields")
            if update_fields:
                immutable = {"product_id", "stock_at_alert", "threshold_at_alert"}
                attempted = immutable.intersection(set(update_fields))
                if attempted:
                    raise ValueError(
                        f"LowStockAlert fields are immutable after creation: "
                        f"{attempted}"
                    )
            # Auto-manage resolved_at timestamp
            if self.is_resolved and not self.resolved_at:
                self.resolved_at = timezone.now()
            elif not self.is_resolved:
                self.resolved_at = None

        super().save(*args, **kwargs)
        logger.debug(
            "LowStockAlert saved: product=%s stock=%s resolved=%s",
            self.product_id, self.stock_at_alert, self.is_resolved,
        )

    def __str__(self) -> str:
        return (
            f"Low stock — {self.product.name} "
            f"({self.stock_at_alert} units remaining)"
        )
