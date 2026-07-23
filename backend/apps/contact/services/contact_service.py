# apps/contact/services/contact_service.py
from __future__ import annotations

"""
Contact service — business logic for contact message submission.

Responsibility:
    ContactService.submit_message() — creates a ContactMessage record
    for both authenticated and anonymous customers.

    All submission logic lives here, not in serializers or views.
    Zero DRF imports. Zero HTTP concerns.

Anonymous support:
    Contact form is accessible without authentication.
    Authenticated users have their user FK auto-set so admin
    can view their order history alongside the inquiry.
    Anonymous submissions store name and email directly on the model.

Admin workflow:
    All reply and resolution actions are handled via Django admin.
    No REST endpoints exist for admin operations on contact messages.
    ContactReply is created via ContactReplyInline in admin.
    Resolution via mark_resolved admin action.

Dependency direction:
    models → selectors → services → views
"""

import logging

from apps.contact.models import ContactMessage

logger = logging.getLogger("apps.contact")


class ContactService:
    """
    Business operations for contact message lifecycle.

    All methods are static — no instance state required.
    No DomainError raised here — contact submission has no
    business rule violations beyond field validation, which
    the serializer handles.
    """

    @staticmethod
    def submit_message(
        *,
        name: str,
        email: str,
        subject: str,
        message: str,
        phone: str = "",
        user=None,
    ) -> ContactMessage:
        """
        Create a new ContactMessage from a customer inquiry.

        Supports both authenticated and anonymous submissions.
        When user is provided (authenticated), the FK is set so
        admin can cross-reference the customer's order history.

        resolved_at is managed by ContactMessage.save() — auto-set
        when is_resolved becomes True, cleared when False.
        New messages are always created with is_resolved=False.

        Args:
            name:    Customer's display name.
            email:   Reply-to email address.
            subject: Inquiry subject line.
            message: Full inquiry body text.
            phone:   Optional contact number.
            user:    Authenticated User instance or None for anonymous.

        Returns:
            Created ContactMessage instance.
        """
        contact_message = ContactMessage.objects.create(
            user=user,
            name=name,
            email=email,
            phone=phone,
            subject=subject,
            message=message,
            is_resolved=False,
        )

        logger.info(
            "ContactService.submit_message: created | "
            "message_id=%s email=%s user=%s subject=%s",
            contact_message.pk,
            email,
            getattr(user, "pk", "anonymous"),
            subject[:50],
        )

        return contact_message