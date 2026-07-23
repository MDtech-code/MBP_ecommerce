# apps/tax/apps.py
from __future__ import annotations

from django.apps import AppConfig


class TaxConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name               = "apps.tax"
    verbose_name       = "Tax"