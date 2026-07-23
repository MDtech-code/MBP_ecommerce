# apps/contact/selectors/contact_selectors.py
from __future__ import annotations

"""
Contact selectors — all database reads for the contact app.

Responsibility:
    Every query that touches ContactMessage or ContactReply lives here.
    Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Note:
    Customer-facing flow has only one write endpoint (submit message).
    There is no customer-facing read endpoint — customers submit and
    receive confirmation only. All reading and replying is admin-driven.
    Selectors here are primarily for admin use and future extensibility.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db.models import QuerySet

from apps.contact.models import ContactMessage

logger = logging.getLogger("apps.contact")


def get_unresolved_messages() -> QuerySet:
    """
    Return all unresolved ContactMessages ordered by oldest first.

    Used by admin to triage support queue.
    Oldest first — FIFO support queue order ensures no inquiry
    gets buried indefinitely by newer submissions.

    Returns:
        QuerySet of ContactMessage instances where is_resolved=False.
    """
    return (
        ContactMessage.objects
        .select_related("user", "resolved_by")
        .filter(is_resolved=False)
        .order_by("created_at")
    )


def get_message_by_id(message_id: int) -> ContactMessage | None:
    """
    Return a single ContactMessage by primary key, or None.

    Used by admin actions to fetch and validate a message
    before marking resolved or adding a reply.

    Args:
        message_id: ContactMessage primary key.

    Returns:
        ContactMessage instance with replies prefetched, or None.
    """
    return (
        ContactMessage.objects
        .select_related("user", "resolved_by")
        .prefetch_related("replies__replied_by")
        .filter(pk=message_id)
        .first()
    )