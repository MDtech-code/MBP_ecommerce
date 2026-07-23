# apps/contact/views.py
from __future__ import annotations

"""
Contact views — HTTP layer for the contact app.

Endpoints:
    POST /api/contact/    ContactSubmitAPIView

Design rules:
    - View inherits from BaseAPIView.
    - No auth required — anonymous customers can submit inquiries.
    - Authenticated user FK auto-set from request.user if authenticated.
    - Serializer validates field formats and lengths only.
    - Service creates the ContactMessage record.
    - No DomainError expected — submission has no business rule violations.
    - All admin operations (reply, resolve) handled via Django admin.

Permission:
    AllowAny — contact form is accessible without authentication.
    Authenticated users have user FK set automatically.

Dependency direction:
    models → selectors → services → serializers → views
"""

import logging

from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response

from apps.core.api.views import BaseAPIView
from apps.contact.serializers import (
    ContactConfirmSerializer,
    ContactSubmitSerializer,
)
from apps.contact.services.contact_service import ContactService

logger = logging.getLogger("apps.contact")


class ContactSubmitAPIView(BaseAPIView):
    """
    POST /api/contact/

    Customer submits a support inquiry via the contact form.

    Accessible without authentication — anonymous customers can
    submit inquiries. Authenticated user FK is auto-set when
    the request comes from a logged-in user so admin can
    cross-reference their order history.

    Returns 201 with a confirmation including the message ID
    so the customer can reference it in follow-up communication.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ContactSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Your message could not be submitted. "
                        "Please check the form and try again.",
                errors=serializer.errors,
                status_code=400,
            )

        validated = serializer.validated_data

        # Auto-set user FK for authenticated requests
        user = (
            request.user
            if request.user and request.user.is_authenticated
            else None
        )

        contact_message = ContactService.submit_message(
            name=validated["name"],
            email=validated["email"],
            subject=validated["subject"],
            message=validated["message"],
            phone=validated.get("phone", ""),
            user=user,
        )

        logger.info(
            "ContactSubmitAPIView.post: submitted | "
            "message_id=%s email=%s authenticated=%s",
            contact_message.pk,
            validated["email"],
            user is not None,
        )

        return self.created_response(
            data=ContactConfirmSerializer(contact_message).data,
            message="Your message has been received. "
                    "Our team will get back to you within 1-2 business days.",
        )