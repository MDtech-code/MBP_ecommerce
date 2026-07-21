# apps/logistics/serializers.py
from __future__ import annotations

"""
Logistics serializers — input validation and output representation.

Responsibility:
    Input serializers: validate and clean incoming request data only.
    Output serializers: shape model data for API responses.
    Zero business logic. Zero ORM mutations. Zero service calls.

Serializer inventory:
    ShipmentCreateSerializer       — write: admin creates shipment
    ShipmentStatusUpdateSerializer — write: admin manual status update
    ShipmentStatusLogSerializer    — read:  single status log entry
    ShipmentListSerializer         — read:  lightweight admin list
    ShipmentDetailSerializer       — read:  full detail with log history
    OrderTrackingSerializer        — read:  customer-facing tracking view
"""

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.core.mixins import TimestampFieldsMixin

from .models import CourierPartner, Shipment, ShipmentStatusLog


class ShipmentCreateSerializer(serializers.Serializer):
    """
    Input validation for creating a shipment for a CONFIRMED order.

    Validates courier choice, AWB format, weight, and cost fields.
    order_number is taken from the URL — not in request body.
    Business validation (order status, duplicate shipment) is in
    ShipmentService.create_shipment().
    """

    courier = serializers.ChoiceField(
        choices=CourierPartner.choices,
        error_messages={
            "required": _("Courier partner is required."),
            "invalid_choice": _("Invalid courier partner selected."),
        },
    )
    tracking_number = serializers.CharField(
        max_length=100,
        error_messages={
            "required": _("Tracking number (AWB) is required."),
            "blank": _("Tracking number cannot be empty."),
        },
    )
    weight_kg = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=0.01,
        default="0.50",
    )
    shipping_cost_pkr = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0,
        default="0.00",
    )
    estimated_delivery_date = serializers.DateField(
        required=False,
        allow_null=True,
        default=None,
    )

    def validate_tracking_number(self, value: str) -> str:
        """Strip whitespace and uppercase tracking number for consistency."""
        return value.strip().upper()


class ShipmentStatusUpdateSerializer(serializers.Serializer):
    """
    Input validation for manually updating a shipment's status.

    Used by admin staff when courier webhook is unavailable or
    for manual status corrections.
    new_status must be a valid Shipment.Status choice.
    """

    new_status = serializers.ChoiceField(
        choices=Shipment.Status.choices,
        error_messages={
            "required": _("New status is required."),
            "invalid_choice": _("Invalid shipment status."),
        },
    )
    note = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
    )


class ShipmentStatusLogSerializer(serializers.ModelSerializer):
    """
    Read-only output for a single shipment status log entry.

    source_display gives the human-readable source label.
    No timestamps mixin — created_at is the only timestamp
    and it is already a model field exposed directly.
    """

    source_display = serializers.CharField(
        source="get_source_display",
        read_only=True,
    )

    class Meta:
        model = ShipmentStatusLog
        fields = [
            "id",
            "from_status",
            "to_status",
            "source",
            "source_display",
            "created_at",
        ]


class ShipmentListSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Lightweight read-only output for admin shipment list cards.

    Includes order number and destination for quick overview.
    Excludes full status log — too heavy for list view.
    """

    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    courier_display = serializers.CharField(
        source="get_courier_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )

    class Meta:
        model = Shipment
        fields = [
            "id",
            "order_number",
            "tracking_number",
            "courier",
            "courier_display",
            "status",
            "status_display",
            "shipment_type",
            "is_cod",
            "cod_amount",
            "destination_city",
            "estimated_delivery_date",
            "actual_delivery_date",
            "created_at",
            "updated_at",
        ]


class ShipmentDetailSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Full read-only output for admin shipment detail page.

    Includes nested status log history and all financial fields.
    courier_display and status_display give human-readable labels
    alongside the machine-readable choice values.
    """

    order_number = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    courier_display = serializers.CharField(
        source="get_courier_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    status_logs = ShipmentStatusLogSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "id",
            "order_number",
            "tracking_number",
            "courier",
            "courier_display",
            "status",
            "status_display",
            "shipment_type",
            "is_cod",
            "cod_amount",
            "shipping_cost_pkr",
            "destination_city",
            "weight_kg",
            "estimated_delivery_date",
            "actual_delivery_date",
            "raw_courier_response",
            "status_logs",
            "created_at",
            "updated_at",
        ]


class OrderTrackingSerializer(serializers.ModelSerializer):
    """
    Customer-facing read-only tracking output.

    Intentionally limited — exposes only tracking and status info.
    Does NOT expose: cod_amount, shipping_cost_pkr, raw_courier_response,
    or any financial fields — these are internal admin data.
    """

    courier_display = serializers.CharField(
        source="get_courier_display",
        read_only=True,
    )
    status_display = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    status_logs = ShipmentStatusLogSerializer(many=True, read_only=True)

    class Meta:
        model = Shipment
        fields = [
            "tracking_number",
            "courier",
            "courier_display",
            "status",
            "status_display",
            "estimated_delivery_date",
            "actual_delivery_date",
            "status_logs",
        ]