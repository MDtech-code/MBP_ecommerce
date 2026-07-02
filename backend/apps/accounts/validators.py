# apps/accounts/validators.py
from __future__ import annotations

import re

from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _


def validate_email_unique(email: str, exclude_user_id: int | None = None) -> str:
    """
    Validate that email is unique across the system.

    Normalizes to lowercase before checking.
    Pass ``exclude_user_id`` when validating during profile update
    to avoid false positives on the existing user's own email.

    Args:
        email: Raw email string from input.
        exclude_user_id: Optional user PK to exclude from uniqueness check.

    Returns:
        Normalized (lowercase, stripped) email string.

    Raises:
        ValidationError: If email is already registered.
    """
    from .models import User

    email = email.lower().strip()
    qs = User.objects.filter(email=email)
    if exclude_user_id:
        qs = qs.exclude(id=exclude_user_id)
    if qs.exists():
        raise ValidationError(_("An account with this email already exists."))
    return email


def validate_full_name(value: str) -> str:
    """
    Validate that full name contains at least two words.

    Strips and normalizes internal whitespace before checking.

    Args:
        value: Raw full name string from input.

    Returns:
        Cleaned, whitespace-normalized full name.

    Raises:
        ValidationError: If fewer than two words are provided.
    """
    name = " ".join(value.strip().split())
    if len(name.split()) < 2:
        raise ValidationError(
            _("Please enter your full name (first and last name).")
        )
    return name


def validate_strong_password(value: str) -> str:
    """
    Run Django's built-in password validators against the given value.

    Centralizes password strength checking so all serializers
    use the same validation chain defined in ``AUTH_PASSWORD_VALIDATORS``.

    Args:
        value: Plain-text password from input.

    Returns:
        The original value if all validators pass.

    Raises:
        ValidationError: If any configured password validator fails.
    """
    django_validate_password(value)
    return value


def validate_passwords_match(password: str, confirm_password: str) -> None:
    """
    Assert that two password strings are identical.

    Intentionally raises a plain ``ValidationError`` with a string message —
    NOT a dict. The calling serializer is responsible for mapping this
    onto the correct field key (e.g. ``confirm_password``).

    Args:
        password: The primary password value.
        confirm_password: The confirmation password value.

    Raises:
        ValidationError: If the two values do not match.
    """
    if password != confirm_password:
        raise ValidationError(_("Passwords do not match."))


def validate_pakistani_phone(value: str) -> str:
    """
    Validate Pakistani phone number format.

    Accepts:
        - International format: ``+923001234567``
        - Local format:         ``03001234567``

    Args:
        value: Raw phone number string from input.

    Returns:
        Stripped phone number string if valid.

    Raises:
        ValidationError: If the format does not match.
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


def validate_image_file(value: UploadedFile) -> UploadedFile:
    """
    Validate an uploaded image file for size and MIME type.

    Limits:
        - Maximum size: 2 MB
        - Allowed types: JPEG, PNG, WebP

    Args:
        value: The uploaded file object from a DRF ``ImageField``.

    Returns:
        The original file object if all checks pass.

    Raises:
        ValidationError: If size exceeds limit or MIME type is not allowed.
    """
    max_size = 2 * 1024 * 1024  # 2 MB
    allowed_types = ["image/jpeg", "image/png", "image/webp"]

    if value.size > max_size:
        raise ValidationError(_("Image size must not exceed 2MB."))

    if hasattr(value, "content_type") and value.content_type not in allowed_types:
        raise ValidationError(_("Only JPEG, PNG and WebP images are allowed."))

    return value
# from __future__ import annotations

# import re
# from django.core.exceptions import ValidationError
# from django.utils.translation import gettext_lazy as _
# from django.contrib.auth.password_validation import validate_password as django_validate_password


# def validate_email_unique(email: str, exclude_user_id: int | None = None) -> str:
#     """
#     Validate that email is unique across the system.

#     Normalizes to lowercase before checking.
#     Pass ``exclude_user_id`` when validating during profile update
#     to avoid false positives on the existing user's own email.

#     Args:
#         email: Raw email string from input.
#         exclude_user_id: Optional user PK to exclude from uniqueness check.

