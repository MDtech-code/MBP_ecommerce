# apps/accounts/tests/unit/test_validators.py
"""
Unit tests for apps.accounts.validators.

Validators are pure functions — no DB, no HTTP.
They are the fastest tests in the suite.

All validators are called by serializers. Testing them in isolation:
    1. Pinpoints failures to the validator not the serializer
    2. Tests edge cases without full HTTP overhead
    3. Serves as living documentation of validation rules

Validators covered:
    validate_email_unique       — uniqueness check against DB
    validate_full_name          — minimum two words
    validate_strong_password    — Django AUTH_PASSWORD_VALIDATORS chain
    validate_passwords_match    — equality check
    validate_pakistani_phone    — format: +923001234567 or 03001234567
    validate_image_file         — size ≤ 2MB, type in JPEG/PNG/WebP
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.validators import (
    validate_email_unique,
    validate_full_name,
    validate_image_file,
    validate_pakistani_phone,
    validate_passwords_match,
    validate_strong_password,
)
from apps.accounts.tests.conftest import STRONG_PASSWORD


# ─── validate_email_unique ────────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestValidateEmailUnique:
    """
    Tests for validate_email_unique().

    Queries the DB to check uniqueness.
    Normalizes to lowercase before checking.
    """

    def test_new_email_passes(self, db):
        """Email not in DB must pass without raising."""
        result = validate_email_unique("new@example.com")
        assert result == "new@example.com"

    def test_duplicate_email_raises(self, user):
        """Email already in DB must raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_email_unique(user.email)

    def test_email_normalized_before_check(self, user):
        """
        Uppercase version of existing email must also be caught.

        validate_email_unique normalizes to lowercase before querying.
        UPPER@TEST.COM must fail if upper@test.com exists.
        """
        with pytest.raises(ValidationError):
            validate_email_unique(user.email.upper())

    def test_returns_normalized_email(self, db):
        """Return value must be normalized (lowercase, stripped)."""
        result = validate_email_unique("  NEW@EXAMPLE.COM  ")
        assert result == "new@example.com"

    def test_exclude_user_id_allows_own_email(self, user):
        """
        Passing exclude_user_id must allow the user's own email.

        Used during profile update — user should not get uniqueness
        error when submitting their own unchanged email.
        """
        result = validate_email_unique(user.email, exclude_user_id=user.id)
        assert result == user.email

    def test_exclude_user_id_still_catches_others_email(self, user, db):
        """
        Excluding one user must still catch another user's email.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        other = User.objects.create_user(
            email="other@example.com",
            full_name="Other User",
            password=STRONG_PASSWORD,
        )
        with pytest.raises(ValidationError):
            validate_email_unique(other.email, exclude_user_id=user.id)


# ─── validate_full_name ───────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateFullName:
    """
    Tests for validate_full_name().

    Pure function — no DB needed.
    Requires at least two words (first + last name minimum).
    """

    def test_two_word_name_passes(self):
        """Standard first + last name must pass."""
        result = validate_full_name("John Doe")
        assert result == "John Doe"

    def test_three_word_name_passes(self):
        """Three-word names (common in Pakistan) must pass."""
        result = validate_full_name("Muhammad Ali Khan")
        assert result == "Muhammad Ali Khan"

    def test_single_word_name_raises(self):
        """Single word name must raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_full_name("John")

    def test_empty_string_raises(self):
        """Empty string must raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_full_name("")

    def test_whitespace_only_raises(self):
        """Whitespace-only string must raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_full_name("   ")

    def test_leading_trailing_whitespace_stripped(self):
        """Leading/trailing whitespace must be stripped from return value."""
        result = validate_full_name("  John Doe  ")
        assert result == "John Doe"

    def test_internal_whitespace_normalized(self):
        """
        Multiple internal spaces must be collapsed to single space.

        "John   Doe" → "John Doe"
        """
        result = validate_full_name("John   Doe")
        assert result == "John Doe"

    def test_returns_cleaned_name(self):
        """Return value must be the cleaned, normalized name string."""
        result = validate_full_name("  Jane   Smith  ")
        assert result == "Jane Smith"


# ─── validate_strong_password ────────────────────────────────────────────────

