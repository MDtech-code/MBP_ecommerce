from __future__ import annotations

import logging

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Cart

logger = logging.getLogger("apps.cart")

User = get_user_model()


@receiver(post_save, sender=User)
def create_cart_for_new_user(
    sender: type[User],
    instance: User,
    created: bool,
    **kwargs,
) -> None:
    """Auto-create an empty Cart when a new User is created."""
    if created:
        Cart.objects.create(user=instance)
        logger.info("Cart created for user: %s", instance.email)