# apps/contact/models.py
from __future__ import annotations
import logging

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.common.validators import phone_validator

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.contact")




class ContactMessage(TimeStampedModel):
    """
    Customer support inquiry submitted via contact form.

    Design decisions:
    - user SET_NULL — inquiry preserved after account deletion.
    - resolved_at auto-set in save() when is_resolved becomes True.
    - Reply history tracked in ContactReply.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
        verbose_name=_("authenticated user"),
    )
    name = models.CharField(_("sender name"), max_length=100)
    email = models.EmailField(_("reply-to email"))
    phone = models.CharField(
        _("contact number"),
        max_length=15,
        blank=True,
        default="",
        validators=[phone_validator],
    )
    subject = models.CharField(_("subject"), max_length=200)
    message = models.TextField(_("message"))
    is_resolved = models.BooleanField(
        _("resolved"),
        default=False,
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_tickets",
        verbose_name=_("resolved by"),
    )
    resolved_at = models.DateTimeField(
        _("resolved at"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name        = _("contact inquiry")
        verbose_name_plural = _("contact inquiries")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["is_resolved", "created_at"]),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.is_resolved and self.resolved_at is None:
            self.resolved_at = timezone.now()
        if not self.is_resolved:
            self.resolved_at = None
        super().save(*args, **kwargs)
        logger.debug(
            "ContactMessage saved: email=%s resolved=%s",
            self.email,
            self.is_resolved,
        )

    def __str__(self) -> str:
        return f"Inquiry from {self.email} — {self.subject[:30]}"


class ContactReply(TimeStampedModel):
    """
    Admin reply to a contact inquiry.
    Tracks full conversation thread for each inquiry.
    """

    message = models.ForeignKey(
        ContactMessage,
        on_delete=models.CASCADE,
        related_name='replies',
        verbose_name=_('contact message'),
    )
    replied_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contact_replies',
        verbose_name=_('replied by'),
    )
    body = models.TextField(_('reply body'))
    sent_via_email = models.BooleanField(
        _('sent via email'),
        default=True,
        help_text=_('True if this reply was emailed to the customer.'),
    )

    class Meta:
        verbose_name        = _('contact reply')
        verbose_name_plural = _('contact replies')
        ordering            = ['created_at']

    def __str__(self) -> str:
        return (
            f"Reply to {self.message.email} "
            f"by {getattr(self.replied_by, 'email', 'system')}"
        )