@pytest.mark.unit
@pytest.mark.django_db
class TestValidateStrongPassword:
    """
    Tests for validate_strong_password().

    Delegates to Django's AUTH_PASSWORD_VALIDATORS chain.
    Tests each validator's rejection case.
    """

    def test_strong_password_passes(self):
        """STRONG_PASSWORD constant must pass all validators."""
        result = validate_strong_password(STRONG_PASSWORD)
        assert result == STRONG_PASSWORD

    def test_too_short_password_raises(self):
        """Password shorter than 8 characters must raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_strong_password("Ab1!")

    def test_common_password_raises(self):
        """
        Common password must be rejected by CommonPasswordValidator.

        'password123' is in Django's common password list.
        """
        with pytest.raises(ValidationError):
            validate_strong_password("password123")

    def test_all_numeric_password_raises(self):
        """
        Fully numeric password must be rejected by NumericPasswordValidator.
        """
        with pytest.raises(ValidationError):
            validate_strong_password("12345678")

    def test_returns_original_value_on_success(self):
        """Valid password must be returned unchanged."""
        result = validate_strong_password(STRONG_PASSWORD)
        assert result == STRONG_PASSWORD


# ─── validate_passwords_match ─────────────────────────────────────────────────

@pytest.mark.unit
class TestValidatePasswordsMatch:
    """
    Tests for validate_passwords_match().

    Pure function — no DB needed.
    Raises plain ValidationError (not dict) — caller maps to field.
    """

    def test_matching_passwords_pass(self):
        """Identical passwords must not raise."""
        try:
            validate_passwords_match(STRONG_PASSWORD, STRONG_PASSWORD)
        except ValidationError:
            pytest.fail(
                "validate_passwords_match raised for identical passwords"
            )

    def test_mismatched_passwords_raise(self):
        """Different passwords must raise ValidationError."""
        with pytest.raises(ValidationError):
            validate_passwords_match(STRONG_PASSWORD, "DifferentPass!99")

    def test_empty_passwords_mismatch_raises(self):
        """Non-equal empty-ish strings must raise."""
        with pytest.raises(ValidationError):
            validate_passwords_match("", "notempty")

    def test_case_sensitive_mismatch_raises(self):
        """
        Password comparison must be case-sensitive.

        "Password" != "password" — must raise.
        """
        with pytest.raises(ValidationError):
            validate_passwords_match("Password123!", "password123!")

    def test_error_is_plain_string_message(self):
        """
        ValidationError must contain a plain string message — not a dict.

        Serializer maps this onto the correct field key.
        If it were a dict, the serializer mapping would double-wrap.
        """
        try:
            validate_passwords_match("abc", "xyz")
        except ValidationError as exc:
            from django.utils.functional import Promise
            assert isinstance(exc.message, (str, Promise))



# ─── validate_pakistani_phone ─────────────────────────────────────────────────

@pytest.mark.unit
class TestValidatePakistaniPhone:
    """
    Tests for validate_pakistani_phone().

    Pure function — no DB needed.
    Accepts: +923001234567 (international) or 03001234567 (local).
    Rejects: everything else.
    """

    # ── Valid formats ─────────────────────────────────────────────────────────

    def test_local_format_accepted(self):
        """03001234567 (local format) must be accepted."""
        result = validate_pakistani_phone("03001234567")
        assert result == "03001234567"

    def test_international_format_accepted(self):
        """+923001234567 (international format) must be accepted."""
        result = validate_pakistani_phone("+923001234567")
        assert result == "+923001234567"

    def test_empty_string_accepted(self):
        """
        Empty string must be accepted — phone is optional on profile.

        Validator is called when value is provided.
        Empty string = field cleared = acceptable.
        """
        result = validate_pakistani_phone("")
        assert result == ""

    def test_whitespace_stripped_before_validation(self):
        """Leading/trailing whitespace must be stripped."""
        result = validate_pakistani_phone("  03001234567  ")
        assert result == "03001234567"

    # ── Invalid formats ───────────────────────────────────────────────────────

    def test_too_short_raises(self):
        """Phone number shorter than expected must raise."""
        with pytest.raises(ValidationError):
            validate_pakistani_phone("12345")

    def test_no_country_code_non_zero_prefix_raises(self):
        """Number not starting with 0 or +92 must raise."""
        with pytest.raises(ValidationError):
            validate_pakistani_phone("13001234567")

    def test_international_wrong_country_raises(self):
        """International number with wrong country code must raise."""
        with pytest.raises(ValidationError):
            validate_pakistani_phone("+13001234567")

    def test_letters_in_number_raises(self):
        """Letters in phone number must raise."""
        with pytest.raises(ValidationError):
            validate_pakistani_phone("0300123456a")

    def test_too_long_raises(self):
        """Number longer than expected must raise."""
        with pytest.raises(ValidationError):
            validate_pakistani_phone("030012345678901")

    def test_returns_stripped_value(self):
        """Return value must be stripped of whitespace."""
        result = validate_pakistani_phone("  +923001234567  ")
        assert result == "+923001234567"


# ─── validate_image_file ──────────────────────────────────────────────────────

@pytest.mark.unit
class TestValidateImageFile:
    """
    Tests for validate_image_file().

    Pure function — no DB needed.
    Validates: size ≤ 2MB, content_type in JPEG/PNG/WebP.
    """

    def _make_file(
        self,
        name: str = "test.jpg",
        content: bytes = b"fake image content",
        content_type: str = "image/jpeg",
    ) -> SimpleUploadedFile:
        """Helper — create minimal in-memory uploaded file."""
        return SimpleUploadedFile(name, content, content_type=content_type)

    # ── Valid files ───────────────────────────────────────────────────────────

    def test_valid_jpeg_passes(self):
        """Small JPEG file must pass validation."""
        file = self._make_file(
            name="photo.jpg",
            content=b"x" * 100,
            content_type="image/jpeg",
        )
        result = validate_image_file(file)
        assert result is file

    def test_valid_png_passes(self):
        """Small PNG file must pass validation."""
        file = self._make_file(
            name="photo.png",
            content=b"x" * 100,
            content_type="image/png",
        )
        result = validate_image_file(file)
        assert result is file

    def test_valid_webp_passes(self):
        """Small WebP file must pass validation."""
        file = self._make_file(
            name="photo.webp",
            content=b"x" * 100,
            content_type="image/webp",
        )
        result = validate_image_file(file)
        assert result is file

    def test_returns_original_file_object(self):
        """Validator must return the original file object unchanged."""
        file = self._make_file()
        result = validate_image_file(file)
        assert result is file

    # ── Size validation ───────────────────────────────────────────────────────

    def test_file_exactly_2mb_passes(self):
        """File exactly at 2MB limit must pass."""
        file = self._make_file(content=b"x" * (2 * 1024 * 1024))
        result = validate_image_file(file)
        assert result is file

    def test_file_over_2mb_raises(self):
        """
        File exceeding 2MB must raise ValidationError.

        2MB + 1 byte triggers the size check.
        """
        file = self._make_file(content=b"x" * (2 * 1024 * 1024 + 1))
        with pytest.raises(ValidationError, match="2MB"):
            validate_image_file(file)

    # ── MIME type validation ──────────────────────────────────────────────────

    def test_pdf_raises(self):
        """PDF file must raise ValidationError."""
        file = self._make_file(
            name="doc.pdf",
            content_type="application/pdf",
        )
        with pytest.raises(ValidationError):
            validate_image_file(file)

    def test_gif_raises(self):
        """
        GIF file must raise ValidationError.

        GIF is not in allowed types — animated GIFs can be problematic
        for avatar display and storage.
        """
        file = self._make_file(
            name="anim.gif",
            content_type="image/gif",
        )
        with pytest.raises(ValidationError):
            validate_image_file(file)

    def test_text_file_raises(self):
        """Plain text file disguised as image must raise."""
        file = self._make_file(
            name="fake.jpg",
            content_type="text/plain",
        )
        with pytest.raises(ValidationError):
            validate_image_file(file)

    def test_error_message_mentions_allowed_types(self):
        """
        ValidationError message must mention allowed types.

        Helps developers and users understand what is accepted.
        """
        file = self._make_file(content_type="application/pdf")
        try:
            validate_image_file(file)
        except ValidationError as exc:
            error_text = str(exc.message).lower()
            assert any(
                fmt in error_text
                for fmt in ["jpeg", "png", "webp"]
            ), f"Error message does not mention allowed types: {exc.message}"
