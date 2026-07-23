# apps/wishlist/serializers.py
from __future__ import annotations

"""
Wishlist serializers — input validation and output shaping.

WishlistItemSerializer — output: shapes WishlistItem with product detail.
WishlistAddSerializer  — input:  validates product_id for add operation.

No business logic in serializers — validation only.
Duplicate check lives in WishlistService.add_item().

Dependency direction:
    models → selectors → services → serializers → views
"""

from rest_framework import serializers

from apps.core.mixins import TimestampFieldsMixin
from apps.products.models import Product
from apps.wishlist.models import WishlistItem


class WishlistItemSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Output serializer for a single WishlistItem.

    Exposes product summary fields inline — the frontend needs
    product name, price, and image to render the wishlist page
    without a second API call per item.
    """

    product_id    = serializers.IntegerField(
        source="product.id",
        read_only=True,
    )
    product_name  = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    product_slug  = serializers.SlugField(
        source="product.slug",
        read_only=True,
    )
    product_price = serializers.DecimalField(
        source="product.current_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    product_in_stock = serializers.BooleanField(
        source="product.is_in_stock",
        read_only=True,
    )

    class Meta:
        model  = WishlistItem
        fields = [
            "id",
            "product_id",
            "product_name",
            "product_slug",
            "product_price",
            "product_in_stock",
            "created_at",
            "updated_at",
        ]


class WishlistAddSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/wishlist/add/

    Validates that product_id refers to an existing Product.
    Uses PrimaryKeyRelatedField so Django validates existence
    at the serializer layer — no need for a separate DB check
    in the view before calling the service.

    Does NOT validate business rules — WishlistService handles:
        - Whether item already exists in user's wishlist.
    """

    product_id = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.all(),
        help_text="Primary key of the product to add to wishlist.",
    )

    def validate_product_id(self, product: Product) -> int:
        """
        Return product PK integer rather than Product instance.

        WishlistService.add_item() receives product_id: int.
        PrimaryKeyRelatedField returns the Product instance by default —
        this validator extracts the pk so the service signature stays clean.
        """
        return product.pk