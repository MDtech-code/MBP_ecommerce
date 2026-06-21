from celery import shared_task

from .models import Author


@shared_task
def calculate_author_books():

    data = {}

    for author in Author.objects.all():

        data[author.name] = author.books.count()


    return data