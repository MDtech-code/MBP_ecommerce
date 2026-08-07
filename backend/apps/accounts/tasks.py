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
    



# apps/accounts/tasks.py — add this task

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_security_otp_task(self, user_id: int, otp_code: str, purpose: str,recipient_email: str | None = None, ) -> None:
    print("recipt wala hu yar @@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
    """
    Send 6-digit security OTP to user's current email address.

    Args:
        user_id:  PK of the User.
        otp_code: Plain-text 6-digit OTP (never stored — only in transit here).
        purpose:  SecurityPurpose string for subject line context.
    """
    from .models import User

    PURPOSE_LABELS = {
        "change_email":    "Email Change",
        "change_password": "Password Change",
        "delete_account":  "Account Deletion",
    }

    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning(
            "Security OTP task skipped — user not found",
            extra={"user_id": user_id},
        )
        return

    purpose_label = PURPOSE_LABELS.get(purpose, "Security Verification")

    subject = f"Your BikeExpress verification code — {purpose_label}"
    message = (
        f"Hi {user.short_name},\n\n"
        f"Your verification code for {purpose_label} is:\n\n"
        f"    {otp_code}\n\n"
        f"This code expires in 10 minutes.\n"
        f"Do not share this code with anyone.\n\n"
        f"If you did not request this, please contact support immediately.\n\n"
        f"BikeExpress Security Team"
    )

    try:
        # print("Enter in a task ",user_id,otp_code,purpose)
        send_mail(
            subject      = subject,
            message      = message,
            from_email   = settings.DEFAULT_FROM_EMAIL,
            recipient_list = [recipient_email or user.email],
            fail_silently  = False,
        )
        logger.info(
            "Security OTP email sent",
            extra={"user_id": user.id, "purpose": purpose},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send security OTP email — will retry",
            extra={"user_id": user.id, "purpose": purpose},
        )
        raise self.retry(exc=exc)





@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_change_verification_task(
    self,
    user_id: int,
    new_email: str,
    token: str,
) -> None:
    """
    Send email change verification link to the NEW email address.

    Args:
        user_id:   PK of the User requesting email change.
        new_email: The new email address to send verification to.
        token:     UUID string of the PendingEmailChange token.

    Retry:
        Up to 3 times with 60-second delay on unexpected failures.
    """
    from .models import User

    try:
        print("user ka pata kar ra ha ")
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning(
            "Email change verification skipped — user not found",
            extra={"user_id": user_id},
        )
        return

    confirm_url = f"{settings.FRONTEND_URL}/update-email/confirm?token={token}"

    subject = "Verify your new MBP Store email address"
    message = (
        f"Hi {user.short_name},\n\n"
        f"You requested to change your email address.\n\n"
        f"Click the link below to verify your new email:\n"
        f"{confirm_url}\n\n"
        f"This link expires in 24 hours.\n\n"
        f"If you did not request this change, please contact us immediately at "
        f"{settings.DEFAULT_FROM_EMAIL}\n\n"
        f"MBP Store Team"
    )

    try:
        print("ab send kar ra ha ")
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[new_email],
            fail_silently=False,
        )
        logger.info(
            "Email change verification sent successfully",
            extra={"user_id": user_id, "new_email": new_email},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send email change verification — will retry",
            extra={"user_id": user_id, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)


# ─── Send Email Change Security Notification ───────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_change_notification_task(
    self,
    user_id: int,
    old_email: str,
    user_name: str,
) -> None:
    """
    Send security notification to the OLD email address.

    Why pass old_email and user_name directly?
        By the time this task runs, user.email may already be updated.
        Passing them directly guarantees correct values regardless
        of when the worker picks up the task.

    Args:
        user_id:   PK of the User (for logging only).
        old_email: Old email address to send notification to.
        user_name: User's short name collected before change.

    Retry:
        Up to 3 times with 60-second delay on unexpected failures.
    """
    subject = "Security notice — email address changed on your MBP Store account"
    message = (
        f"Hi {user_name},\n\n"
        f"This is a security notification to let you know that "
        f"the email address on your MBP Store account has been changed.\n\n"
        f"If you made this change, you can safely ignore this email.\n\n"
        f"If you did NOT make this change, your account may be compromised.\n"
        f"Please contact us immediately at: {settings.DEFAULT_FROM_EMAIL}\n\n"
        f"MBP Store Team"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[old_email],
            fail_silently=False,
        )
        logger.info(
            "Email change security notification sent successfully",
            extra={"user_id": user_id, "old_email": old_email},
        )
    except Exception as exc:
        logger.exception(
            "Failed to send email change security notification — will retry",
            extra={"user_id": user_id, "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)
    





# apps/accounts/tasks.py — add this task

# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
# def send_security_otp_task(self, user_id: int, otp_code: str, purpose: str) -> None:
#     """
#     Send 6-digit security OTP to user's current email address.

#     Args:
#         user_id:  PK of the User.
#         otp_code: Plain-text 6-digit OTP (never stored — only in transit here).
#         purpose:  SecurityPurpose string for subject line context.
#     """
#     from .models import User

#     PURPOSE_LABELS = {
#         "change_email":    "Email Change",
#         "change_password": "Password Change",
#         "delete_account":  "Account Deletion",
#     }

#     try:
#         user = User.objects.get(id=user_id)
#     except User.DoesNotExist:
#         logger.warning(
#             "Security OTP task skipped — user not found",
#             extra={"user_id": user_id},
#         )
#         return

#     purpose_label = PURPOSE_LABELS.get(purpose, "Security Verification")

#     subject = f"Your BikeExpress verification code — {purpose_label}"
#     message = (
#         f"Hi {user.short_name},\n\n"
#         f"Your verification code for {purpose_label} is:\n\n"
#         f"    {otp_code}\n\n"
#         f"This code expires in 10 minutes.\n"
#         f"Do not share this code with anyone.\n\n"
#         f"If you did not request this, please contact support immediately.\n\n"
#         f"BikeExpress Security Team"
#     )

#     try:
#         send_mail(
#             subject      = subject,
#             message      = message,
#             from_email   = settings.DEFAULT_FROM_EMAIL,
#             recipient_list = [user.email],
#             fail_silently  = False,
#         )
#         logger.info(
#             "Security OTP email sent",
#             extra={"user_id": user.id, "purpose": purpose},
#         )
#     except Exception as exc:
#         logger.exception(
#             "Failed to send security OTP email — will retry",
#             extra={"user_id": user.id, "purpose": purpose},
#         )
#         raise self.retry(exc=exc)