from __future__ import annotations

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from apps.common.choices.role import Role

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .models import User

class UserManager(BaseUserManager):
    """
    Custom manager for User model with email as login field.
    Replaces Django's default username-based UserManager.
    """

    def create_user(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields,
    ) -> "User":
        if not email:
            raise ValueError(_("Email address is required."))
        if not full_name:
            raise ValueError(_("Full name is required."))

        email = self.normalize_email(email)
        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields,
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("is_active", True)
        
        if extra_fields.get("role") != Role.ADMIN:
            extra_fields["role"] = Role.ADMIN

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, full_name, password, **extra_fields)