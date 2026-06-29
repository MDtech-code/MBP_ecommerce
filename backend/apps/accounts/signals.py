from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import User, UserProfile

logger = logging.getLogger("apps.accounts")


@receiver(post_save, sender=User)
def create_user_profile(
    sender: type[User],
    instance: User,
    created: bool,
    **kwargs,
) -> None:
    """Auto-create UserProfile when a new User is created."""
    if created:
        UserProfile.objects.create(user=instance)
        logger.info("Profile created for user: %s", instance.email)


@receiver(post_save, sender=User)
def save_user_profile(
    sender: type[User],
    instance: User,
    **kwargs,
) -> None:
    """Keep profile in sync when user is saved."""
    if hasattr(instance, "profile"):
        instance.profile.save()