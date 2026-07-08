# apps/accounts/managers.py
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _

from apps.common.choices.role import Role

if TYPE_CHECKING:
    from .models import User

logger = logging.getLogger("apps.accounts")


class UserManager(BaseUserManager):
    """
    Custom manager for ``User`` with email as the login identifier.

    Replaces Django's default username-based ``UserManager``.
    Normalizes both email (via ``BaseUserManager.normalize_email``)
    and full name (whitespace normalization) before persisting.
    """

    def create_user(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """
        Create and return a regular user.

        Args:
            email: User's email address (will be normalized to lowercase).
            full_name: User's full name (internal whitespace normalized).
            password: Plain-text password (will be hashed).
            **extra_fields: Additional model field values.

        Returns:
            Saved ``User`` instance.

        Raises:
            ValueError: If email or full_name are empty.
        """
        if not email:
            raise ValueError(_("Email address is required."))
        if not full_name:
            raise ValueError(_("Full name is required."))

        # Normalize at the manager level as the final line of defense —
        # regardless of whether input came from a serializer, management
        # command, shell, or fixture.
        email = self.normalize_email(email)
        full_name = " ".join(full_name.strip().split())

        user = self.model(email=email, full_name=full_name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self,
        email: str,
        full_name: str,
        password: str | None = None,
        **extra_fields: Any,
    ) -> "User":
        """
        Create and return a superuser with all elevated flags set.

        Forces ``is_staff``, ``is_superuser``, ``is_verified``,
        ``is_active``, and ``role=ADMIN`` regardless of input.

        Args:
            email: Superuser email address.
            full_name: Superuser full name.
            password: Plain-text password.
            **extra_fields: Additional field overrides.

        Returns:
            Saved superuser ``User`` instance.

        Raises:
            ValueError: If ``is_staff`` or ``is_superuser`` are explicitly
                set to ``False`` in ``extra_fields``.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_verified", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("role") not in (Role.ADMIN, None):
            logger.warning(
                "create_superuser called with non-ADMIN role '%s' — "
                "overriding to ADMIN.",
                extra_fields.get("role"),
            )
        extra_fields["role"] = Role.ADMIN

        if not extra_fields.get("is_staff"):
            raise ValueError(_("Superuser must have is_staff=True."))
        if not extra_fields.get("is_superuser"):
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, full_name, password, **extra_fields)
