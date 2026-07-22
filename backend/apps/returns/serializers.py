# apps/returns/serializers.py
from __future__ import annotations

"""
Return serializers — input validation and output shaping for the returns app.

Responsibility:
    ReturnCreateSerializer  — validates customer return submission input.
    ReturnListSerializer    — shapes ReturnRequest list for customer view.
    ReturnDetailSerializer  — shapes ReturnRequest detail with photos.
    ReturnPhotoSerializer   — shapes ReturnItemPhoto for detail output.

Design rules:
    - No business logic in serializers — validation only.
    - Eligibility checks (delivery status, window, uniqueness) live
      in ReturnService, not here.
    - Serializers validate field types, choices, and required presence.
    - TimestampFieldsMixin provides created_at / updated_at as ISO-8601.
    - Photo upload accepted as multipart — handled by ReturnCreateSerializer.

Dependency direction:
    models → selectors → services → serializers → views
"""

from rest_framework import serializers

from apps.core.mixins import TimestampFieldsMixin
from apps.returns.models import ReturnRequest, ReturnItemPhoto


class ReturnPhotoSerializer(serializers.ModelSerializer):
    """
    Output serializer for a single ReturnItemPhoto.

    Used as nested serializer inside ReturnDetailSerializer.
    image field returns the full URL via request context.
    """

    class Meta:
        model  = ReturnItemPhoto
        fields = ["id", "image", "caption"]


class ReturnCreateSerializer(serializers.Serializer):
    """
    Input serializer for customer return request submission.

    Validates:
        - order_item_id is a positive integer.
        - reason is a valid ReturnRequest.Reason choice.
        - resolution_requested is a valid ReturnRequest.Resolution choice.
        - reason_detail is optional text.
        - photos is an optional list of image files (multipart).

    Does NOT validate business rules — service layer handles:
        - Order ownership.
        - Delivery status.
        - Return window.
        - Uniqueness per order item.
        - Photos required for specific reasons.
    """

    order_item_id = serializers.IntegerField(
        min_value=1,
        help_text="Primary key of the OrderItem being returned.",
    )
    reason = serializers.ChoiceField(
        choices=ReturnRequest.Reason.choices,
        help_text="Reason for the return.",
    )
    reason_detail = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        max_length=2000,
        help_text="Customer explanation in their own words.",
    )
    resolution_requested = serializers.ChoiceField(
        choices=ReturnRequest.Resolution.choices,
        default=ReturnRequest.Resolution.REFUND,
        help_text="Preferred resolution: refund, exchange, or store_credit.",
    )
    photos = serializers.ListField(
        child=serializers.ImageField(),
        required=False,
        allow_empty=True,
        default=list,
        help_text=(
            "Upload photos as multipart/form-data. "
            "Required for damaged and not_described reasons."
        ),
    )


class ReturnListSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Output serializer for a ReturnRequest in list view.

    Shows summary fields only — no photos in list.
    Includes human-readable display values alongside raw choice values
    so the frontend can display labels without maintaining its own map.
    """

    status_display              = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    reason_display              = serializers.CharField(
        source="get_reason_display",
        read_only=True,
    )
    resolution_requested_display = serializers.CharField(
        source="get_resolution_requested_display",
        read_only=True,
    )
    order_number                = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    product_name                = serializers.CharField(
        source="order_item.product_name",
        read_only=True,
    )

    class Meta:
        model = ReturnRequest
        fields = [
            "id",
            "order_number",
            "product_name",
            "reason",
            "reason_display",
            "resolution_requested",
            "resolution_requested_display",
            "status",
            "status_display",
            "approved_at",
            "received_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]


class ReturnDetailSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Output serializer for a single ReturnRequest with full detail.

    Includes photos as nested list.
    Includes rejection_reason when status is REJECTED.
    Includes all timestamps.
    """

    status_display               = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    reason_display               = serializers.CharField(
        source="get_reason_display",
        read_only=True,
    )
    resolution_requested_display = serializers.CharField(
        source="get_resolution_requested_display",
        read_only=True,
    )
    order_number                 = serializers.CharField(
        source="order.order_number",
        read_only=True,
    )
    product_name                 = serializers.CharField(
        source="order_item.product_name",
        read_only=True,
    )
    photos                       = ReturnPhotoSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = ReturnRequest
        fields = [
            "id",
            "order_number",
            "product_name",
            "reason",
            "reason_display",
            "reason_detail",
            "resolution_requested",
            "resolution_requested_display",
            "status",
            "status_display",
            "rejection_reason",
            "photos",
            "approved_at",
            "received_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]