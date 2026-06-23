from django.urls import path
from .views import (
    AuthorListAPIView,
    BookListAPIView,
    ActivityLogAPIView,
    SystemHealthAPIView,
    CreateBookAPIView,
    SentryTestAPIView
)

urlpatterns = [
    path("authors/", AuthorListAPIView.as_view()),
    path("books/", BookListAPIView.as_view()),
    path("books/create/", CreateBookAPIView.as_view()),
    path("logs/", ActivityLogAPIView.as_view()),
    path("health/", SystemHealthAPIView.as_view()),
    path("sentry-test/", SentryTestAPIView.as_view()),
]