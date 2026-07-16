from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth import authenticate
from django.db import IntegrityError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from rest_framework.exceptions import ErrorDetail
from apps.core.error_codes import ErrorCode
from rest_framework import serializers

from apps.core.mixins import TimestampFieldsMixin

from .models import User, UserProfile,UserAddress
from .validators import validate_email_unique,validate_full_name,validate_image_file,validate_pakistani_phone,validate_passwords_match,validate_strong_password

logger = logging.getLogger("apps.accounts")



# ─── User Profile Serializer ───────────────────────────────────────────────────────
class UserProfileSerializer(TimestampFieldsMixin,serializers.ModelSerializer):
    

    
    gender_display = serializers.CharField(
        source="get_gender_display",
        read_only=True,
    )
    

    class Meta:
        model = UserProfile
        fields = [
            "phone",
            "date_of_birth",
            "gender",
            "gender_display",
            "avatar",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            # Avatar is read-only here — handled by AvatarUploadView
            "avatar": {"read_only": True},
            "created_at": {"read_only": True},
            "updated_at": {"read_only": True},
        }

    def validate_phone(self, value: str) -> str:
        """
        Run Pakistani phone number format validation.

        Delegates to the shared validator so model and serializer
        use identical validation logic. Empty string is allowed
        (phone is optional on the profile).
        """
        if not value:
            return value
        return validate_pakistani_phone(value)

    def validate_date_of_birth(self, value) -> object:
        """
        Assert date of birth is in the past.

        Prevents submission of future dates which would pass
        model-level validation but are semantically invalid.
        """
        if value and value >= timezone.now().date():
            raise serializers.ValidationError(
                ErrorDetail(
                _("Date of birth must be in the past."),
                code=ErrorCode.INVALID_DATE_OF_BIRTH,
            )
            )
        return value


class UserAddressSerializer(TimestampFieldsMixin,serializers.ModelSerializer):
    """
    Shipping address serializer.

    province, postal_code, country are read-only —
    auto-derived from city selection on save().
    label_display and province_display for frontend rendering.
    full_address computed property exposed for display banner.
    """
    label_display    = serializers.CharField(
        source="get_label_display",
        read_only=True,
    )
    province_display = serializers.CharField(
        source="get_province_display",
        read_only=True,
    )

    full_address     = serializers.CharField(
        read_only=True,
    )
    class Meta:
        model  = UserAddress
        fields = [
            "id",
            "label",
            "label_display",
            "address_line1",
            "address_line2",
            "phone",
            "city",
            "province",
            "province_display",
            "postal_code",
            "country",
            "is_default",
            "full_address",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "province":    {"read_only": True},
            "postal_code": {"read_only": True},
            "country":     {"read_only": True},
            "created_at":  {"read_only": True},
            "updated_at":  {"read_only": True},
        }

    def validate_address_line1(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(
               ErrorDetail(
                _("Address line 1 is required."),
                code=ErrorCode.INVALID_ADDRESS,
            )
            )
        return value.strip()
    def validate_phone(self, value: str) -> str:
        """
        Run Pakistani phone number format validation.

        Delegates to the shared validator so model and serializer
        use identical validation logic. Empty string is allowed
        (phone is optional on the profile).
        """
        if not value:
            return value
        return validate_pakistani_phone(value)






# ─── User Serializer ──────────────────────────────────────────────────────────

class UserSerializer(TimestampFieldsMixin,serializers.ModelSerializer):
    """Read-only user representation returned in responses."""

    profile = UserProfileSerializer(read_only=True)
    addresses       = UserAddressSerializer(many=True, read_only=True)
    default_address = serializers.SerializerMethodField()
    role_display = serializers.CharField(
        source="get_role_display",
        read_only=True,
    )
    short_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "short_name",
            "role",
            "role_display",
            "is_verified",
            "date_joined",
            "profile",
            "addresses",
            "default_address",
        ]
        read_only_fields = fields
    def get_default_address(self, obj):
         """
         Returns the single default address or None.
         Avoids re-querying if addresses are prefetched.
         """
         default = next(
             (addr for addr in obj.addresses.all() if addr.is_default),
             None,
         )
         if default:
             return UserAddressSerializer(default).data
         return None


# ─── Registration Serializer ──────────────────────────────────────────────────

