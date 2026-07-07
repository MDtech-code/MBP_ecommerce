from django.db import models
from django.utils.translation import gettext_lazy as _


class Gender(models.TextChoices):
    MALE              = "M", _("Male")
    FEMALE            = "F", _("Female")
    OTHER             = "O", _("Other")
    PREFER_NOT_TO_SAY = "N", _("Prefer not to say")