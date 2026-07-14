# apps/accounts/admin.py
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from .models import (
    EmailVerificationToken,
    PasswordResetToken,
    PendingEmailChange,
    User,
    UserAddress,
    UserLoginActivity,
    UserProfile,
)


# ─────────────────────────────────────────────────────────────────────────────
# INLINES
# ─────────────────────────────────────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    """
    Inline profile editor shown within the User admin page.
    Shows personal identity and phone verification status.
    Address data is managed via UserAddressInline.
    """

    model        = UserProfile
    can_delete   = False
    verbose_name_plural = _("Profile")
    fields = [
        "phone",
        "date_of_birth",
        "gender",
        "avatar",
        "is_phone_verified",
        "phone_verified_at",
    ]
    readonly_fields = [
        "is_phone_verified",
        "phone_verified_at",
    ]


class UserAddressInline(admin.TabularInline):
    """
    Inline address editor shown within the User admin page.
    Province, postal_code, and country are read-only — auto-derived.
    """

    model      = UserAddress
    extra      = 0
    verbose_name_plural = _("Addresses")
    fields = [
        "label",
        "address_line1",
        "address_line2",
        "city",
        "province",
        "postal_code",
        "country",
        "phone",
        "is_default",
    ]
    readonly_fields = [
        "province",
        "postal_code",
        "country",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        No FK traversal in fields — default queryset is sufficient.
        Explicitly documented so future editors don't add FK display
        fields without adding select_related here.
        """
        return super().get_queryset(request)


