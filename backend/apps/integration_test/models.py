from django.db import models
from apps.common.models import TimeStampedModel


class Author(TimeStampedModel):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    def __str__(self):
        return self.name


class Book(TimeStampedModel):
    author = models.ForeignKey(
        Author,
        related_name="books",
        on_delete=models.CASCADE
    )
    title = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return self.title


class ActivityLog(TimeStampedModel):
    message = models.TextField()
