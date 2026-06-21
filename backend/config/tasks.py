from celery import shared_task

@shared_task
def test_task(message):
    print(f"Celery received: {message}")
    return f"Done: {message}"