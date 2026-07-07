from __future__ import annotations

import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator

from apps.common.models import TimeStampedModel
from apps.common.choices.role import Role

from .managers import UserManager



class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model using email as the primary identifier.

    Replaces Django's default username-based User.
    Email is the login field — standard for ecommerce.
    """

    email = models.EmailField(
        _("email address"),
        unique=True,
        db_index=True,
    )
    full_name = models.CharField(
        _("full name"),
        max_length=255,
    )
    role = models.CharField(
        _("role"),
        max_length=2,
        choices=Role.choices,
        default=Role.CUSTOMER,
    )
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_(
            "Designates whether this user should be treated as active. "
            "Unselect this instead of deleting accounts."
        ),
    )
    is_staff = models.BooleanField(
        _("staff status"),
        default=False,
        help_text=_("Designates whether the user can log into the admin site."),
    )
    is_verified = models.BooleanField(
        _("email verified"),
        default=False,
        help_text=_("Designates whether the user has verified their email address."),
    )
    date_joined = models.DateTimeField(
        _("date joined"),
        default=timezone.now,
    )
    updated_at = models.DateTimeField(
        _("last updated"),
        auto_now=True,
        help_text=_("Automatically updated whenever the user record is saved."),
    )

    # ─── Auth configuration ───────────────────────────────
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

        indexes = [
            models.Index(fields=["role"], name="accounts_user_role_idx"),
            models.Index(fields=["last_login"], name="accounts_user_last_login_idx"),
        ]

    def __str__(self) -> str:
        return self.email

    @property
    def is_customer(self) -> bool:
        return self.role == Role.CUSTOMER

    @property
    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    @property
    def short_name(self) -> str:
        """Return first word of full name."""
        return self.full_name.split()[0] if self.full_name else self.email


class UserProfile(TimeStampedModel):
    """
    Extended profile information for a user.

    Separated from User to keep auth concerns clean.
    Created automatically via signal when User is created.
    """

    class Gender(models.TextChoices):
        MALE = "M", _("Male")
        FEMALE = "F", _("Female")
        OTHER = "O", _("Other")
        PREFER_NOT_TO_SAY = "N", _("Prefer not to say")

    class Province(models.TextChoices):
        PUNJAB = "PB", _("Punjab")
        SINDH = "SD", _("Sindh")
        KPK = "KP", _("Khyber Pakhtunkhwa")
        BALOCHISTAN = "BL", _("Balochistan")
        GILGIT_BALTISTAN = "GB", _("Gilgit-Baltistan")
        AJK = "AK", _("Azad Jammu & Kashmir")
        ISLAMABAD = "IC", _("Islamabad Capital Territory")

    phone_validator = RegexValidator(
        regex=r"^\+?92\d{10}$|^0\d{10}$",
        message=_(
            "Enter a valid Pakistani phone number. "
            "Format: +923001234567 or 03001234567"
        ),
    )

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("user"),
    )
    phone = models.CharField(
        _("phone number"),
        max_length=15,
        validators=[phone_validator],
        blank=True,
        default="",
    )
    date_of_birth = models.DateField(
        _("date of birth"),
        null=True,
        blank=True,
    )
    gender = models.CharField(
        _("gender"),
        max_length=1,
        choices=Gender.choices,
        blank=True,
        default="",
    )
    avatar = models.ImageField(
        _("avatar"),
        upload_to="avatars/%Y/%m/",
        null=True,
        blank=True,
    )
    address_line1 = models.CharField(
        _("address line 1"),
        max_length=255,
        blank=True,
        default="",
    )
    address_line2 = models.CharField(
        _("address line 2"),
        max_length=255,
        blank=True,
        default="",
    )
    city = models.CharField(
        _("city"),
        max_length=100,
        blank=True,
        default="",
    )
    province = models.CharField(
        _("province"),
        max_length=2,
        choices=Province.choices,
        blank=True,
        default="",
    )
    postal_code = models.CharField(
        _("postal code"),
        max_length=10,
        blank=True,
        default="",
    )
    country = models.CharField(
        _("country"),
        max_length=100,
        default="Pakistan",
    )

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self) -> str:
        return f"{self.user.email} — profile"

    @property
    def has_complete_address(self) -> bool:
        return all([
            self.address_line1,
            self.city,
            self.province,
            self.postal_code,
        ])

    @property
    def full_address(self) -> str:
        parts = filter(None, [
            self.address_line1,
            self.address_line2,
            self.city,
            self.get_province_display(),
            self.postal_code,
            self.country,
        ])
        return ", ".join(parts)


class EmailVerificationToken(models.Model):
    """
    One-time token for email address verification.

    Expires after 24 hours. Multiple tokens can exist
    per user (for resend scenarios) but only the latest is valid.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
        verbose_name=_("user"),
    )
    token = models.UUIDField(
        _("token"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )
    expires_at = models.DateTimeField(
        _("expires at"),
    )

    class Meta:
        verbose_name = _("email verification token")
        verbose_name_plural = _("email verification tokens")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs) -> None:
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Email verification for {self.user.email}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_expired

    @classmethod
    def create_for_user(cls, user: User) -> "EmailVerificationToken":
        """
        Create a new token for user.
        Deletes all previous tokens for this user first.
        """
        cls.objects.filter(user=user).delete()
        return cls.objects.create(user=user)


class PasswordResetToken(models.Model):
    """
    Single-use token for password reset.

    Expires after 1 hour. Marked as used after password reset
    to prevent replay attacks.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name=_("user"),
    )
    token = models.UUIDField(
        _("token"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
    )
    expires_at = models.DateTimeField(
        _("expires at"),
    )
    is_used = models.BooleanField(
        _("is used"),
        default=False,
        help_text=_("Token becomes invalid after first use."),
    )

    class Meta:
        verbose_name = _("password reset token")
        verbose_name_plural = _("password reset tokens")
        ordering = ["-created_at"]

    def save(self, *args, **kwargs) -> None:
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"Password reset for {self.user.email}"

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        return not self.is_used and not self.is_expired

    @classmethod
    def create_for_user(cls, user: User) -> "PasswordResetToken":
        """
        Create a new token. Invalidates all previous reset tokens for user.
        """
        cls.objects.filter(user=user).delete()
        return cls.objects.create(user=user)

    def mark_used(self) -> None:
        self.is_used = True
        self.save(update_fields=["is_used"])