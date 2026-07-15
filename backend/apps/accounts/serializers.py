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
# class RegisterSerializer(serializers.Serializer):
#     """
#     Validate and process new user registration input.

#     Validates:
#         - Full name: minimum two words.
#         - Email: valid format, unique in the system.
#         - Password: meets Django's AUTH_PASSWORD_VALIDATORS.
#         - Confirm password: must match password.

#     On ``save()``, creates and returns the new ``User`` instance.
#     Profile creation is handled automatically via post_save signal.

#     Error codes:
#         All custom raises use ErrorCode registry so frontend
#         receives machine-readable codes alongside human-readable messages.
#         DRF built-in field codes (blank, required, min_length, invalid)
#         are already descriptive — no override needed for those.
#     """

#     full_name = serializers.CharField(
#         max_length=255,
#         error_messages={"blank": _("Full name is required.")},
#     )
#     email = serializers.EmailField(
#         error_messages={
#             "blank": _("Email address is required."),
#             "invalid": _("Enter a valid email address."),
#         }
#     )
#     password = serializers.CharField(
#         write_only=True,
#         min_length=8,
#         error_messages={
#             "blank": _("Password is required."),
#             "min_length": _("Password must be at least 8 characters."),
#         },
#     )
#     confirm_password = serializers.CharField(
#         write_only=True,
#         error_messages={"blank": _("Please confirm your password.")},
#     )

#     def validate_email(self, value: str) -> str:
#         """Normalize and assert email uniqueness."""
#         return validate_email_unique(value)

#     def validate_full_name(self, value: str) -> str:
#         """Assert full name has at least two words."""
#         return validate_full_name(value)

#     def validate_password(self, value: str) -> str:
#         """Run Django's password strength validators."""
#         return validate_strong_password(value)

#     def validate(self, attrs: dict) -> dict:
#         """
#         Cross-field validation.

#         Maps the password mismatch error onto ``confirm_password``
#         so the client receives a field-level error on the correct key.

#         ErrorDetail is used directly so the code travels with the message
#         through DRF's error collection and into _format_errors() intact.
#         """
#         try:
#             validate_passwords_match(attrs["password"], attrs["confirm_password"])
#         except DjangoValidationError:
#             raise serializers.ValidationError(
#                 {
#                     "confirm_password": ErrorDetail(
#                         _("Passwords do not match."),
#                         code=ErrorCode.PASSWORD_MISMATCH,
#                     )
#                 }
#             )
#         return attrs

#     def create(self, validated_data: dict) -> User:
#         """
#         Persist the new user.

#         Guards against the rare race condition where two concurrent requests
#         pass email uniqueness validation but one fails on the DB unique
#         constraint — surfaces this as a clean field error instead of a 500.

#         Args:
#             validated_data: Cleaned data from ``validate()``.

#         Returns:
#             Newly created ``User`` instance.

#         Raises:
#             serializers.ValidationError: On duplicate email race condition.
#         """
#         validated_data.pop("confirm_password")
#         try:
#             return User.objects.create_user(
#                 email=validated_data["email"],
#                 full_name=validated_data["full_name"],
#                 password=validated_data["password"],
#             )
#         except IntegrityError:
#             raise serializers.ValidationError(
#                 {
#                     "email": ErrorDetail(
#                         _("An account with this email already exists."),
#                         code=ErrorCode.EMAIL_ALREADY_EXISTS,
#                     )
#                 }
#             )

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
# class LoginSerializer(serializers.Serializer):
#     """
#     Validate login credentials and return authenticated user.

#     Checks (in order):
#         1. Email + password match a real user (via Django authenticate).
#         2. Account is active (not deactivated by admin).
#         3. Email is verified (user completed registration flow).

#     On success, attaches the ``User`` instance to ``attrs["user"]``
#     for the view to consume.

#     Error codes exposed to client:
#         - ``invalid_credentials``: email/password mismatch.
#         - ``account_inactive``:    account deactivated by admin.
#         - ``email_not_verified``:  registration email not confirmed yet.

#     Note:
#         Invalid credentials message is intentionally vague — we never
#         confirm whether an email address exists in the system.
#         This prevents user enumeration attacks.

#     Why ErrorDetail directly instead of code= on ValidationError:
#         When raising ValidationError with a dict payload, the code=
#         argument on the outer exception is ignored by DRF — it never
#         reaches the ErrorDetail objects inside the dict.
#         Wrapping in ErrorDetail directly guarantees the code travels
#         through DRF's internal processing into _format_errors() intact.
#     """

#     email = serializers.EmailField(
#         error_messages={"blank": _("Email address is required.")}
#     )
#     password = serializers.CharField(
#         write_only=True,
#         error_messages={"blank": _("Password is required.")}
#     )

#     def validate(self, attrs: dict) -> dict:
#         email = attrs["email"].lower().strip()
#         password = attrs["password"]

#         user = authenticate(
#             request=self.context.get("request"),
#             username=email,
#             password=password,
#         )