class RegisterSerializer(serializers.Serializer):
    """
    Validate new user registration input.

    Responsibility:
        Validate and clean input data ONLY.
        No database writes. No user creation.
        User creation is handled by AccountService.register_user()
        in the service layer.

    Validates:
        - Full name: minimum two words.
        - Email: valid format, unique in the system.
        - Password: meets Django's AUTH_PASSWORD_VALIDATORS.
        - Confirm password: must match password.
    """

    full_name = serializers.CharField(
        max_length=255,
        error_messages={"blank": _("Full name is required.")},
    )
    email = serializers.EmailField(
        error_messages={
            "blank": _("Email address is required."),
            "invalid": _("Enter a valid email address."),
        }
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "blank": _("Password is required."),
            "min_length": _("Password must be at least 8 characters."),
        },
    )
    confirm_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": _("Please confirm your password.")},
    )

    def validate_email(self, value: str) -> str:
        return validate_email_unique(value)

    def validate_full_name(self, value: str) -> str:
        return validate_full_name(value)

    def validate_password(self, value: str) -> str:
        return validate_strong_password(value)

    def validate(self, attrs: dict) -> dict:
        try:
            validate_passwords_match(attrs["password"], attrs["confirm_password"])
        except DjangoValidationError:
            raise serializers.ValidationError(
                {
                    "confirm_password": ErrorDetail(
                        _("Passwords do not match."),
                        code=ErrorCode.PASSWORD_MISMATCH,
                    )
                }
            )
        attrs.pop("confirm_password")
        return attrs


# ─── Login Serializer ─────────────────────────────────────────────────────────
# apps/accounts/serializers.py  (Login section — add after RegisterSerializer)
# ─── Login ─────────────────────────────────────────────────────────────────────

class LoginSerializer(serializers.Serializer):
    """
    Validate login input format only.

    Responsibility:
        Data Translation and Format Compliance ONLY.
        Normalizes email, ensures fields are present and non-blank.

        Credential checking (authenticate, is_active, is_verified)
        is business logic — it belongs in the service layer.
        Serializer has no knowledge of authentication outcome.

    Fields:
        email:    Normalized to lowercase + stripped.
        password: Write-only, required.
    """

    email = serializers.EmailField(
        error_messages={
            "blank": _("Email address is required."),
            "invalid": _("Enter a valid email address."),
        }
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={"blank": _("Password is required.")},
    )

    def validate_email(self, value: str) -> str:
        return value.lower().strip()

# ─── Email Verification ────────────────────────────────────────────────────────

class EmailVerificationSerializer(serializers.Serializer):
    """
    Validate an email verification token.

    Responsibility:
        Validate UUID format only.
        Token existence and state checks happen in the service layer.
    """

    token = serializers.UUIDField(
        error_messages={
            "invalid": _("Invalid verification token."),
            "blank": _("Verification token is required."),
        }
    )


# ─── Resend Verification ───────────────────────────────────────────────────────

class ResendVerificationSerializer(serializers.Serializer):
    """
    Validate an email address for verification resend requests.

    Responsibility:
        Normalize and validate email format only.
        User existence and verification state checks happen
        in the service layer — never here — to prevent
        serializer-level email enumeration.
    """

    email = serializers.EmailField(
        error_messages={"blank": _("Email address is required.")}
    )

    def validate_email(self, value: str) -> str:
        return value.lower().strip()



# ─── Password Reset Request ────────────────────────────────────────────────────

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Validate email address for password reset request.

    Responsibility:
        Normalize and validate email format only.
        User existence check happens in service layer — never here —
        to prevent serializer-level email enumeration.
    """

    email = serializers.EmailField(
        error_messages={"blank": _("Email address is required.")}
    )

    def validate_email(self, value: str) -> str:
        return value.lower().strip()


# ─── Password Reset Confirm ────────────────────────────────────────────────────

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Validate token and new password for password reset confirmation.

    Responsibility:
        Validate UUID format, password strength, and password match.
        Token existence and state checks happen in service layer.
    """

    token = serializers.UUIDField(
        error_messages={"invalid": _("Invalid reset token.")}
    )
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": _("Password must be at least 8 characters."),
            "blank": _("Password is required."),
        },
    )
    confirm_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": _("Please confirm your password.")},
    )

    def validate_password(self, value: str) -> str:
        return validate_strong_password(value)

    def validate(self, attrs: dict) -> dict:
        try:
            validate_passwords_match(attrs["password"], attrs["confirm_password"])
        except DjangoValidationError:
            raise serializers.ValidationError(
                {
                    "confirm_password": ErrorDetail(
                        _("Passwords do not match."),
                        code=ErrorCode.PASSWORD_MISMATCH,
                    )
                }
            )
        attrs.pop("confirm_password")
        return attrs


