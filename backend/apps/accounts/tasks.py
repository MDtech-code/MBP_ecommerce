from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger("apps.accounts")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, user_id: int, token: str) -> None:
    """Send email verification link to user."""
    from .models import User
    try:
        user = User.objects.get(id=user_id)
        verification_url = (
            f"{settings.FRONTEND_URL}/verify-email?token={token}"
        )
        subject = "Verify your MBP Store email address"
        message = (
            f"Hi {user.short_name},\n\n"
            f"Please verify your email by clicking the link below:\n"
            f"{verification_url}\n\n"
            f"This link expires in 24 hours.\n\n"
            f"If you did not create an account, ignore this email.\n\n"
            f"MBP Store Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Verification email sent to: %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found for verification email", user_id)
    except Exception as exc:
        logger.error("Failed to send verification email: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_id: int, token: str) -> None:
    """Send password reset link to user."""
    from .models import User
    try:
        user = User.objects.get(id=user_id)
        reset_url = (
            f"{settings.FRONTEND_URL}/reset-password?token={token}"
        )
        subject = "Reset your MBP Store password"
        message = (
            f"Hi {user.short_name},\n\n"
            f"You requested a password reset. Click the link below:\n"
            f"{reset_url}\n\n"
            f"This link expires in 1 hour.\n\n"
            f"If you did not request this, ignore this email.\n\n"
            f"MBP Store Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Password reset email sent to: %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found for password reset email", user_id)
    except Exception as exc:
        logger.error("Failed to send password reset email: %s", exc)
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id: int) -> None:
    """Send welcome email after email is verified."""
    from .models import User
    try:
        user = User.objects.get(id=user_id)
        subject = "Welcome to MBP Store!"
        message = (
            f"Hi {user.short_name},\n\n"
            f"Your email has been verified. Welcome to MBP Store!\n\n"
            f"You can now browse and purchase motorbike parts.\n\n"
            f"MBP Store Team"
        )
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info("Welcome email sent to: %s", user.email)

    except User.DoesNotExist:
        logger.error("User %s not found for welcome email", user_id)
    except Exception as exc:
        logger.error("Failed to send welcome email: %s", exc)
        raise self.retry(exc=exc)