# apps/accounts/admin.py
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import EmailVerificationToken, PasswordResetToken, User, UserProfile,UserAddress




# ─── Inlines ──────────────────────────────────────────────────────────────────

class UserProfileInline(admin.StackedInline):
    """
    Inline profile editor shown within the User admin page.
    Shows personal identity fields only.
    Address data is managed via UserAddressInline.
    """

    model = UserProfile
    can_delete = False
    verbose_name_plural = _("Profile")
    fields = [
        "phone",
        "date_of_birth",
        "gender",
        "avatar",
    ]


class UserAddressInline(admin.TabularInline):
    """
    Inline address editor shown within the User admin page.
    Displays all addresses for this user in a compact table.
    Province and postal_code are read-only — auto-derived from city.
    Country is read-only — always Pakistan.
    """

    model = UserAddress
    extra = 0
    verbose_name_plural = _("Addresses")
    fields = [
        "label",
        "address_line1",
        "address_line2",
        "city",
        "province",
        "postal_code",
        "country",
        "is_default",
    ]
    readonly_fields = [
        "province",
        "postal_code",
        "country",
    ]


# ─── User Admin ───────────────────────────────────────────────────────────────

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
    search_fields = ["email", "full_name"]
    ordering = ["-date_joined"]
    date_hierarchy = "date_joined"
    list_per_page = 50
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


# ─── UserProfile Admin ────────────────────────────────────────────────────────

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for UserProfile.
    Shows personal identity fields only.
    Address data lives in UserAddress.
    """

    list_display = [
        "user",
        "phone",
        "gender",
        "date_of_birth",
        "display_has_avatar",
    ]
    search_fields = [
        "user__email",
        "user__full_name",
        "phone",
    ]
    list_filter = ["gender"]
    list_per_page = 50
    readonly_fields = ["created_at", "updated_at"]

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
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(boolean=True, description=_("Has Avatar"))
    def display_has_avatar(self, obj: UserProfile) -> bool:
        """
        Shows a boolean icon indicating whether user has uploaded an avatar.
        """
        return bool(obj.avatar)


# ─── UserAddress Admin ────────────────────────────────────────────────────────

@admin.register(UserAddress)
class UserAddressAdmin(admin.ModelAdmin):
    """
    Admin interface for UserAddress.
    Province, postal_code and country are read-only —
    auto-derived from city selection on save.
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
        "city",
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
# # ─── Inlines ──────────────────────────────────────────────────────────────────

# class UserProfileInline(admin.StackedInline):
#     """
#     Inline profile editor shown within the User admin page.

#     Displays the most commonly edited profile fields.
#     Avatar is excluded — managed via the frontend upload endpoint.
#     """

#     model = UserProfile
#     can_delete = False
#     verbose_name_plural = _("Profile")
#     fields = [
#         "phone",
#         "date_of_birth",
#         "gender",
#         "address_line1",
#         "address_line2",
#         "city",
#         "province",
#         "postal_code",
#         "country",
#     ]


# # ─── User Admin ───────────────────────────────────────────────────────────────

# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     """
#     Admin interface for the custom User model.

#     Overrides BaseUserAdmin completely because the default fieldsets
#     reference the 'username' field which does not exist on this model.
#     Email is the USERNAME_FIELD — all forms reflect this.
#     """

#     inlines = [UserProfileInline]

#     # ── List view ─────────────────────────────────────────────────────────────
#     list_display = [
#         "email",
#         "full_name",
#         "role",
#         "is_verified",
#         "is_active",
#         "is_staff",
#         "date_joined",
#     ]
#     list_filter = [
#         "role",
#         "is_verified",
#         "is_active",
#         "is_staff",
#         "is_superuser",
#     ]
#     search_fields = ["email", "full_name"]
#     ordering = ["-date_joined"]
#     date_hierarchy = "date_joined"
#     list_per_page = 50

#     # Prevents expensive COUNT(*) on large user tables
#     show_full_result_count = False

