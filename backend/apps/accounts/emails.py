# apps/accounts/emails.py
from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def _base_context() -> dict:
    """
    Build the shared context injected into every email template.

    Every template receives:
        brand_name    — from settings.BRAND_NAME
        support_email — from settings.SUPPORT_EMAIL
        current_year  — for footer copyright
        shop_url      — homepage link used in welcome email CTA

    Centralised here so adding a new global variable means
    one change.
    """
    return {
        "brand_name":    settings.BRAND_NAME,
        "support_email": settings.SUPPORT_EMAIL,
        "current_year":  datetime.now().year,
        "shop_url":      settings.FRONTEND_URL,
    }


def _render_plain_text(html_content: str) -> str:
   
    import re
    # Remove style blocks entirely — CSS has no place in plain text
    text = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL)
    # Replace block-level tags with newlines for readability
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</(p|div|h1|h2|h3|li|tr)>', '\n', text)
    # Strip remaining tags
    text = re.sub(r'<[^>]+>', '', text)
    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def send_email(
    *,
    subject: str,
    template_name: str,
    context: dict,
    recipient: str,
) -> None:
    """
    Render an HTML email template and send it with a plain-text alternative.

    This is the single sending function used by every task in tasks.py.
    No task should call send_mail or EmailMultiAlternatives directly —
    all sending goes through here.

    Args:
        subject:       Email subject line.
        template_name: Path relative to templates/ e.g. "emails/verify_email.html"
        context:       Template-specific variables. Base context is merged in
                       automatically — do not pass brand_name etc. manually.
        recipient:     Single recipient email address string.

    Raises:
        Exception: Re-raised after logging so the calling Celery task
                   can handle retry logic itself.
    """
    
    full_context = {**_base_context(), **context}

    html_content  = render_to_string(template_name, full_context)
    plain_content = _render_plain_text(html_content)

    email = EmailMultiAlternatives(
        subject      = subject,
        body         = plain_content,
        from_email   = settings.DEFAULT_FROM_EMAIL,
        to           = [recipient],
    )
    email.attach_alternative(html_content, "text/html")
    email.send(fail_silently=False)