# ─── Change Password ───────────────────────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    """
    Validate current and new password for authenticated password change.

    Responsibility:
        Validate field presence, new password strength, and match.
        Current password correctness check happens in service layer
        against authenticated user's stored hash.
    """

    current_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": _("Current password is required.")},
    )
    new_password = serializers.CharField(
        write_only=True,
        min_length=8,
        error_messages={
            "min_length": _("New password must be at least 8 characters."),
            "blank": _("New password is required."),
        },
    )
    confirm_new_password = serializers.CharField(
        write_only=True,
        error_messages={"blank": _("Please confirm your new password.")},
    )

    def validate_new_password(self, value: str) -> str:
        return validate_strong_password(value)

    def validate(self, attrs: dict) -> dict:
        try:
            validate_passwords_match(
                attrs["new_password"],
                attrs["confirm_new_password"],
            )
        except DjangoValidationError:
            raise serializers.ValidationError(
                {
                    "confirm_new_password": ErrorDetail(
                        _("Passwords do not match."),
                        code=ErrorCode.PASSWORD_MISMATCH,
                    )
                }
            )
        attrs.pop("confirm_new_password")
        return attrs


# ─── Email Change Request ──────────────────────────────────────────────────────

class EmailChangeRequestSerializer(serializers.Serializer):
    """
    Validate new email and password for email change request.

    Responsibility:
        Validate new email format, uniqueness, and password presence.
        Password correctness and new email availability checks
        happen in service layer.

    Why validate uniqueness here?
        Fast fail — no need to hit service if email format is wrong.
        Service does a second check inside transaction for race conditions.
    """

    new_email = serializers.EmailField(
        error_messages={
            "blank": _("New email address is required."),
            "invalid": _("Enter a valid email address."),
        }
    )
    password = serializers.CharField(
        write_only=True,
        error_messages={"blank": _("Password is required to confirm email change.")},
    )

    def validate_new_email(self, value: str) -> str:
        return validate_email_unique(value)


# ─── Email Change Confirm ──────────────────────────────────────────────────────

class EmailChangeConfirmSerializer(serializers.Serializer):
    """
    Validate token for email change confirmation.

    Responsibility:
        Validate UUID format only.
        Token existence and state checks happen in service layer.
    """

    token = serializers.UUIDField(
        error_messages={
            "invalid": _("Invalid email change token."),
            "blank": _("Token is required."),
        }
    )



# ─── Profile Update Serializer ───────────────────────────────────────────────
class ProfileUpdateSerializer(UserProfileSerializer):
    """
    Explicit partial-update serializer for ``UserProfile``.

    Inherits all fields and validators from ``UserProfileSerializer``.
    Exists as a named class for clarity in the view and for
    drf-spectacular schema generation (shows as distinct schema type).

    All fields are optional — clients send only what they want to change.
    """

    class Meta(UserProfileSerializer.Meta):
        # Explicitly mark all writable fields as not required
        # Redundant when used with partial=True but makes intent clear
        extra_kwargs = {
            **UserProfileSerializer.Meta.extra_kwargs,
            "phone": {"required": False},
            "date_of_birth": {"required": False},
            "gender": {"required": False},
            "address_line1": {"required": False},
            "address_line2": {"required": False},
            "city": {"required": False},
            "province": {"required": False},
            "postal_code": {"required": False},
            "country": {"required": False},
        }



# ─── Avatar Upload Serializer ─────────────────────────────────────────────────
class AvatarUploadSerializer(serializers.Serializer):
    """
    Accept and validate an avatar image upload.

    Validation:
        - File must be present.
        - Size must not exceed 2 MB.
        - MIME type must be JPEG, PNG, or WebP.

    Note:
        Kept as a plain ``Serializer`` (not ``ModelSerializer``) because
        avatar saving is handled explicitly in the view — we want full
        control over old avatar deletion before saving the new one.
    """

    avatar = serializers.ImageField(
        error_messages={
            "required": _("Please select an image to upload."),
            "invalid": _("Upload a valid image file."),
            "empty": _("The submitted image file is empty."),
        }
    )

    def validate_avatar(self, value) -> object:
        """
        Run size and MIME type validation via shared image validator.

        Delegates to ``validate_image_file`` so all image upload
        points in the system use identical validation rules.
        """
        return validate_image_file(value)



# ─── Account Deletion ──────────────────────────────────────────────────────────

class DeleteAccountSerializer(serializers.Serializer):
    """
    Validate password confirmation for account deletion.

    Responsibility:
        Validate password field presence only.
        Password correctness check happens in the service layer
        against the authenticated user's stored hash.

    Security note:
        We do NOT check password correctness here.
        Serializer has no access to request.user safely.
        Service layer owns that check.
    """

    password = serializers.CharField(
        write_only=True,
        error_messages={
            "blank": _("Password is required to confirm account deletion."),
        },
    )