#         # ── Credential check ──────────────────────────────────────────────────
#         # Deliberately vague — do not confirm whether email exists.
#         # Prevents user enumeration attacks.
#         if not user:
#             raise serializers.ValidationError(
#                {
#                     "non_field_errors": ErrorDetail(
#                         _("Invalid email or password."),
#                         code=ErrorCode.INVALID_CREDENTIALS,
#                     )
#                 }
#             )

#         # ── Account active check ──────────────────────────────────────────────
#         if not user.is_active:
#             raise serializers.ValidationError(
#                 {
#                     "non_field_errors": ErrorDetail(
#                         _(
#                             "Your account has been deactivated. "
#                             "Please contact support."
#                         ),
#                         code=ErrorCode.ACCOUNT_INACTIVE,
#                     )
#                 }
#             )

#         # ── Email verified check ──────────────────────────────────────────────
#         # Distinct code so frontend can offer "resend verification" option.
#         if not user.is_verified:
#             raise serializers.ValidationError(
#                 {
#                     "non_field_errors": ErrorDetail(
#                         _(
#                             "Please verify your email address "
#                             "before logging in."
#                         ),
#                         code=ErrorCode.EMAIL_NOT_VERIFIED,
#                     )
#                 }
#             )

#         attrs["user"] = user
#         return attrs


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
# # ─── Email Verification Serializer ───────────────────────────────────────────

# class EmailVerificationSerializer(serializers.Serializer):
#     """
#     Accept and validate an email verification token.

#     The token is a UUID submitted by the user after clicking
#     the verification link sent to their email address.

#     Fields:
#         token: UUID string from the verification email link.
#     """

#     token = serializers.UUIDField(
#         error_messages={
#             "invalid": _("Invalid verification token."),
#             "blank": _("Verification token is required."),
#         }
#     )

# # ─── Resend Verification Serializer ──────────────────────────────────────────

# class ResendVerificationSerializer(serializers.Serializer):
#     """
#     Accept an email address for verification resend requests.

#     Intentionally minimal — we normalize the email and return it.
#     Existence and verification state checks happen in the view,
#     not here, to prevent serializer-level email enumeration.

#     Fields:
#         email: Email address to resend verification to.
#     """

#     email = serializers.EmailField(
#         error_messages={"blank": _("Email address is required.")}
#     )

#     def validate_email(self, value: str) -> str:
#         """Normalize email to lowercase and strip whitespace."""
#         return value.lower().strip()


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

'''
# ─── Password Reset Request Serializer ───────────────────────────────────────

class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Accept an email address for password reset requests.

    Intentionally minimal — we normalize the email and return it.
    Existence checks happen in the view to prevent serializer-level
    email enumeration.

    Fields:
        email: Email address of the account to reset.
    """

    email = serializers.EmailField(
        error_messages={"blank": _("Email address is required.")}
    )

    def validate_email(self, value: str) -> str:
        """Normalize email to lowercase and strip whitespace."""
        return value.lower().strip()


# ─── Password Reset Confirm Serializer ───────────────────────────────────────

class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Accept a reset token and new password to complete password reset.

    Validates:
        - Token is a valid UUID format.
        - Password meets strength requirements.
        - Password and confirm_password match.

    Token existence and expiry checks happen in the view —
    not here — to keep serializer concerns clean.

    Fields:
        token:            UUID from the password reset email link.
        password:         New password (write-only).
        confirm_password: Must match password (write-only).
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
        """Run Django's password strength validators."""
        return validate_strong_password(value)

    def validate(self, attrs: dict) -> dict:
        """
        Cross-field validation — map password mismatch onto confirm_password.

        Catches DjangoValidationError from validate_passwords_match and
        re-raises as DRF ValidationError on the correct field key.
        """
        try:
            validate_passwords_match(attrs["password"], attrs["confirm_password"])
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
               {
                "confirm_password": ErrorDetail(
                    _("Passwords do not match."),
                    code=ErrorCode.PASSWORD_MISMATCH,
                )
            }
            )
        return attrs


# ─── Change Password Serializer ───────────────────────────────────────────────

class ChangePasswordSerializer(serializers.Serializer):
    """
    Allow an authenticated user to change their own password.

    Current password is verified in the view (requires request.user context).
    New password strength is validated here.

    Fields:
        current_password:    User's existing password (write-only).
        new_password:        Desired new password (write-only).
        confirm_new_password: Must match new_password (write-only).
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
        """
        Run Django's password strength validators against the new password.

        NOTE: Method name is validate_new_password — not validate_password.
        DRF maps validate_<field_name> to the field. The field is new_password,
        so the method must be validate_new_password.
        """
        return validate_strong_password(value)

    def validate(self, attrs: dict) -> dict:
        """
        Cross-field validation — assert new_password matches confirm_new_password.

        Maps the mismatch error onto confirm_new_password field key
        so the client receives a field-level error on the correct key.
        """
        try:
            validate_passwords_match(
                attrs["new_password"],
                attrs["confirm_new_password"],
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                {
                "confirm_new_password": ErrorDetail(
                    _("Passwords do not match."),
                    code=ErrorCode.PASSWORD_MISMATCH,
                )
            }
            )
        return attrs


'''

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