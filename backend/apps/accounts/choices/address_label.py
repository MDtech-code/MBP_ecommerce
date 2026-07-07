from django.db import models
from django.utils.translation import gettext_lazy as _


class AddressLabel(models.TextChoices):
    HOME   = "home",   _("Home")
    OFFICE = "office", _("Office")
    OTHER  = "other",  _("Other")