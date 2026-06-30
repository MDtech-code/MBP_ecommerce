from __future__ import annotations

import logging

from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.conf import settings

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.products")


class Category(TimeStampedModel):
    """
    Product category with optional self-referencing parent
    for subcategories (e.g. Engine > Pistons > Piston Rings).
    """

    name: models.CharField = models.CharField(
        _("name"),
        max_length=100,
        unique=True,
    )
    slug: models.SlugField = models.SlugField(
        _("slug"),
        max_length=120,
        unique=True,
        blank=True,
    )
    parent: models.ForeignKey = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="subcategories",
        verbose_name=_("parent category"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("is active"),
        default=True,
    )

    class Meta:
        verbose_name = _("category")
        verbose_name_plural = _("categories")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def is_subcategory(self) -> bool:
        return self.parent_id is not None


class Brand(TimeStampedModel):
    """
    Motorbike part manufacturer or brand (Honda, Yamaha, Suzuki, etc.)
    """

    name: models.CharField = models.CharField(
        _("name"),
        max_length=100,
        unique=True,
    )
    slug: models.SlugField = models.SlugField(
        _("slug"),
        max_length=120,
        unique=True,
        blank=True,
    )
    logo: models.ImageField = models.ImageField(
        _("logo"),
        upload_to="brands/",
        null=True,
        blank=True,
    )
    is_active: models.BooleanField = models.BooleanField(
        _("is active"),
        default=True,
    )

    class Meta:
        verbose_name = _("brand")
        verbose_name_plural = _("brands")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BikeModel(TimeStampedModel):
    """
    Specific motorbike model used for product compatibility matching.

    This is the core feature that differentiates this store from
    generic ecommerce — customers can filter parts by their exact bike.
    """

    brand: models.ForeignKey = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="bike_models",
        verbose_name=_("brand"),
    )
    name: models.CharField = models.CharField(
        _("model name"),
        max_length=100,
        help_text=_("e.g. CB150F, YBR125"),
    )
    slug: models.SlugField = models.SlugField(
        _("slug"),
        max_length=150,
        unique=True,
        blank=True,
    )
    year_start: models.PositiveIntegerField = models.PositiveIntegerField(
        _("production start year"),
    )
    year_end: models.PositiveIntegerField = models.PositiveIntegerField(
        _("production end year"),
        null=True,
        blank=True,
        help_text=_("Leave blank if still in production."),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("is active"),
        default=True,
    )

    class Meta:
        verbose_name = _("bike model")
        verbose_name_plural = _("bike models")
        ordering = ["brand__name", "name"]
        unique_together = [["brand", "name"]]

    def __str__(self) -> str:
        year_range = f"{self.year_start}–{self.year_end or 'present'}"
        return f"{self.brand.name} {self.name} ({year_range})"

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(f"{self.brand.name}-{self.name}")
        super().save(*args, **kwargs)

    @property
    def display_name(self) -> str:
        return f"{self.brand.name} {self.name}"

    def covers_year(self, year: int) -> bool:
        """Check if this bike model was in production during given year."""
        if self.year_end is None:
            return year >= self.year_start
        return self.year_start <= year <= self.year_end


class Product(TimeStampedModel):
    """
    Motorbike part product.

    Compatibility with specific bike models is handled via
    ManyToMany relationship for the "fits my bike" filtering feature.
    """

    class Status(models.TextChoices):
        AVAILABLE = "available", _("Available")
        OUT_OF_STOCK = "out_of_stock", _("Out of Stock")
        DISCONTINUED = "discontinued", _("Discontinued")

    name: models.CharField = models.CharField(
        _("name"),
        max_length=255,
    )
    slug: models.SlugField = models.SlugField(
        _("slug"),
        max_length=280,
        unique=True,
        blank=True,
    )
    category: models.ForeignKey = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products",
        verbose_name=_("category"),
    )
    brand: models.ForeignKey = models.ForeignKey(
        Brand,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="products",
        verbose_name=_("brand"),
        help_text=_("Leave blank if part is universal/aftermarket."),
    )
    compatible_bikes: models.ManyToManyField = models.ManyToManyField(
        BikeModel,
        related_name="compatible_products",
        blank=True,
        verbose_name=_("compatible bike models"),
        help_text=_("Select which bike models this part fits."),
    )
    description: models.TextField = models.TextField(
        _("description"),
        blank=True,
        default="",
    )
    sku: models.CharField = models.CharField(
        _("SKU"),
        max_length=50,
        unique=True,
        help_text=_("Stock keeping unit — unique product code."),
    )
    price: models.DecimalField = models.DecimalField(
        _("price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    discount_price: models.DecimalField = models.DecimalField(
        _("discount price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    stock: models.PositiveIntegerField = models.PositiveIntegerField(
        _("stock quantity"),
        default=0,
    )
    status: models.CharField = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.AVAILABLE,
    )
    is_featured: models.BooleanField = models.BooleanField(
        _("is featured"),
        default=False,
    )
    created_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="products_created",
        verbose_name=_("created by"),
    )

    class Meta:
        verbose_name = _("product")
        verbose_name_plural = _("products")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs) -> None:
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
        logger.debug("Product saved: %s (sku=%s)", self.name, self.sku)

    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0 and self.status == self.Status.AVAILABLE

    @property
    def current_price(self) -> models.DecimalField:
        """Return discount price if set, otherwise regular price."""
        return self.discount_price if self.discount_price else self.price

    @property
    def has_discount(self) -> bool:
        return self.discount_price is not None and self.discount_price < self.price

    @property
    def discount_percentage(self) -> int:
        """Calculate discount percentage, rounded to nearest integer."""
        if not self.has_discount:
            return 0
        return round((1 - (self.discount_price / self.price)) * 100)

    def is_compatible_with(self, bike_model_id: int) -> bool:
        """Check if this product fits a specific bike model."""
        return self.compatible_bikes.filter(id=bike_model_id).exists()


class ProductImage(TimeStampedModel):
    """
    Product image gallery. One product can have multiple images,
    with one marked as primary for listing thumbnails.
    """

    product: models.ForeignKey = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name=_("product"),
    )
    image: models.ImageField = models.ImageField(
        _("image"),
        upload_to="products/%Y/%m/",
    )
    is_primary: models.BooleanField = models.BooleanField(
        _("is primary"),
        default=False,
    )
    order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("display order"),
        default=0,
    )

    class Meta:
        verbose_name = _("product image")
        verbose_name_plural = _("product images")
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"Image for {self.product.name}"

    def save(self, *args, **kwargs) -> None:
        """
        Ensure only one primary image per product.
        If this image is marked primary, unmark all others.
        """
        if self.is_primary:
            ProductImage.objects.filter(
                product=self.product, is_primary=True
            ).exclude(id=self.id).update(is_primary=False)
            logger.debug(
                "Primary image updated for product: %s", self.product.name
            )
        super().save(*args, **kwargs)