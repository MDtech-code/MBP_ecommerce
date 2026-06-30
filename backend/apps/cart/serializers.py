from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.api.serializers import BaseModelSerializer
from apps.products.models import Product
from .models import Cart, CartItem


class CartItemSerializer(BaseModelSerializer):
    """Read representation of a single cart line item."""

    product_name: serializers.CharField = serializers.CharField(
        source="product.name", read_only=True,
    )
    product_slug: serializers.CharField = serializers.CharField(
        source="product.slug", read_only=True,
    )
    product_price: serializers.DecimalField = serializers.DecimalField(
        source="product.current_price",
        max_digits=10, decimal_places=2, read_only=True,
    )
    product_image: serializers.SerializerMethodField = serializers.SerializerMethodField()
    is_in_stock: serializers.BooleanField = serializers.BooleanField(
        source="product.is_in_stock", read_only=True,
    )
    subtotal: serializers.FloatField = serializers.FloatField(read_only=True)

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_slug",
            "product_price",
            "product_image",
            "is_in_stock",
            "quantity",
            "subtotal",
        ]
        extra_kwargs = {
            "product": {"write_only": True},
        }

    def get_product_image(self, obj: CartItem) -> str | None:
        image = obj.product.images.filter(is_primary=True).first()
        image = image or obj.product.images.first()
        if image and image.image:
            request = self.context.get("request")
            url = image.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class CartSerializer(BaseModelSerializer):
    """Full cart with all items and computed totals."""

    items: CartItemSerializer = CartItemSerializer(many=True, read_only=True)
    total_items: serializers.IntegerField = serializers.IntegerField(read_only=True)
    total_price: serializers.FloatField = serializers.FloatField(read_only=True)
    is_empty: serializers.BooleanField = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "total_items",
            "total_price",
            "is_empty",
            "updated_at",
        ]


class AddToCartSerializer(serializers.Serializer):
    """Input validation for adding a product to the cart."""

    product_id: serializers.IntegerField = serializers.IntegerField(
        error_messages={"required": _("Product ID is required.")}
    )
    quantity: serializers.IntegerField = serializers.IntegerField(
        default=1,
        min_value=1,
        error_messages={"min_value": _("Quantity must be at least 1.")},
    )

    def validate_product_id(self, value: int) -> int:
        if not Product.objects.filter(
            id=value, status=Product.Status.AVAILABLE
        ).exists():
            raise serializers.ValidationError(
                _("Product not found or is unavailable.")
            )
        return value

    def validate(self, attrs: dict) -> dict:
        product = Product.objects.get(id=attrs["product_id"])
        if attrs["quantity"] > product.stock:
            raise serializers.ValidationError({
                "quantity": _(
                    "Only %(stock)d unit(s) of %(name)s in stock."
                ) % {"stock": product.stock, "name": product.name}
            })
        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """Input validation for updating quantity of an existing cart item."""

    quantity: serializers.IntegerField = serializers.IntegerField(
        min_value=1,
        error_messages={
            "min_value": _("Quantity must be at least 1."),
            "required": _("Quantity is required."),
        },
    )