#     # ── Detail view ───────────────────────────────────────────────────────────
#     fieldsets = (
#         (
#             None,
#             {"fields": ("email", "password")},
#         ),
#         (
#             _("Personal Information"),
#             {"fields": ("full_name",)},
#         ),
#         (
#             _("Role & Status"),
#             {
#                 "fields": (
#                     "role",
#                     "is_verified",
#                     "is_active",
#                     "is_staff",
#                     "is_superuser",
#                 )
#             },
#         ),
#         (
#             _("Permissions"),
#             {
#                 "fields": ("groups", "user_permissions"),
#                 # Collapsed by default — reduces visual noise
#                 "classes": ("collapse",),
#             },
#         ),
#         (
#             _("Important Dates"),
#             {
#                 "fields": ("last_login", "date_joined"),
#             },
#         ),
#     )
#     readonly_fields = ["last_login", "date_joined"]

#     # ── Add user form ─────────────────────────────────────────────────────────
#     add_fieldsets = (
#         (
#             None,
#             {
#                 "classes": ("wide",),
#                 "fields": (
#                     "email",
#                     "full_name",
#                     "password1",
#                     "password2",
#                     "role",
#                     "is_verified",   # ← allow admin to verify on creation
#                     "is_active",
#                     "is_staff",
#                 ),
#             },
#         ),
#     )

#     # Prevents loading ALL groups/permissions into memory as dropdowns
#     filter_horizontal = ["groups", "user_permissions"]


# # ─── UserProfile Admin ────────────────────────────────────────────────────────

# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     """
#     Admin interface for UserProfile.

#     list_display uses explicit admin methods for @property fields
#     so Django can render boolean icons and set column headers.
#     """

#     list_display = [
#         "user",
#         "phone",
#         "city",
#         "province",
#         "display_has_complete_address",
#     ]
#     search_fields = ["user__email", "user__full_name", "city"]
#     list_filter = ["province", "gender"]
#     list_per_page = 50
#     readonly_fields = ["created_at", "updated_at"]

#     fieldsets = (
#         (
#             _("User"),
#             {"fields": ("user",)},
#         ),
#         (
#             _("Contact"),
#             {"fields": ("phone",)},
#         ),
#         (
#             _("Personal"),
#             {"fields": ("date_of_birth", "gender", "avatar")},
#         ),
#         (
#             _("Address"),
#             {
#                 "fields": (
#                     "address_line1",
#                     "address_line2",
#                     "city",
#                     "province",
#                     "postal_code",
#                     "country",
#                 )
#             },
#         ),
#         (
#             _("Timestamps"),
#             {
#                 "fields": ("created_at", "updated_at"),
#                 "classes": ("collapse",),
#             },
#         ),
#     )

#     @admin.display(boolean=True, description=_("Complete Address"))
#     def display_has_complete_address(self, obj: UserProfile) -> bool:
#         """
#         Render has_complete_address @property as a boolean icon column.

#         @admin.display(boolean=True) renders ✓/✗ icons instead of
#         True/False strings. description sets the column header text.
#         """
#         return obj.has_complete_address


# ─── Email Verification Token Admin ──────────────────────────────────────────

