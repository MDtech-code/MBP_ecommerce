from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Book, ActivityLog


@receiver(post_save, sender=Book)
def book_created(sender, instance, created, **kwargs):

    if created:

        ActivityLog.objects.create(
            message=f"New book created: {instance.title}"
        )