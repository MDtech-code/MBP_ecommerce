# apps/accounts/signals.py
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver



logger = logging.getLogger("apps.accounts")



@receiver(user_login_failed)
def handle_login_failure(sender, credentials, request, **kwargs):
    email = credentials.get("username", "unknown")
    ip = request.META.get("REMOTE_ADDR") if request else None
    logger.warning(
        "Failed login attempt",
        extra={"email": email, "ip": ip}
    )
    # Later: increment Redis counter → lockout after 5 attempts

