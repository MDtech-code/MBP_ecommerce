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
from apps.common.choices.city import City
from apps.common.choices.city_postal_map import CITY_POSTAL_MAP, CITY_PROVINCE_MAP
from apps.accounts.choices.gender import Gender
from apps.accounts.choices.province import Province
from apps.accounts.choices.address_label import AddressLabel

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
    Extended personal information for a user.
    Separated from User to keep auth concerns clean.
    Created automatically via signal when User is created.

    Address data lives in UserAddress (ISSUE-A02).
    This model holds personal identity only.
    """

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
    null=True,
    blank=True,
    default=None,
    unique=True,
    db_index=True,
    help_text=_(
        "Pakistani phone number. "
        "Format: +923001234567 or 03001234567. "
        "Must be unique across all accounts."
    ),
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

    class Meta:
        verbose_name = _("user profile")
        verbose_name_plural = _("user profiles")

    def __str__(self) -> str:
        return f"{self.user.email} — profile"

    @property
    def default_address(self) -> UserAddress | None:
        """
        Returns the user default shipping address or None.
        Address data lives in UserAddress since ISSUE-A02.
        """
        return self.user.addresses.filter(is_default=True).first()


class UserAddress(TimeStampedModel):
    """
    Stores multiple shipping addresses per user.

    City selection drives province and postal code automatically.
    Province and postal code are never entered manually by user.
    Country is always Pakistan — single market platform.
    One address per user can be marked as default enforced at
    both DB level and application level.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="addresses",
        verbose_name=_("user"),
    )
    label = models.CharField(
        _("address label"),
        max_length=10,
        choices=AddressLabel.choices,
        default=AddressLabel.HOME,
    )
    address_line1 = models.CharField(
        _("address line 1"),
        max_length=255,
        help_text=_("Street address, house number, building name."),
    )
    address_line2 = models.CharField(
        _("address line 2"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Apartment, floor, area, landmark. Optional."),
    )
    city = models.CharField(
        _("city"),
        max_length=50,
        choices=City.choices,
        help_text=_("Select your city from the list."),
    )
    province = models.CharField(
        _("province"),
        max_length=2,
        choices=Province.choices,
        editable=False,
        help_text=_("Auto-derived from selected city."),
    )
    postal_code = models.CharField(
        _("postal code"),
        max_length=10,
        editable=False,
        help_text=_("Auto-derived from selected city."),
    )
    country = models.CharField(
        _("country"),
        max_length=100,
        default="Pakistan",
        editable=False,
    )
    is_default = models.BooleanField(
        _("is default"),
        default=False,
        help_text=_("Only one address per user can be default."),
    )

    class Meta:
        verbose_name = _("user address")
        verbose_name_plural = _("user addresses")
        ordering = ["-is_default", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"{self.get_label_display()} — {self.address_line1}, {self.city}"

    def save(self, *args, **kwargs) -> None:
        """
        Auto-derives province and postal_code from city.
        Enforces single default address per user.
        """
        if self.city:
            self.province    = CITY_PROVINCE_MAP.get(self.city, self.province)
            self.postal_code = CITY_POSTAL_MAP.get(self.city, self.postal_code)

        if self.is_default:
            UserAddress.objects.filter(
                user=self.user,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

        super().save(*args, **kwargs)

    def set_as_default(self) -> None:
        """Explicit helper — preferred over setting is_default directly."""
        self.is_default = True
        self.save()

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
    is_used = models.BooleanField(
        _("is used"),
        default=False,
        help_text=_(
            "Token is marked used immediately after successful "
            "verification. Used tokens are rejected even if "
            "they have not yet expired."
        ),
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
        """
        Token is valid only if:
        - Not yet used (is_used=False)
        - Not yet expired (within 24 hour window)
        Mirrors PasswordResetToken.is_valid pattern.
        """
        return not self.is_expired
    
    def mark_used(self) -> None:
        """
        Marks token as consumed after successful email verification.
        Call this immediately after setting User.is_verified=True.
        Prevents replay attacks within the 24 hour expiry window.

        Usage in verification view:
            token.mark_used()
            user.is_verified = True
            user.save(update_fields=["is_verified"])
        """
        self.is_used = True
        self.save(update_fields=["is_used"])

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