# ─────────────────────────────────────────────────────────────────────────────
# USER ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin interface for the custom User model.

    Overrides BaseUserAdmin completely because the default fieldsets
    reference the 'username' field which does not exist on this model.
    Email is the USERNAME_FIELD — all forms reflect this.
    """

    inlines = [UserProfileInline, UserAddressInline]

    # ── List view ─────────────────────────────────────────────────────────────
    list_display = [
        "email",
        "full_name",
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "date_joined",
        "updated_at",
    ]
    list_filter = [
        "role",
        "is_verified",
        "is_active",
        "is_staff",
        "is_superuser",
    ]
    search_fields  = ["email", "full_name"]
    ordering       = ["-date_joined"]
    date_hierarchy = "date_joined"
    list_per_page  = 50
    show_full_result_count = False

    # ── Detail view ───────────────────────────────────────────────────────────
    fieldsets = (
        (
            None,
            {
                "fields": ("email", "password"),
            },
        ),
        (
            _("Personal Information"),
            {
                "fields": ("full_name",),
            },
        ),
        (
            _("Role & Status"),
            {
                "fields": (
                    "role",
                    "is_verified",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": ("groups", "user_permissions"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Important Dates"),
            {
                "fields": (
                    "last_login",
                    "date_joined",
                    "updated_at",
                ),
            },
        ),
    )
    readonly_fields = [
        "last_login",
        "date_joined",
        "updated_at",
    ]

    # ── Add user form ─────────────────────────────────────────────────────────
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "full_name",
                    "password1",
                    "password2",
                    "role",
                    "is_verified",
                    "is_active",
                    "is_staff",
                ),
            },
        ),
    )

    filter_horizontal = ["groups", "user_permissions"]


# ─────────────────────────────────────────────────────────────────────────────
# USER PROFILE ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Standalone admin for UserProfile.
    Useful for support staff who need to look up profiles
    by phone number without going through the User admin.
    """

    list_display = [
        "user",
        "phone",
        "gender",
        "date_of_birth",
        "is_phone_verified",
        "display_has_avatar",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "user__full_name",
        "phone",
    ]
    list_filter    = ["gender", "is_phone_verified"]
    list_per_page  = 50
    readonly_fields = [
        "is_phone_verified",
        "phone_verified_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("User"),
            {
                "fields": ("user",),
            },
        ),
        (
            _("Contact"),
            {
                "fields": ("phone",),
            },
        ),
        (
            _("Personal"),
            {
                "fields": (
                    "date_of_birth",
                    "gender",
                    "avatar",
                ),
            },
        ),
        (
            _("Phone Verification"),
            {
                "fields": (
                    "is_phone_verified",
                    "phone_verified_at",
                ),
                "description": _(
                    "Phone verification is set automatically by the "
                    "WhatsApp COD verification flow. Do not edit manually."
                ),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("user"): list_display accesses user.email — N+1 without this.
        """
        return super().get_queryset(request).select_related("user")

    @admin.display(boolean=True, description=_("Has Avatar"))
    def display_has_avatar(self, obj: UserProfile) -> bool:
        return bool(obj.avatar)


# ─────────────────────────────────────────────────────────────────────────────
# USER ADDRESS ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    """
    Admin interface for UserAddress.
    Province, postal_code and country are read-only — auto-derived from city.
    """

    list_display = [
        "user",
        "label",
        "address_line1",
        "city",
        "province",
        "is_default",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "user__full_name",
        "address_line1",
        "city",
    ]
    list_filter = [
        "label",
        "province",
        "is_default",
    ]
    list_per_page = 50
    readonly_fields = [
        "province",
        "postal_code",
        "country",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("User"),
            {
                "fields": ("user",),
            },
        ),
        (
            _("Address"),
            {
                "fields": (
                    "label",
                    "address_line1",
                    "address_line2",
                    "city",
                    "province",
                    "postal_code",
                    "country",
                    "phone",
                ),
            },
        ),
        (
            _("Default"),
            {
                "fields": ("is_default",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("user"): list_display accesses user.email — N+1 without this.
        """
        return super().get_queryset(request).select_related("user")


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL VERIFICATION TOKEN ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """
    Read-only admin for EmailVerificationToken.
    Tokens are system-generated — no manual creation or editing.
    Supports staff looking up verification status for a user.
    """

    list_display = [
        "user",
        "token",
        "created_at",
        "expires_at",
        "is_used",
        "display_is_valid",
    ]
    search_fields  = ["user__email"]
    list_filter    = ["is_used"]
    list_per_page  = 50
    date_hierarchy = "created_at"
    ordering       = ["-created_at"]

    # All fields read-only — tokens are system-generated, never hand-edited
    readonly_fields = [
        "user",
        "token",
        "created_at",
        "expires_at",
        "is_used",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """select_related("user"): list_display accesses user.email."""
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    @admin.display(boolean=True, description=_("Valid"))
    def display_is_valid(self, obj: EmailVerificationToken) -> bool:
        """
        is_valid = not is_used AND not is_expired.
        Computed property — cannot be used as admin_order_field.
        """
        return obj.is_valid


# ─────────────────────────────────────────────────────────────────────────────
# PASSWORD RESET TOKEN ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Read-only admin for PasswordResetToken.
    Tokens are system-generated — no manual creation or editing.
    Supports staff investigating failed password reset attempts.
    """

    list_display = [
        "user",
        "token",
        "created_at",
        "expires_at",
        "is_used",
        "display_is_valid",
    ]
    search_fields  = ["user__email"]
    list_filter    = ["is_used"]
    list_per_page  = 50
    date_hierarchy = "created_at"
    ordering       = ["-created_at"]

    readonly_fields = [
        "user",
        "token",
        "created_at",
        "expires_at",
        "is_used",
    ]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """select_related("user"): list_display accesses user.email."""
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    @admin.display(boolean=True, description=_("Valid"))
    def display_is_valid(self, obj: PasswordResetToken) -> bool:
        return obj.is_valid


# ─────────────────────────────────────────────────────────────────────────────
# PENDING EMAIL CHANGE ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(PendingEmailChange)
class PendingEmailChangeAdmin(admin.ModelAdmin):
    """
    Admin interface for PendingEmailChange.

    Primary use case: support staff clearing a stuck pending change
    so a user can request a new email change.

    Delete is permitted — clearing a stuck record is a valid
    support action. Add and change are blocked — changes must
    go through the email change service flow.
    """

    list_display = [
        "user",
        "new_email",
        "created_at",
        "expires_at",
        "is_used",
        "display_is_valid",
    ]
    search_fields = [
        "user__email",
        "new_email",
    ]
    list_filter    = ["is_used"]
    list_per_page  = 50
    date_hierarchy = "created_at"
    ordering       = ["-created_at"]

    readonly_fields = [
        "user",
        "new_email",
        "token",
        "created_at",
        "expires_at",
        "is_used",
    ]

    fieldsets = (
        (
            _("Request Details"),
            {
                "fields": (
                    "user",
                    "new_email",
                    "token",
                ),
            },
        ),
        (
            _("Status"),
            {
                "fields": (
                    "is_used",
                    "created_at",
                    "expires_at",
                ),
                "description": _(
                    "All fields are read-only. To clear a stuck pending "
                    "change, use the Delete action."
                ),
            },
        ),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """select_related("user"): list_display accesses user.email."""
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    @admin.display(boolean=True, description=_("Valid"))
    def display_is_valid(self, obj: PendingEmailChange) -> bool:
        return obj.is_valid


# ─────────────────────────────────────────────────────────────────────────────
# USER LOGIN ACTIVITY ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(UserLoginActivity)
class UserLoginActivityAdmin(admin.ModelAdmin):
    """
    Read-only admin for UserLoginActivity.
    Immutable audit log — no add, change, or delete permitted.
    Primary use: fraud investigation and brute force detection.
    """

    list_display = [
        "email_attempted",
        "user",
        "ip_address",
        "display_was_successful",
        "failure_reason",
        "created_at",
    ]
    search_fields = [
        "email_attempted",
        "user__email",
        "ip_address",
    ]
    list_filter = [
        "was_successful",
        "failure_reason",
    ]
    readonly_fields = [
        "user",
        "email_attempted",
        "ip_address",
        "user_agent",
        "was_successful",
        "failure_reason",
        "created_at",
    ]
    list_per_page  = 100
    date_hierarchy = "created_at"
    ordering       = ["-created_at"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """
        select_related("user"): list_display accesses user.email.
        Left join — user can be NULL (SET_NULL on delete).
        """
        return super().get_queryset(request).select_related("user")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        return False

    @admin.display(boolean=True, description=_("Successful"))
    def display_was_successful(self, obj: UserLoginActivity) -> bool:
        return obj.was_successful