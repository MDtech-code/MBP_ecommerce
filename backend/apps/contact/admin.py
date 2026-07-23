# apps/contact/admin.py
from __future__ import annotations

"""
Contact admin — Django admin for ContactMessage and ContactReply.

Admin workflow:
    1. Staff opens ContactMessage list — sorted oldest unresolved first.
    2. Staff opens individual message to read inquiry.
    3. Staff adds reply via ContactReplyInline — fills body, sends email.
    4. Staff marks resolved via mark_resolved action.
       ContactMessage.save() auto-sets resolved_at and resolved_by.

Design rules:
    - ContactMessage core fields are readonly after creation —
      customer submission is immutable evidence.
    - ContactReply is added via inline — full conversation thread visible.
    - mark_resolved action sets is_resolved=True and resolved_by=request.user.
    - mark_unresolved action reopens inquiry if incorrectly closed.
    - No delete permission on ContactMessage — support audit trail.
    - ContactReply can be deleted by admin (corrections to replies).
"""

import logging

from django.contrib import admin, messages
from django.http import HttpRequest
from django.utils import timezone

from apps.contact.models import ContactMessage, ContactReply

logger = logging.getLogger("apps.contact")


class ContactReplyInline(admin.TabularInline):
    """
    Inline for viewing and adding replies within a ContactMessage.

    Staff can add new replies directly from the message detail page.
    replied_by is auto-set to request.user in save_formset().
    Existing replies are read-only — corrections require deletion
    and re-entry to preserve audit intent.
    """

    model       = ContactReply
    extra       = 1
    fields      = ["body", "sent_via_email", "replied_by", "created_at"]
    readonly_fields = ["replied_by", "created_at"]
    ordering    = ["created_at"]

    def get_readonly_fields(
        self,
        request: HttpRequest,
        obj: ContactMessage | None = None,
    ) -> list[str]:
        """
        Make all fields on existing replies readonly.

        Only the new (extra) reply form is editable.
        Existing replies are immutable conversation history.
        """
        return ["replied_by", "created_at"]


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """
    ContactMessage admin — full support queue management.

    List view sorted by unresolved first, then oldest first within
    unresolved — implements FIFO support queue ordering.

    Actions:
        mark_resolved   — close inquiry, set resolved_by and resolved_at.
        mark_unresolved — reopen incorrectly closed inquiry.
    """

    list_display = [
        "id",
        "name",
        "email",
        "subject_truncated",
        "is_resolved",
        "resolved_by",
        "created_at",
        "resolved_at",
    ]
    list_filter  = [
        "is_resolved",
        "created_at",
    ]
    search_fields = [
        "name",
        "email",
        "subject",
        "message",
        "user__email",
    ]
    ordering = [
        "is_resolved",   # Unresolved (False=0) sorts before resolved (True=1)
        "created_at",    # Oldest first within each group
    ]
    readonly_fields = [
        "user",
        "name",
        "email",
        "phone",
        "subject",
        "message",
        "created_at",
        "updated_at",
    ]
    fieldsets = [
        (
            "Customer Inquiry",
            {
                "fields": [
                    "user",
                    "name",
                    "email",
                    "phone",
                    "subject",
                    "message",
                    "created_at",
                    "updated_at",
                ]
            },
        ),
        (
            "Resolution",
            {
                "fields": [
                    "is_resolved",
                    "resolved_by",
                    "resolved_at",
                ]
            },
        ),
    ]
    inlines = [ContactReplyInline]
    actions = ["mark_resolved", "mark_unresolved"]

    def has_add_permission(self, request: HttpRequest) -> bool:
        """
        Prevent manual creation from admin.

        ContactMessages are created only via the customer-facing
        POST /api/contact/ endpoint.
        """
        return False

    def has_delete_permission(
        self,
        request: HttpRequest,
        obj: ContactMessage | None = None,
    ) -> bool:
        """
        Prevent deletion — support audit trail must be preserved.

        Mark resolved instead of deleting.
        """
        return False

    def save_formset(
        self,
        request: HttpRequest,
        form,
        formset,
        change: bool,
    ) -> None:
        """
        Auto-set replied_by to request.user on new ContactReply records.

        Called by Django admin when the inline formset is saved.
        Only sets replied_by on new instances (not pk yet assigned).
        """
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, ContactReply) and not instance.pk:
                instance.replied_by = request.user
            instance.save()
        formset.save_m2m()

        logger.info(
            "ContactMessageAdmin.save_formset: replies saved | "
            "message_id=%s admin=%s reply_count=%d",
            form.instance.pk,
            request.user.email,
            len(instances),
        )

    def subject_truncated(self, obj: ContactMessage) -> str:
        """Return truncated subject for list display readability."""
        return obj.subject[:60] + "..." if len(obj.subject) > 60 else obj.subject

    subject_truncated.short_description = "Subject"  # type: ignore[attr-defined]

    # ── Admin actions ──────────────────────────────────────────────────────

    @admin.action(description="✅ Mark selected inquiries as resolved")
    def mark_resolved(
        self,
        request: HttpRequest,
        queryset,
    ) -> None:
        """
        Mark selected ContactMessages as resolved.

        Sets is_resolved=True and resolved_by=request.user.
        ContactMessage.save() auto-sets resolved_at via its
        save() override when is_resolved transitions to True.
        Skips already-resolved messages with a warning.
        """
        success = 0
        skipped = 0

        for message in queryset:
            if message.is_resolved:
                skipped += 1
                continue

            message.is_resolved = True
            message.resolved_by = request.user
            message.save(update_fields=[
                "is_resolved",
                "resolved_by",
                "resolved_at",
            ])
            success += 1

            logger.info(
                "ContactMessageAdmin.mark_resolved: resolved | "
                "message_id=%s admin=%s",
                message.pk,
                request.user.email,
            )

        if success:
            self.message_user(
                request,
                f"{success} inquiry/inquiries marked as resolved.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} inquiry/inquiries were already resolved — skipped.",
                level=messages.WARNING,
            )

    @admin.action(description="🔄 Mark selected inquiries as unresolved")
    def mark_unresolved(
        self,
        request: HttpRequest,
        queryset,
    ) -> None:
        """
        Reopen selected ContactMessages.

        Sets is_resolved=False and clears resolved_by.
        ContactMessage.save() auto-clears resolved_at when
        is_resolved is False via its save() override.
        Skips already-unresolved messages with a warning.
        """
        success = 0
        skipped = 0

        for message in queryset:
            if not message.is_resolved:
                skipped += 1
                continue

            message.is_resolved = False
            message.resolved_by = None
            message.save(update_fields=[
                "is_resolved",
                "resolved_by",
                "resolved_at",
            ])
            success += 1

            logger.info(
                "ContactMessageAdmin.mark_unresolved: reopened | "
                "message_id=%s admin=%s",
                message.pk,
                request.user.email,
            )

        if success:
            self.message_user(
                request,
                f"{success} inquiry/inquiries reopened.",
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                f"{skipped} inquiry/inquiries were already unresolved — skipped.",
                level=messages.WARNING,
            )


@admin.register(ContactReply)
class ContactReplyAdmin(admin.ModelAdmin):
    """
    ContactReply admin — standalone view of all replies.

    Primarily used for audit — staff can see all replies sent
    across all inquiries. Replies are managed via the inline
    on ContactMessageAdmin but visible here for search and audit.
    """

    list_display = [
        "id",
        "message_email",
        "replied_by",
        "sent_via_email",
        "body_truncated",
        "created_at",
    ]
    list_filter  = [
        "sent_via_email",
        "created_at",
    ]
    search_fields = [
        "message__email",
        "message__subject",
        "replied_by__email",
        "body",
    ]
    ordering      = ["-created_at"]
    readonly_fields = [
        "message",
        "replied_by",
        "created_at",
        "updated_at",
    ]

    def message_email(self, obj: ContactReply) -> str:
        """Return customer email the reply was sent to."""
        return obj.message.email

    message_email.short_description = "Customer Email"  # type: ignore[attr-defined]

    def body_truncated(self, obj: ContactReply) -> str:
        """Return truncated reply body for list readability."""
        return obj.body[:80] + "..." if len(obj.body) > 80 else obj.body

    body_truncated.short_description = "Reply Body"  # type: ignore[attr-defined]