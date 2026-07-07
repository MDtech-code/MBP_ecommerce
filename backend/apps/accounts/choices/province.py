from django.db import models
from django.utils.translation import gettext_lazy as _


class Province(models.TextChoices):
    PUNJAB           = "PB", _("Punjab")
    SINDH            = "SD", _("Sindh")
    KPK              = "KP", _("Khyber Pakhtunkhwa")
    BALOCHISTAN      = "BL", _("Balochistan")
    GILGIT_BALTISTAN = "GB", _("Gilgit-Baltistan")
    AJK              = "AK", _("Azad Jammu & Kashmir")
    ISLAMABAD        = "IC", _("Islamabad Capital Territory")