#     Returns:
#         Normalized (lowercase, stripped) email string.

#     Raises:
#         ValidationError: If email is already registered.
#     """
#     from .models import User

#     email = email.lower().strip()
#     qs = User.objects.filter(email=email)
#     if exclude_user_id:
#         qs = qs.exclude(id=exclude_user_id)
#     if qs.exists():
#         raise ValidationError(_("An account with this email already exists."))
#     return email

# # def validate_email_unique(email: str, exclude_user_id: int | None = None) -> str:
# #     """
# #     Validate email is unique across the system.
# #     Pass exclude_user_id when updating existing user.
# #     """
# #     from .models import User
# #     email = email.lower().strip()
# #     qs = User.objects.filter(email=email)
# #     if exclude_user_id:
# #         qs = qs.exclude(id=exclude_user_id)
# #     if qs.exists():
# #         raise ValidationError(
# #             _("An account with this email already exists.")
# #         )
# #     return email


# def validate_full_name(value: str) -> str:
#     """
#     Validate that full name contains at least two words.

#     Strips and normalizes internal whitespace before checking.

#     Args:
#         value: Raw full name string from input.

#     Returns:
#         Cleaned, whitespace-normalized full name.

#     Raises:
#         ValidationError: If fewer than two words are provided.
#     """
#     name = " ".join(value.strip().split())
#     if len(name.split()) < 2:
#         raise ValidationError(
#             _("Please enter your full name (first and last name).")
#         )
#     return name

# def validate_strong_password(value: str) -> str:
#     """
#     Run Django's built-in password validators against the given value.

#     Centralizes password strength checking so all serializers
#     use the same validation chain defined in ``AUTH_PASSWORD_VALIDATORS``.

#     Args:
#         value: Plain-text password from input.

#     Returns:
#         The original value if all validators pass.

#     Raises:
#         ValidationError: If any configured password validator fails.
#     """
#     django_validate_password(value)
#     return value
# # def validate_strong_password(value: str) -> str:
# #     """
# #     Runs Django's built-in password validators.
# #     Centralizes password strength checking.
# #     """
# #     django_validate_password(value)
# #     return value

# def validate_passwords_match(password: str, confirm_password: str) -> None:
#     """
#     Assert that two password strings are identical.

#     Intentionally raises a plain ``ValidationError`` with a string message —
#     NOT a dict. The calling serializer is responsible for mapping this
#     onto the correct field key (e.g. ``confirm_password``).

#     Args:
#         password: The primary password value.
#         confirm_password: The confirmation password value.

#     Raises:
#         ValidationError: If the two values do not match.
#     """
#     if password != confirm_password:
#         raise ValidationError(_("Passwords do not match."))

# # def validate_passwords_match(password: str, confirm_password: str) -> None:
# #     """
# #     Raises ValidationError if passwords don't match.
# #     Used in register and reset confirm serializers.
# #     """
# #     if password != confirm_password:
# #         raise ValidationError(
# #             {"confirm_password": _("Passwords do not match.")}
# #         )


# def validate_pakistani_phone(value: str) -> str:
#     """
#     Validates Pakistani phone number format.
#     Accepts: +923001234567 or 03001234567
#     Centralizes phone validation — used in profile serializer and model.
#     """
#     pattern = r"^\+?92\d{10}$|^0\d{10}$"
#     value = value.strip()
#     if value and not re.match(pattern, value):
#         raise ValidationError(
#             _(
#                 "Enter a valid Pakistani phone number. "
#                 "Format: +923001234567 or 03001234567"
#             )
#         )
#     return value


# def validate_image_file(value) -> object:
#     """
#     Validates uploaded image — size and type.
#     Used in AvatarUploadSerializer and anywhere else images are uploaded.
#     """
#     max_size = 2 * 1024 * 1024  # 2MB
#     allowed_types = ["image/jpeg", "image/png", "image/webp"]

#     if value.size > max_size:
#         raise ValidationError(_("Image size must not exceed 2MB."))

#     if hasattr(value, "content_type") and value.content_type not in allowed_types:
#         raise ValidationError(
#             _("Only JPEG, PNG and WebP images are allowed.")
#         )
#     return value