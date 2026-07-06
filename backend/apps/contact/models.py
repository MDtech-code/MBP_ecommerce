from __future__ import annotations

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel


class ContactMessage(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contact_messages",
        verbose_name=_("authenticated user"),
    )
    name = models.CharField(_("sender name"), max_length=100)
    email = models.EmailField(_("reply-to email address"))
    phone = models.CharField(_("contact number"), max_length=15, blank=True, default="")
    subject = models.CharField(_("subject title"), max_length=200)
    message = models.TextField(_("message contents"))
    
    # Verification/Admin Workflows
    is_resolved = models.BooleanField(_("resolved status"), default=False)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resolved_tickets",
        verbose_name=_("resolved by admin"),
    )
    resolved_at = models.DateTimeField(_("resolved timestamp"), null=True, blank=True)

    class Meta:
        verbose_name = _("contact inquiry")
        verbose_name_plural = _("contact inquiries")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Inquiry from {self.email} — {self.subject[:30]}"