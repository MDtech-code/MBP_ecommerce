# apps/contact/serializers.py
from __future__ import annotations

"""
Contact serializers — input validation and output shaping.

ContactSubmitSerializer  — validates customer contact form submission.
ContactConfirmSerializer — shapes ContactMessage for submission response.

Design rules:
    - No business logic in serializers — validation only.
    - ContactSubmitSerializer validates field formats and lengths.
    - Phone field is optional — not all customers provide it.
    - Email field uses EmailField for format validation.
    - Subject and message have max_length guards to prevent abuse.

Dependency direction:
    models → selectors → services → serializers → views
"""

from rest_framework import serializers

from apps.contact.models import ContactMessage


class ContactSubmitSerializer(serializers.Serializer):
    """
    Input serializer for POST /api/contact/

    Validates all fields from the customer contact form.
    No auth required — anonymous customers can submit.

    Fields:
        name:    Required. Customer display name.
        email:   Required. Valid email format enforced.
        phone:   Optional. Contact number.
        subject: Required. Inquiry subject line.
        message: Required. Full inquiry body.
    """

    name = serializers.CharField(
        max_length=100,
        help_text="Your full name.",
    )
    email = serializers.EmailField(
        help_text="Email address we will use to reply to you.",
    )
    phone = serializers.CharField(
        max_length=15,
        required=False,
        allow_blank=True,
        default="",
        help_text="Optional contact number.",
    )
    subject = serializers.CharField(
        max_length=200,
        help_text="Brief description of your inquiry.",
    )
    message = serializers.CharField(
        max_length=5000,
        help_text="Full details of your inquiry.",
    )

    def validate_name(self, value: str) -> str:
        """Strip whitespace and enforce non-empty after strip."""
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError(
                "Name cannot be blank or whitespace only."
            )
        return stripped

    def validate_subject(self, value: str) -> str:
        """Strip whitespace and enforce non-empty after strip."""
        stripped = value.strip()
        if not stripped:
            raise serializers.ValidationError(
                "Subject cannot be blank or whitespace only."
            )
        return stripped

    def validate_message(self, value: str) -> str:
        """Strip whitespace and enforce minimum length."""
        stripped = value.strip()
        if len(stripped) < 10:
            raise serializers.ValidationError(
                "Message must be at least 10 characters long."
            )
        return stripped


class ContactConfirmSerializer(serializers.ModelSerializer):
    """
    Output serializer for contact submission confirmation.

    Returns minimal fields — enough for the frontend to display
    a confirmation message with a reference ID.
    Does not expose internal fields like is_resolved or resolved_by.
    """

    class Meta:
        model  = ContactMessage
        fields = [
            "id",
            "name",
            "email",
            "subject",
            "created_at",
        ]