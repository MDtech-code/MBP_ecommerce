from celery import shared_task

from .models import Author
import logging

logger = logging.getLogger(__name__)

@shared_task
def calculate_author_books():

    data = {}

    for author in Author.objects.all():

        data[author.name] = author.books.count()


    return data





@shared_task
def test_task(message):
    logger.info(f"Celery received: {message}")
    return f"Done: {message}"