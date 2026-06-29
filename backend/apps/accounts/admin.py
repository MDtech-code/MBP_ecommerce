from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, EmailVerificationToken, PasswordResetToken


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Profile"
    fields = ["phone", "date_of_birth", "gender", "city", "province"]


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [UserProfileInline]
    list_display = ["email", "full_name", "role", "is_verified", "is_active", "date_joined"]
    list_filter = ["role", "is_verified", "is_active", "is_staff"]
    search_fields = ["email", "full_name"]
    ordering = ["-date_joined"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("full_name",)}),
        (_("Role & Status"), {"fields": ("role", "is_verified", "is_active", "is_staff", "is_superuser")}),
        (_("Permissions"), {"fields": ("groups", "user_permissions")}),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "full_name", "password1", "password2", "role"),
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "phone", "city", "province", "has_complete_address"]
    search_fields = ["user__email", "city"]
    list_filter = ["province", "gender"]


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "created_at", "expires_at", "is_valid"]
    search_fields = ["user__email"]
    readonly_fields = ["token", "created_at"]


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ["user", "token", "created_at", "expires_at", "is_used", "is_valid"]
    search_fields = ["user__email"]
    readonly_fields = ["token", "created_at"]