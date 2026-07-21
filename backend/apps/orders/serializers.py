# apps/orders/serializers.py
from __future__ import annotations

"""
Order serializers — input validation and output representation.

Responsibility:
    Input serializers: validate and clean incoming request data only.
    Output serializers: shape model data for API responses.
    Zero business logic. Zero ORM mutations. Zero service calls.

Serializer inventory:
    ShippingAddressInputSerializer  — write: checkout address input
    CheckoutInputSerializer         — write: full checkout input
    OrderShippingAddressSerializer  — read:  immutable address snapshot
    OrderItemSerializer             — read:  order line item snapshot
    OrderListSerializer             — read:  lightweight list card
    OrderDetailSerializer           — read:  full order detail with nesting
"""

from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.common.validators import phone_validator
from apps.core.mixins import TimestampFieldsMixin

from .models import Order, OrderItem, OrderShippingAddress


class ShippingAddressInputSerializer(serializers.Serializer):
    """
    Input validation for the shipping address block inside checkout.

    Validates all required address fields including phone format
    and province code length. Address is snapshotted on Order creation —
    this serializer is the only entry point for that data.
    """

    full_name = serializers.CharField(
        max_length=255,
        error_messages={"required": _("Full name is required.")},
    )
    phone = serializers.CharField(
        max_length=15,
        error_messages={"required": _("Phone number is required.")},
    )
    address_line1 = serializers.CharField(
        max_length=255,
        error_messages={"required": _("Address line 1 is required.")},
    )
    address_line2 = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        default="",
    )
    city = serializers.CharField(
        max_length=100,
        error_messages={"required": _("City is required.")},
    )
    province = serializers.CharField(
        max_length=2,
        error_messages={"required": _("Province code is required.")},
    )
    postal_code = serializers.CharField(
        max_length=10,
        error_messages={"required": _("Postal code is required.")},
    )

    def validate_phone(self, value: str) -> str:
        """
        Run phone_validator from common.validators against the phone field.

        phone_validator raises ValidationError on invalid format —
        serializer catches and converts to field error automatically.
        """
        try:
            phone_validator(value)
        except Exception:
            raise serializers.ValidationError(
                _("Enter a valid Pakistani phone number e.g. 03001234567.")
            )
        return value

    def validate_province(self, value: str) -> str:
        """
        Province must be exactly 2 characters — Pakistani province codes.

        e.g. PB (Punjab), SD (Sindh), KP (Khyber Pakhtunkhwa),
             BN (Balochistan), GB (Gilgit-Baltistan), AK (Azad Kashmir).
        """
        if len(value.strip()) != 2:
            raise serializers.ValidationError(
                _("Province must be a 2-character code e.g. PB, SD, KP.")
            )
        return value.strip().upper()


class CheckoutInputSerializer(serializers.Serializer):
    """
    Input validation for the full checkout request body.

    Wraps payment method selection, nested shipping address,
    and optional delivery notes. Coupon is NOT accepted here —
    it is already on Cart.coupon from the apply endpoint.
    """

    payment_method = serializers.ChoiceField(
        choices=Order.PaymentMethod.choices,
        error_messages={
            "required": _("Payment method is required."),
            "invalid_choice": _("Invalid payment method selected."),
        },
    )
    shipping_address = ShippingAddressInputSerializer()
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
    )


class OrderShippingAddressSerializer(serializers.ModelSerializer):
    """
    Read-only output representation of the immutable shipping address snapshot.

    Exposes full_address computed property alongside individual fields
    for flexible frontend rendering — list view uses city/province,
    detail view uses full_address.
    """

    full_address = serializers.CharField(read_only=True)

    class Meta:
        model = OrderShippingAddress
        fields = [
            "full_name",
            "phone",
            "address_line1",
            "address_line2",
            "city",
            "province",
            "postal_code",
            "country",
            "full_address",
        ]


class OrderItemSerializer(serializers.ModelSerializer):
    """
    Read-only output representation of a single order line item.

    All fields are snapshots taken at order placement time.
    No timestamps — line items are part of the order snapshot,
    not independently auditable resources.
    """

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "product_sku",
            "original_price",
            "unit_price",
            "quantity",
            "subtotal",
            "discount_amount",
            "tax_rate_percentage",
            "tax_amount",
        ]


class OrderListSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Lightweight read-only output for order history list cards.

    Excludes nested items and full address — too heavy for a list.
    Exposes payment_status from Order.payment_status property
    and city/province from the related shipping_address for display.
    item_count gives the number of distinct line items without
    loading the full items queryset.
    """

    payment_status = serializers.CharField(
        source="payment_status",
        read_only=True,
    )
    city = serializers.CharField(
        source="shipping_address.city",
        read_only=True,
        default="",
    )
    province = serializers.CharField(
        source="shipping_address.province",
        read_only=True,
        default="",
    )
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_number",
            "status",
            "payment_method",
            "total_price",
            "discount_amount",
            "coupon_code_snapshot",
            "placed_at",
            "item_count",
            "payment_status",
            "city",
            "province",
            "created_at",
            "updated_at",
        ]

    def get_item_count(self, obj: Order) -> int:
        """
        Return number of distinct line items in this order.

        Uses prefetch cache when items are prefetched — no extra query.
        Falls back to count() query if not prefetched.
        """
        if hasattr(obj, "_prefetched_objects_cache") and \
                "items" in obj._prefetched_objects_cache:
            return len(obj._prefetched_objects_cache["items"])
        return obj.items.count()

class OrderDetailSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Full read-only output for the order detail page.

    Includes nested shipping address, all line items, payment status,
    and action flags (is_cancellable, is_terminal). TimestampFieldsMixin
    adds created_at and updated_at as ISO-8601 timezone-aware fields.

    payment_status, is_cancellable, is_terminal are model properties —
    SerializerMethodField used for all three. Using source= on a field
    whose name matches the property name causes DRF to raise a
    redundant source error at serializer class construction time.
    """

    shipping_address = OrderShippingAddressSerializer(read_only=True)
    items            = OrderItemSerializer(many=True, read_only=True)
    payment_status   = serializers.SerializerMethodField()
    is_cancellable   = serializers.SerializerMethodField()
    is_terminal      = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_number",
            "status",
            "payment_method",
            "notes",
            "subtotal",
            "shipping_fee",
            "discount_amount",
            "tax_amount",
            "total_price",
            "coupon_code_snapshot",
            "placed_at",
            "confirmed_at",
            "cancelled_at",
            "shipping_address",
            "items",
            "payment_status",
            "is_cancellable",
            "is_terminal",
            "created_at",
            "updated_at",
        ]

    def get_payment_status(self, obj: Order) -> str:
        """
        Read payment status from Order.payment_status property.

        Property queries payment_transactions related manager and
        returns the latest transaction status, or 'PENDING' if none.
        """
        return obj.payment_status

    def get_is_cancellable(self, obj: Order) -> bool:
        """
        Return whether this order can be cancelled by the customer.

        True only when order status is PENDING.
        """
        return obj.is_cancellable

    def get_is_terminal(self, obj: Order) -> bool:
        """
        Return whether this order has reached a terminal state.

        True when status is CANCELLED or REFUNDED — no further
        transitions are possible from these states.
        """
        return obj.is_terminal
# class OrderDetailSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
#     """
#     Full read-only output for the order detail page.

#     Includes nested shipping address, all line items, payment status,
#     and action flags (is_cancellable). TimestampFieldsMixin adds
#     created_at and updated_at as ISO-8601 timezone-aware fields.
#     """

#     shipping_address = OrderShippingAddressSerializer(read_only=True)
#     items = OrderItemSerializer(many=True, read_only=True)
#     payment_status = serializers.CharField(
#         source="payment_status",
#         read_only=True,
#     )
#     is_cancellable = serializers.BooleanField(
#         source="is_cancellable",
#         read_only=True,
#     )
#     is_terminal = serializers.BooleanField(
#         source="is_terminal",
#         read_only=True,
#     )

#     class Meta:
#         model = Order
#         fields = [
#             "order_number",
#             "status",
#             "payment_method",
#             "notes",
#             "subtotal",
#             "shipping_fee",
#             "discount_amount",
#             "tax_amount",
#             "total_price",
#             "coupon_code_snapshot",
#             "placed_at",
#             "confirmed_at",
#             "cancelled_at",
#             "shipping_address",
#             "items",
#             "payment_status",
#             "is_cancellable",
#             "is_terminal",
#             "created_at",
#             "updated_at",
#         ]