@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for EmailVerificationToken.

    All fields are read-only — tokens must not be manually edited.
    Expired/valid state displayed as boolean icon column.
    """

    list_display = [
        "user",
        "token",
        "created_at",
        "expires_at",
        "display_is_valid",
    ]
    search_fields = ["user__email"]
    list_filter = ["created_at", "expires_at"]
    list_per_page = 50
    date_hierarchy = "created_at"

    # All fields read-only — tokens are system-generated, never hand-edited
    readonly_fields = ["user", "token", "created_at", "expires_at"]

    def has_add_permission(self, request) -> bool:
        """
        Disable manual token creation via admin.

        Tokens must be created programmatically via
        EmailVerificationToken.create_for_user() to ensure
        correct expiry, uniqueness, and old token cleanup.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Disable manual token editing via admin.

        All fields are readonly but this adds an explicit guard
        at the permission level.
        """
        return False

    @admin.display(boolean=True, description=_("Valid"))
    def display_is_valid(self, obj: EmailVerificationToken) -> bool:
        """
        Render is_valid @property as a boolean icon column.

        Checks both expiry and used state (via is_valid property).
        """
        return obj.is_valid


# ─── Password Reset Token Admin ───────────────────────────────────────────────

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Admin interface for PasswordResetToken.

    All fields are read-only — tokens must not be manually edited.
    Expired/used/valid states displayed as boolean icon columns.
    """

    list_display = [
        "user",
        "token",
        "created_at",
        "expires_at",
        "display_is_used",
        "display_is_valid",
    ]
    search_fields = ["user__email"]
    list_filter = ["is_used", "created_at", "expires_at"]
    list_per_page = 50
    date_hierarchy = "created_at"

    # All fields read-only — tokens are system-generated, never hand-edited
    readonly_fields = ["user", "token", "created_at", "expires_at", "is_used"]

    def has_add_permission(self, request) -> bool:
        """
        Disable manual token creation via admin.

        Tokens must be created programmatically via
        PasswordResetToken.create_for_user() to ensure
        correct expiry, uniqueness, and old token cleanup.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Disable manual token editing via admin.

        Prevents an admin user from manually marking a used token
        as unused — which would reopen a consumed reset link.
        """
        return False

    @admin.display(boolean=True, description=_("Used"))
    def display_is_used(self, obj: PasswordResetToken) -> bool:
        """Render is_used field as a boolean icon column."""
        return obj.is_used

    @admin.display(boolean=True, description=_("Valid"))
    def display_is_valid(self, obj: PasswordResetToken) -> bool:
        """
        Render is_valid @property as a boolean icon column.

        is_valid = not is_used AND not is_expired.
        A token can be invalid by being either used OR expired.
        """
        return obj.is_valid
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# from django.utils.translation import gettext_lazy as _

# from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken


# class UserProfileInline(admin.StackedInline):
#     model = UserProfile
#     can_delete = False
#     verbose_name_plural = "Profile"
#     fields = ["phone", "date_of_birth", "gender", "city", "province"]


# @admin.register(User)
# class UserAdmin(BaseUserAdmin):
#     inlines = [UserProfileInline]
#     list_display = ["email", "full_name", "role", "is_verified", "is_active", "date_joined"]
#     list_filter = ["role", "is_verified", "is_active", "is_staff"]
#     search_fields = ["email", "full_name"]
#     ordering = ["-date_joined"]

#     fieldsets = (
#         (None, {"fields": ("email", "password")}),
#         (_("Personal info"), {"fields": ("full_name",)}),
#         (_("Role & Status"), {"fields": ("role", "is_verified", "is_active", "is_staff", "is_superuser")}),
#         (_("Permissions"), {"fields": ("groups", "user_permissions")}),
#         (_("Important dates"), {"fields": ("last_login", "date_joined")}),
#     )
#     add_fieldsets = (
#         (None, {
#             "classes": ("wide",),
#             "fields": ("email", "full_name", "password1", "password2", "role"),
#         }),
#     )


# @admin.register(UserProfile)
# class UserProfileAdmin(admin.ModelAdmin):
#     list_display = ["user", "phone", "city", "province", "has_complete_address"]
#     search_fields = ["user__email", "city"]
#     list_filter = ["province", "gender"]


# @admin.register(EmailVerificationToken)
# class EmailVerificationTokenAdmin(admin.ModelAdmin):
#     list_display = ["user", "token", "created_at", "expires_at", "is_valid"]
#     search_fields = ["user__email"]
#     readonly_fields = ["token", "created_at"]


# @admin.register(PasswordResetToken)
# class PasswordResetTokenAdmin(admin.ModelAdmin):
#     list_display = ["user", "token", "created_at", "expires_at", "is_used", "is_valid"]
#     search_fields = ["user__email"]
#     readonly_fields = ["token", "created_at"]