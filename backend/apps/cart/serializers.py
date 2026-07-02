# apps/cart/serializers.py
from __future__ import annotations

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.products.models import Product
from .models import Cart, CartItem


class CartItemSerializer(serializers.ModelSerializer):
    """
    Read representation of a single cart line item.

    Exposes product display fields alongside quantity and subtotal.
    Requires select_related('product') and prefetch_related('product__images')
    on the queryset to avoid N+1 queries.

    product_image resolution:
        Primary image is selected from prefetched images in Python —
        no extra DB query if images are prefetched.
    """

    product_name = serializers.CharField(
        source="product.name",
        read_only=True,
    )
    product_slug = serializers.CharField(
        source="product.slug",
        read_only=True,
    )
    product_price = serializers.DecimalField(
        source="product.current_price",
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    product_image = serializers.SerializerMethodField()
    is_in_stock = serializers.BooleanField(
        source="product.is_in_stock",
        read_only=True,
    )
    subtotal = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

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
        """
        Resolve product's primary image URL.

        Iterates prefetched images in Python — no extra DB query
        if product__images is in the prefetch_related chain.
        Falls back to first image if no primary is set.
        """
        request = self.context.get("request")
        images = list(obj.product.images.all())

        # Select primary first, fall back to first available
        image = next(
            (img for img in images if img.is_primary), None
        ) or (images[0] if images else None)

        if image and image.image:
            url = image.image.url
            return request.build_absolute_uri(url) if request else url
        return None


class CartSerializer(serializers.ModelSerializer):
    """
    Full cart representation with all items and computed totals.

    Requires the cart queryset to use:
        prefetch_related('items__product__images')
    to prevent N+1 queries on items, products, and images.
    """

    items = CartItemSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    total_price = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )
    is_empty = serializers.BooleanField(read_only=True)

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
    """
    Input validation for adding a product to the cart.

    Validates:
        - product_id references an existing, available product.
        - quantity does not exceed current stock.

    The validated product instance is attached to attrs["product"]
    so the view can use it directly — avoiding a third DB fetch.
    """

    product_id = serializers.IntegerField(
        error_messages={"required": _("Product ID is required.")}
    )
    quantity = serializers.IntegerField(
        default=1,
        min_value=1,
        error_messages={
            "min_value": _("Quantity must be at least 1."),
        },
    )

    def validate_product_id(self, value: int) -> int:
        """Assert product exists and is available for purchase."""
        if not Product.objects.filter(
            id=value,
            status=Product.Status.AVAILABLE,
        ).exists():
            raise serializers.ValidationError(
                _("Product not found or is unavailable.")
            )
        return value

    def validate(self, attrs: dict) -> dict:
        """
        Cross-field validation — check quantity against stock.

        Fetches the product once and attaches it to attrs["product"]
        so the view does not need to fetch it again.
        """
        try:
            product = Product.objects.get(id=attrs["product_id"])
        except Product.DoesNotExist:
            raise serializers.ValidationError(
                {"product_id": _("Product not found or is unavailable.")}
            )

        if attrs["quantity"] > product.stock:
            raise serializers.ValidationError({
                "quantity": _(
                    "Only %(stock)d unit(s) of %(name)s in stock."
                ) % {"stock": product.stock, "name": product.name}
            })

        # Attach product to avoid re-fetching in the view
        attrs["product"] = product
        return attrs


class UpdateCartItemSerializer(serializers.Serializer):
    """
    Input validation for updating the quantity of an existing cart item.

    Quantity must be at least 1. Stock validation happens in the view
    where the current item and product context are available.
    """

    quantity = serializers.IntegerField(
        min_value=0,
        error_messages={
            "min_value": _("Quantity can not negative."),
            "required": _("Quantity is required."),
        },
    )
# from __future__ import annotations

# from django.utils.translation import gettext_lazy as _
# from rest_framework import serializers

# from apps.core.api.serializers import BaseModelSerializer
# from apps.products.models import Product
# from .models import Cart, CartItem


# class CartItemSerializer(BaseModelSerializer):
#     """Read representation of a single cart line item."""

#     product_name: serializers.CharField = serializers.CharField(
#         source="product.name", read_only=True,
#     )
#     product_slug: serializers.CharField = serializers.CharField(
#         source="product.slug", read_only=True,
#     )
#     product_price: serializers.DecimalField = serializers.DecimalField(
#         source="product.current_price",
#         max_digits=10, decimal_places=2, read_only=True,
#     )
#     product_image: serializers.SerializerMethodField = serializers.SerializerMethodField()
#     is_in_stock: serializers.BooleanField = serializers.BooleanField(
#         source="product.is_in_stock", read_only=True,
#     )
#     subtotal: serializers.FloatField = serializers.FloatField(read_only=True)

#     class Meta:
#         model = CartItem
#         fields = [
#             "id",
#             "product",
#             "product_name",
#             "product_slug",
#             "product_price",
#             "product_image",
#             "is_in_stock",
#             "quantity",
#             "subtotal",
#         ]
#         extra_kwargs = {
#             "product": {"write_only": True},
#         }

#     def get_product_image(self, obj: CartItem) -> str | None:
#         image = obj.product.images.filter(is_primary=True).first()
#         image = image or obj.product.images.first()
#         if image and image.image:
#             request = self.context.get("request")
#             url = image.image.url
#             return request.build_absolute_uri(url) if request else url
#         return None


# class CartSerializer(BaseModelSerializer):
#     """Full cart with all items and computed totals."""

#     items: CartItemSerializer = CartItemSerializer(many=True, read_only=True)
#     total_items: serializers.IntegerField = serializers.IntegerField(read_only=True)
#     total_price: serializers.FloatField = serializers.FloatField(read_only=True)
#     is_empty: serializers.BooleanField = serializers.BooleanField(read_only=True)

#     class Meta:
#         model = Cart
#         fields = [
#             "id",
#             "items",
#             "total_items",
#             "total_price",
#             "is_empty",
#             "updated_at",
#         ]


# class AddToCartSerializer(serializers.Serializer):
#     """Input validation for adding a product to the cart."""

#     product_id: serializers.IntegerField = serializers.IntegerField(
#         error_messages={"required": _("Product ID is required.")}
#     )
#     quantity: serializers.IntegerField = serializers.IntegerField(
#         default=1,
#         min_value=1,
#         error_messages={"min_value": _("Quantity must be at least 1.")},
#     )

#     def validate_product_id(self, value: int) -> int:
#         if not Product.objects.filter(
#             id=value, status=Product.Status.AVAILABLE
#         ).exists():
#             raise serializers.ValidationError(
#                 _("Product not found or is unavailable.")
#             )
#         return value

#     def validate(self, attrs: dict) -> dict:
#         product = Product.objects.get(id=attrs["product_id"])
#         if attrs["quantity"] > product.stock:
#             raise serializers.ValidationError({
#                 "quantity": _(
#                     "Only %(stock)d unit(s) of %(name)s in stock."
#                 ) % {"stock": product.stock, "name": product.name}
#             })
#         return attrs


# class UpdateCartItemSerializer(serializers.Serializer):
#     """Input validation for updating quantity of an existing cart item."""

#     quantity: serializers.IntegerField = serializers.IntegerField(
#         min_value=1,
#         error_messages={
#             "min_value": _("Quantity must be at least 1."),
#             "required": _("Quantity is required."),
#         },
#     )