from __future__ import annotations

import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.password_validation import validate_password as django_validate_password


def validate_email_unique(email: str, exclude_user_id: int | None = None) -> str:
    """
    Validate email is unique across the system.
    Pass exclude_user_id when updating existing user.
    """
    from .models import User
    email = email.lower().strip()
    qs = User.objects.filter(email=email)
    if exclude_user_id:
        qs = qs.exclude(id=exclude_user_id)
    if qs.exists():
        raise ValidationError(
            _("An account with this email already exists.")
        )
    return email


def validate_full_name(value: str) -> str:
    """
    Full name must have at least two words.
    Strips extra whitespace.
    """
    name = " ".join(value.strip().split())
    if len(name.split()) < 2:
        raise ValidationError(
            _("Please enter your full name (first and last name).")
        )
    return name


def validate_strong_password(value: str) -> str:
    """
    Runs Django's built-in password validators.
    Centralizes password strength checking.
    """
    django_validate_password(value)
    return value


def validate_passwords_match(password: str, confirm_password: str) -> None:
    """
    Raises ValidationError if passwords don't match.
    Used in register and reset confirm serializers.
    """
    if password != confirm_password:
        raise ValidationError(
            {"confirm_password": _("Passwords do not match.")}
        )


def validate_pakistani_phone(value: str) -> str:
    """
    Validates Pakistani phone number format.
    Accepts: +923001234567 or 03001234567
    Centralizes phone validation — used in profile serializer and model.
    """
    pattern = r"^\+?92\d{10}$|^0\d{10}$"
    value = value.strip()
    if value and not re.match(pattern, value):
        raise ValidationError(
            _(
                "Enter a valid Pakistani phone number. "
                "Format: +923001234567 or 03001234567"
            )
        )
    return value


def validate_image_file(value) -> object:
    """
    Validates uploaded image — size and type.
    Used in AvatarUploadSerializer and anywhere else images are uploaded.
    """
    max_size = 2 * 1024 * 1024  # 2MB
    allowed_types = ["image/jpeg", "image/png", "image/webp"]

    if value.size > max_size:
        raise ValidationError(_("Image size must not exceed 2MB."))

    if hasattr(value, "content_type") and value.content_type not in allowed_types:
        raise ValidationError(
            _("Only JPEG, PNG and WebP images are allowed.")
        )
    return value