# apps/payments/serializers.py
from __future__ import annotations

"""
Payment serializers — input validation and output shaping.

PaymentInitiateSerializer  — validates gateway and order_number input.
PaymentStatusSerializer    — shapes PaymentTransaction for status endpoint.

No business logic in serializers — validation only.
Gateway existence check is in PaymentService, not here.
"""

from rest_framework import serializers

from apps.core.mixins import TimestampFieldsMixin
from apps.payments.gateways.registry import ONLINE_GATEWAYS
from apps.payments.models import PaymentTransaction


class PaymentInitiateSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/payments/initiate/

    Validates that:
        - order_number is a non-empty string.
        - gateway is one of the known ONLINE gateways.

    Does NOT validate business rules — PaymentService handles:
        - Order ownership and PENDING status.
        - Existing SUCCESS transaction check.
        - Gateway credentials configured check.
    """

    order_number = serializers.CharField(
        max_length=30,
        help_text="Order number from the placed order.",
    )
    gateway = serializers.ChoiceField(
        choices=[(g, g) for g in sorted(ONLINE_GATEWAYS)],
        help_text=(
            f"Online payment gateway to use. "
            f"Supported: {', '.join(sorted(ONLINE_GATEWAYS))}."
        ),
    )


class PaymentStatusSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Output serializer for GET /api/payments/status/<order_number>/

    Returns current payment transaction state for the order.
    Includes human-readable status display and gateway display.
    Does not expose internal error_message in full — only a
    sanitised version safe to show the customer.
    """

    status_display  = serializers.CharField(
        source="get_status_display",
        read_only=True,
    )
    gateway_display = serializers.CharField(
        source="get_gateway_display",
        read_only=True,
    )

    class Meta:
        model  = PaymentTransaction
        fields = [
            "id",
            "gateway",
            "gateway_display",
            "status",
            "status_display",
            "amount_pkr",
            "transaction_reference",
            "created_at",
            "updated_at",
        ]