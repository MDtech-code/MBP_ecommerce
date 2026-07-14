# apps/common/validators.py
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

phone_validator = RegexValidator(
    regex=r"^\+?92\d{10}$|^0\d{10}$",
    message=_(
        "Enter a valid Pakistani phone number. "
        "Format: +923001234567 or 03001234567"
    ),
)
