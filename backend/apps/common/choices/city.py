from django.db import models
from django.utils.translation import gettext_lazy as _


class City(models.TextChoices):
    # ── Punjab ────────────────────────────────────────────
    LAHORE          = "Lahore",          _("Lahore")
    FAISALABAD      = "Faisalabad",      _("Faisalabad")
    RAWALPINDI      = "Rawalpindi",      _("Rawalpindi")
    GUJRANWALA      = "Gujranwala",      _("Gujranwala")
    MULTAN          = "Multan",          _("Multan")
    SIALKOT         = "Sialkot",         _("Sialkot")
    BAHAWALPUR      = "Bahawalpur",      _("Bahawalpur")
    SARGODHA        = "Sargodha",        _("Sargodha")
    SHEIKHUPURA     = "Sheikhupura",     _("Sheikhupura")
    GUJRAT          = "Gujrat",          _("Gujrat")
    RAHIM_YAR_KHAN  = "Rahim Yar Khan",  _("Rahim Yar Khan")
    JHANG           = "Jhang",           _("Jhang")
    SAHIWAL         = "Sahiwal",         _("Sahiwal")
    OKARA           = "Okara",           _("Okara")
    KASUR           = "Kasur",           _("Kasur")
    # ── Sindh ─────────────────────────────────────────────
    KARACHI         = "Karachi",         _("Karachi")
    HYDERABAD       = "Hyderabad",       _("Hyderabad")
    SUKKUR          = "Sukkur",          _("Sukkur")
    LARKANA         = "Larkana",         _("Larkana")
    NAWABSHAH       = "Nawabshah",       _("Nawabshah")
    MIRPUR_KHAS     = "Mirpur Khas",     _("Mirpur Khas")
    # ── Khyber Pakhtunkhwa ────────────────────────────────
    PESHAWAR        = "Peshawar",        _("Peshawar")
    ABBOTTABAD      = "Abbottabad",      _("Abbottabad")
    MARDAN          = "Mardan",          _("Mardan")
    SWAT            = "Swat",            _("Swat")
    KOHAT           = "Kohat",           _("Kohat")
    MINGORA         = "Mingora",         _("Mingora")
    # ── Balochistan ───────────────────────────────────────
    QUETTA          = "Quetta",          _("Quetta")
    TURBAT          = "Turbat",          _("Turbat")
    KHUZDAR         = "Khuzdar",         _("Khuzdar")
    # ── Federal / AJK / GB ────────────────────────────────
    ISLAMABAD       = "Islamabad",       _("Islamabad")
    MUZAFFARABAD    = "Muzaffarabad",    _("Muzaffarabad")
    GILGIT          = "Gilgit",          _("Gilgit")