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
# from django.db import models


# class Author(models.Model):

#     name = models.CharField(max_length=100)
#     email = models.EmailField(unique=True)

#     created_at = models.DateTimeField(auto_now_add=True)


#     def __str__(self):
#         return self.name



# class Book(models.Model):

#     author = models.ForeignKey(
#         Author,
#         related_name="books",
#         on_delete=models.CASCADE
#     )

#     title = models.CharField(max_length=200)

#     price = models.DecimalField(
#         max_digits=8,
#         decimal_places=2
#     )

#     created_at = models.DateTimeField(
#         auto_now_add=True
#     )


#     def __str__(self):
#         return self.title



# class ActivityLog(models.Model):

#     message = models.TextField()

#     created_at = models.DateTimeField(
#         auto_now_add=True
#     )