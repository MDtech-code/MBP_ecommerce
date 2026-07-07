# apps/accounts/signals.py
from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.signals import user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile

logger = logging.getLogger("apps.accounts")


@receiver(post_save, sender=User)
def create_user_profile(
    sender: type[User],
    instance: User,
    created: bool,
    **kwargs: Any,
) -> None:
    """
    Auto-create a ``UserProfile`` whenever a new ``User`` is saved.

    Triggered by ``post_save`` on the ``User`` model.
    Logs an error (but does not raise) if profile creation fails,
    so that the user record itself is never silently lost.
    """
    if not created:
        return

    try:
        UserProfile.objects.create(user=instance)
        logger.info(
            "UserProfile created for new user",
            extra={"user_id": instance.id, "email": instance.email},
        )
    except Exception:
        logger.exception(
            "Failed to create UserProfile for new user — "
            "manual intervention may be required.",
            extra={"user_id": instance.id, "email": instance.email},
        )



# Example receiver you could add to signals.py:
@receiver(user_login_failed)
def handle_login_failure(sender, credentials, request, **kwargs):
    email = credentials.get("username", "unknown")
    ip = request.META.get("REMOTE_ADDR") if request else None
    logger.warning(
        "Failed login attempt",
        extra={"email": email, "ip": ip}
    )
    # Later: increment Redis counter → lockout after 5 attempts

# from __future__ import annotations

# import logging

# from django.db.models.signals import post_save
# from django.dispatch import receiver

# from .models import User, UserProfile

# logger = logging.getLogger("apps.accounts")


# @receiver(post_save, sender=User)
# def create_user_profile(
#     sender: type[User],
#     instance: User,
#     created: bool,
#     **kwargs,
# ) -> None:
#     """Auto-create UserProfile when a new User is created."""
#     if created:
#         UserProfile.objects.create(user=instance)
#         logger.info("Profile created for user: %s", instance.email)


# @receiver(post_save, sender=User)
# def save_user_profile(
#     sender: type[User],
#     instance: User,
#     **kwargs,
# ) -> None:
#     """Keep profile in sync when user is saved."""
#     if hasattr(instance, "profile"):
#         instance.profile.save()