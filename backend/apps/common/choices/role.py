from django.db import models
from django.utils.translation import gettext_lazy as _

class Role(models.TextChoices):
    """
    Enum-like class to define user roles across the system.

    Used for:
        - Field choices in models (e.g., UserProfile.role)
        - Permission checks in views and decorators
        - Role-based UI rendering and filtering

    Values:
        CUSTOMER ('CU') — Represents customer users
        ADMIN   ('AD') — Represents platform administrators

    """

    CUSTOMER = 'CU', _('Customer')
    ADMIN = 'AD', _('Admin')