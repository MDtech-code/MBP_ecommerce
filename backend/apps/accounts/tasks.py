# apps/accounts/tasks.py
from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger("apps.accounts")


# ─── Send Verification Email ──────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_verification_email_task(self, user_id: int, token: str) -> None:
    """
    Send an email verification link to a newly registered user.

    Args:
        user_id: PK of the ``User`` to send to.
        token:   UUID string of the ``EmailVerificationToken``.

    Retry:
        Up to 3 times with 60-second delay on unexpected failures.
        No retry if user is not found — that is a permanent condition.
    """
    from .models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # User was deleted between task creation and execution.
        # Permanent failure — do not retry.
        logger.warning(
            "Verification email skipped — user not found",
            extra={"user_id": user_id},
        )
        return

    verification_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"

    subject = "Verify your MBP Store email address"
    message = (
        f"Hi {user.short_name},\n\n"
        f"Please verify your email by clicking the link below:\n"
        f"{verification_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not create an account, you can safely ignore this email.\n\n"
        f"MBP Store Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(
            "Verification email sent successfully",
            extra={"user_id": user.id},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send verification email — will retry",
            extra={"user_id": user.id, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)


# ─── Send Password Reset Email ────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_password_reset_email_task(self, user_id: int, token: str) -> None:
    """
    Send a password reset link to the requesting user.

    Args:
        user_id: PK of the ``User`` requesting the reset.
        token:   UUID string of the ``PasswordResetToken``.

    Retry:
        Up to 3 times with 60-second delay on unexpected failures.
        No retry if user is not found — that is a permanent condition.
    """
    from .models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # User was deleted between task creation and execution.
        # Permanent failure — do not retry.
        logger.warning(
            "Password reset email skipped — user not found",
            extra={"user_id": user_id},
        )
        return

    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"

    subject = "Reset your MBP Store password"
    message = (
        f"Hi {user.short_name},\n\n"
        f"You requested a password reset. Click the link below:\n"
        f"{reset_url}\n\n"
        f"This link expires in 1 hour.\n\n"
        f"If you did not request this, you can safely ignore this email.\n\n"
        f"MBP Store Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(
            "Password reset email sent successfully",
            extra={"user_id": user.id},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send password reset email — will retry",
            extra={"user_id": user.id, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)


# ─── Send Welcome Email ───────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_welcome_email_task(self, user_id: int) -> None:
    """
    Send a welcome email after a user successfully verifies their email.

    Args:
        user_id: PK of the newly verified ``User``.

    Retry:
        Up to 3 times with 60-second delay on unexpected failures.
        No retry if user is not found — that is a permanent condition.
    """
    from .models import User

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        # User was deleted between task creation and execution.
        # Permanent failure — do not retry.
        logger.warning(
            "Welcome email skipped — user not found",
            extra={"user_id": user_id},
        )
        return

    subject = "Welcome to MBP Store!"
    message = (
        f"Hi {user.short_name},\n\n"
        f"Your email has been verified. Welcome to MBP Store!\n\n"
        f"You can now browse and purchase motorbike parts.\n\n"
        f"MBP Store Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(
            "Welcome email sent successfully",
            extra={"user_id": user.id},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send welcome email — will retry",
            extra={"user_id": user.id, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)



# ─── Send Goodbye Email ────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_goodbye_email_task(self, user_email: str, user_name: str) -> None:
    """
    Send a goodbye email after a user deletes their account.

    Why email and name instead of user_id?
        User is hard deleted before this task runs.
        A user_id lookup would always fail with DoesNotExist.
        Email and name are collected before deletion and passed directly.

    Args:
        user_email: Email address collected before deletion.
        user_name:  First name collected before deletion.

    Retry:
        Up to 3 times with 60-second delay on unexpected failures.
    """
    subject = "We are sad to see you go — MBP Store"
    message = (
        f"Hi {user_name},\n\n"
        f"Your MBP Store account has been successfully deleted.\n\n"
        f"We are truly sad to see you leave. 😔\n\n"
        f"You were part of our family and we genuinely valued "
        f"having you with us.\n\n"
        f"If this was a mistake or you change your mind, "
        f"you are always welcome back — just create a new account "
        f"and we will be here waiting.\n\n"
        f"If you deleted your account due to a bad experience, "
        f"we would love to hear from you so we can do better.\n"
        f"Contact us anytime at: {settings.SUPPORT_EMAIL}\n\n"
        f"We hope to see you again someday. 🙏\n\n"
        f"With warm regards,\n"
        f"The MBP Store Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user_email],
            fail_silently=False,
        )
        logger.info(
            "Goodbye email sent successfully",
            extra={"email": user_email},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send goodbye email — will retry",
            extra={"email": user_email, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)