# apps/accounts/validators.py
from __future__ import annotations

import re
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _


from apps.core.error_codes import ErrorCode

def validate_email_format(email: str) -> str:
    """
    Responsibilities:
    - Strip whitespace
    - Lowercase normalize
    - Basic format check
    
    Args:
        email: Raw email string from input.
        
    Returns:
        Normalized (lowercase, stripped) email string.
        
    Raises:
        ValidationError: If email FORMAT is invalid.
    """
    

    email = email.lower().strip()
    

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        raise ValidationError(
            _("Enter a valid email address."),
            code=ErrorCode.EMAIL_INVALID_FORMAT,
        )
    
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
            _("Please enter your full name (first and last name)."),
            code=ErrorCode.INVALID_FULL_NAME,
        )
    return name


def validate_strong_password(value: str) -> str:
    """
    Run Django's built-in password validators against the given value.

    Centralizes password strength checking so all serializers
    use the same validation chain defined in ``AUTH_PASSWORD_VALIDATORS``.

    Django's validate_password raises django.core.exceptions.ValidationError
    with its own messages. We catch it and re-raise with our code so the
    frontend receives a consistent machine-readable code regardless of which
    specific Django validator triggered the failure.

    Args:
        value: Plain-text password from input.

    Returns:
        The original value if all validators pass.

    Raises:
        ValidationError: If any configured password validator fails.
    """
    try:
        django_validate_password(value)
    except ValidationError as exc:
        # Django may raise multiple messages — we preserve them all
        # but attach our unified code so frontend knows the category.
        raise ValidationError(
            exc.messages,
            code=ErrorCode.PASSWORD_TOO_WEAK,
        )
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
        raise ValidationError(
            _("Passwords do not match."),
            code=ErrorCode.PASSWORD_MISMATCH,
        )


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
            ),
            code=ErrorCode.INVALID_PHONE,
        )
    return value
from django.core.exceptions import ValidationError
from apps.accounts.models import UserProfile

def ensure_phone_uniqueness(phone: str, instance=None) -> str:
    """
    Ensure the given phone number is unique in Profile.

    Args:
        phone: Phone number string from validated data.
        instance: Optional Profile instance being updated.

    Returns:
        The phone number string if unique.

    Raises:
        ValidationError: If the phone number already exists.
    """
    qs = UserProfile.objects.filter(phone=phone)
    print(qs)
    if instance:
        print('ha instance be hu')
        qs = qs.exclude(pk=instance.pk)
    if qs.exists():
        raise ValidationError("This phone number is already in use.")
    return phone


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
        raise ValidationError(
            _("Image size must not exceed 2MB."),
            code=ErrorCode.INVALID_IMAGE_SIZE,
        )

    if hasattr(value, "content_type") and value.content_type not in allowed_types:
        raise ValidationError(
            _("Only JPEG, PNG and WebP images are allowed."),
            code=ErrorCode.INVALID_IMAGE_TYPE,
        )

    return value
