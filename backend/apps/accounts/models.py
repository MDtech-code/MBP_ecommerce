from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.validators import phone_validator
from apps.common.models import TimeStampedModel
from apps.common.choices.role import Role
from apps.common.choices.city import City
from apps.common.choices.city_postal_map import CITY_POSTAL_MAP, CITY_PROVINCE_MAP

from apps.accounts.choices.gender import Gender
from apps.accounts.choices.province import Province
from apps.accounts.choices.address_label import AddressLabel

from .managers import UserManager

logger = logging.getLogger("apps.accounts")


# ─────────────────────────────────────────────────────────────────────────────
# USER (AUTH CORE)
# ─────────────────────────────────────────────────────────────────────────────

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

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["full_name"]

    objects = UserManager()

    class Meta:
        verbose_name        = _("user")
        verbose_name_plural = _("users")
        ordering            = ["-date_joined"]
        indexes = [
            models.Index(fields=["role"],       name="accounts_user_role_idx"),
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
        """Return first word of full name, fall back to email."""
        return self.full_name.split()[0] if self.full_name else self.email


# ─────────────────────────────────────────────────────────────────────────────
# ADDRESS QUERYSET + MANAGER
# Defined before UserProfile so UserProfile.default_address can reference
# UserAddress.objects.default_for_user() without a forward-reference error.
# ─────────────────────────────────────────────────────────────────────────────

class UserAddressQuerySet(models.QuerySet):

    def default_for_user(self, user_id: int) -> "UserAddress | None":
        """
        Returns the default address for a user in a single optimized query.
        Preferred over profile.default_address in list view or serializer contexts.
        """
        return self.filter(user_id=user_id, is_default=True).first()


class UserAddressManager(models.Manager):

    def get_queryset(self) -> UserAddressQuerySet:
        return UserAddressQuerySet(self.model, using=self._db)

    def default_for_user(self, user_id: int) -> "UserAddress | None":
        return self.get_queryset().default_for_user(user_id)


# ─────────────────────────────────────────────────────────────────────────────
# USER ADDRESS
# ─────────────────────────────────────────────────────────────────────────────

class UserAddress(TimeStampedModel):
    """
    Stores multiple shipping addresses per user.

    City selection drives province and postal code automatically.
    Province and postal code are never entered manually by the user.
    Country is always Pakistan — single market platform.
    One address per user can be marked as default, enforced at
    both DB level (UniqueConstraint) and application level
    (_set_as_sole_default with select_for_update).
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
    phone = models.CharField(
        _("contact phone for this address"),
        max_length=15,
        blank=True,
        default="",
        validators=[phone_validator],
        help_text=_(
            "Phone number for delivery at this address. "
            "Leave blank to use profile phone number."
        ),
    )
    is_default = models.BooleanField(
        _("is default"),
        default=False,
        help_text=_("Only one address per user can be default."),
    )

    objects = UserAddressManager()

    class Meta:
        verbose_name        = _("user address")
        verbose_name_plural = _("user addresses")
        ordering            = ["-is_default", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=models.Q(is_default=True),
                name="unique_default_address_per_user",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_default"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_label_display()} — {self.address_line1}, {self.city}"

    # ─── Save Pipeline ────────────────────────────────────────────────

    def save(self, *args, **kwargs) -> None:
        """
        1. Auto-derives province and postal_code from city (data invariant).
        2. If is_default=True, routes to _set_as_sole_default() which
           acquires SELECT FOR UPDATE locks before clearing other defaults.
        3. *args/**kwargs are forwarded on both paths so update_fields,
           force_insert, force_update all work correctly.
        """
        if self.city:
            self.province    = CITY_PROVINCE_MAP.get(self.city, self.province)
            self.postal_code = CITY_POSTAL_MAP.get(self.city, self.postal_code)

        if self.is_default:
            self._set_as_sole_default(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def _set_as_sole_default(self, *args, **kwargs) -> None:
        """
        Atomically ensures only this address is marked default.

        Why list() is required:
            Django QuerySets are lazy. select_for_update().filter(...)
            builds a query object but does NOT hit the database until
            the QuerySet is consumed. list() forces immediate evaluation,
            executing SELECT ... FOR UPDATE and holding row locks
            for the duration of this transaction.atomic() block.

        Concurrency guarantee:
            Any concurrent request attempting to set a default address
            for the same user_id will block at the SELECT FOR UPDATE
            until this transaction commits — eliminating the TOCTOU
            race condition.
        """
        with transaction.atomic():
            # ✅ list() consumes QuerySet → SELECT FOR UPDATE fires immediately
            list(
                UserAddress.objects.select_for_update().filter(
                    user_id=self.user_id
                )
            )

            # Safe to modify — exclusive row locks are held on all rows above
            UserAddress.objects.filter(
                user_id=self.user_id,
                is_default=True,
            ).exclude(pk=self.pk).update(is_default=False)

            # ✅ *args/**kwargs forwarded — update_fields etc. work correctly
            super().save(*args, **kwargs)

            logger.debug(
                "UserAddress default set atomically: user=%s address=%s city=%s",
                self.user_id,
                self.pk,
                self.city,
            )

    def set_as_default(self) -> None:
        """
        Public API for changing the default address.
        Preferred over setting is_default=True directly.
        Do NOT call from within a transaction that already holds
        conflicting UserAddress row locks — will deadlock.
        """
        self.is_default = True
        self.save()

    # ─── Properties ───────────────────────────────────────────────────

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

    @property
    def contact_phone(self) -> str:
        """
        Returns address-specific phone if set,
        otherwise falls back to user profile phone.
        Used at checkout to populate OrderShippingAddress.phone.

        ⚠️  Requires select_related('user__profile') on the calling
        queryset to avoid N+1 queries in list contexts.
        """
        return self.phone or (self.user.profile.phone or "")


# ─────────────────────────────────────────────────────────────────────────────
# USER PROFILE
# Defined after UserAddress so default_address property can reference
# UserAddress.objects without a forward-reference NameError.
# ─────────────────────────────────────────────────────────────────────────────

class UserProfile(TimeStampedModel):
    """
    Extended personal information for a user.
    Separated from User to keep auth concerns clean.
    Created automatically via signal when User is created.
    Address data lives in UserAddress.
    This model holds personal identity only.
    """

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
    is_phone_verified = models.BooleanField(
        _("phone verified"),
        default=False,
        help_text=_(
            "True after customer confirms phone via WhatsApp COD verification. "
            "Verified customers skip re-verification on subsequent COD orders."
        ),
    )
    phone_verified_at = models.DateTimeField(
        _("phone verified at"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name        = _("user profile")
        verbose_name_plural = _("user profiles")

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        logger.debug("UserProfile saved: user=%s", self.user_id)

    def __str__(self) -> str:
        return f"{self.user.email} — profile"

    @property
    def default_address(self) -> UserAddress | None:
        """
        Returns the default shipping address or None.

        ⚠️  Fires a DB query on every access.
        In list views or serializers, use the Prefetch pattern instead:
            User.objects.prefetch_related(
                Prefetch(
                    'addresses',
                    queryset=UserAddress.objects.filter(is_default=True),
                    to_attr='prefetched_default_address'
                )
            )
        """
        return UserAddress.objects.default_for_user(self.user_id)


# ─────────────────────────────────────────────────────────────────────────────
# TOKEN BASE + CONCRETE TOKEN MODELS
# ─────────────────────────────────────────────────────────────────────────────

class BaseVerificationToken(models.Model):
    """
    Abstract base for all single-use expiring tokens.

    Provides:
        - token     : UUID, unique, indexed
        - created_at: auto-set on creation
        - expires_at: auto-set from expiry_hours in save()
        - is_used   : flipped by mark_used()
        - is_expired: property
        - is_valid  : property (not used AND not expired)
        - mark_used(): saves is_used=True atomically

    Concrete subclasses must define:
        - user          : ForeignKey or OneToOneField to User
        - expiry_hours  : int class attribute (default: 24)
        - Meta.verbose_name etc.
    """

    # Override in subclasses. Plain class attribute — NOT a DB field.
    expiry_hours = 24

    token = models.UUIDField(
        _("token"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    expires_at = models.DateTimeField(_("expires at"), null=True, blank=True)
    is_used    = models.BooleanField(_("is used"), default=False)

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=self.expiry_hours)
        super().save(*args, **kwargs)

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_valid(self) -> bool:
        """True only if token has not been used and has not expired."""
        return not self.is_used and not self.is_expired

    def mark_used(self) -> None:
        """
        Marks token as consumed. Call inside transaction.atomic()
        alongside the action the token authorizes (e.g. setting
        user.is_verified=True) to prevent replay attacks.
        """
        self.is_used = True
        self.save(update_fields=["is_used"])


class EmailVerificationToken(BaseVerificationToken):
    """
    One-time token for email address verification.
    Expires after 24 hours.
    """

    expiry_hours = 24

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_verification_tokens",
        verbose_name=_("user"),
    )

    class Meta:
        verbose_name        = _("email verification token")
        verbose_name_plural = _("email verification tokens")
        ordering            = ["-created_at"]

    def __str__(self) -> str:
        return f"Email verification for {self.user.email}"


class PasswordResetToken(BaseVerificationToken):
    """
    Single-use token for password reset.
    Expires after 1 hour — shorter window for security.
    """

    expiry_hours = 1

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
        verbose_name=_("user"),
    )

    class Meta:
        verbose_name        = _("password reset token")
        verbose_name_plural = _("password reset tokens")
        ordering            = ["-created_at"]

    def __str__(self) -> str:
        return f"Password reset for {self.user.email}"


class PendingEmailChange(BaseVerificationToken):
    """
    Tracks unconfirmed email change requests.

    User.email is NOT changed until new email is verified.
    Old email remains active during the 24-hour verification window.
    Old email receives a security notification when change is requested.
    OneToOne on user — only one pending change per user at a time.

    Inherits from BaseVerificationToken:
        token, created_at, expires_at, is_used,
        is_expired, is_valid, mark_used(), save()
    """

    expiry_hours = 24

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="pending_email_change",
        verbose_name=_("user"),
    )
    new_email = models.EmailField(
        _("new email address"),
        help_text=_("Email address waiting to be verified."),
    )

    class Meta:
        verbose_name        = _("pending email change")
        verbose_name_plural = _("pending email changes")

    def save(self, *args, **kwargs) -> None:
        # BaseVerificationToken.save() handles expires_at auto-set
        super().save(*args, **kwargs)
        logger.debug(
            "PendingEmailChange saved: user=%s new_email=%s expires_at=%s",
            self.user_id,
            self.new_email,
            self.expires_at,
        )

    def __str__(self) -> str:
        return f"Email change: {self.user.email} → {self.new_email}"


# ─────────────────────────────────────────────────────────────────────────────
# LOGIN ACTIVITY (APPEND-ONLY AUDIT LOG)
# ─────────────────────────────────────────────────────────────────────────────

class UserLoginActivity(models.Model):
    """
    Immutable append-only log of every login attempt.

    Records both successful and failed attempts with IP and
    user agent for fraud detection and security auditing.

    Rows are never updated after creation — INSERT only.
    No TimeStampedModel — updated_at contradicts immutability.

    Celery periodic task purges records older than 90 days
    to prevent unbounded table growth.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="login_activity",
        verbose_name=_("user"),
        help_text=_(
            "SET NULL on delete — preserve security logs "
            "even if user account is deleted."
        ),
    )
    email_attempted = models.EmailField(
        _("email attempted"),
        help_text=_(
            "Email submitted in the login form. "
            "Stored separately from user FK — captures "
            "attempts against non-existent accounts too."
        ),
    )
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
        help_text=_("Remote IP of the login request."),
    )
    user_agent = models.TextField(
        _("user agent"),
        blank=True,
        default="",
        help_text=_("Browser and device string from request headers."),
    )
    was_successful = models.BooleanField(
        _("was successful"),
        help_text=_("True if credentials were valid and user logged in."),
    )
    failure_reason = models.CharField(
        _("failure reason"),
        max_length=50,
        blank=True,
        default="",
        help_text=_(
            "Short code for failed attempts. "
            "e.g. invalid_credentials, account_inactive, email_not_verified"
        ),
    )
    created_at = models.DateTimeField(
        _("created at"),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name        = _("user login activity")
        verbose_name_plural = _("user login activities")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user", "created_at"],
                name="acc_user_created_idx",
            ),
            models.Index(
                fields=["ip_address", "created_at"],
                name="acc_ip_created_idx",
            ),
            models.Index(
                fields=["was_successful", "created_at"],
                name="acc_success_created_idx",
            ),
            # Compound index: "count failed attempts from this IP in last N minutes"
            models.Index(
                fields=["ip_address", "was_successful", "created_at"],
                name="acc_ip_fail_rate_idx",
            ),
            # Compound index: "has this email been brute-forced recently"
            models.Index(
                fields=["email_attempted", "was_successful", "created_at"],
                name="acc_email_fail_rate_idx",
            ),
        ]

    def __str__(self) -> str:
        status = "success" if self.was_successful else "failed"
        return f"{self.email_attempted} — {status} — {self.created_at}"

    def save(self, *args, **kwargs) -> None:
        """
        Guard against updates — this model is append-only.
        Existing rows must never be modified after creation.
        """
        if self.pk:
            raise ValueError(
                "UserLoginActivity records are immutable "
                "and cannot be updated."
            )
        super().save(*args, **kwargs)
