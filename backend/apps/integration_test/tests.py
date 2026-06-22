from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache
from rest_framework.test import APITestCase
from .models import Author, Book, ActivityLog


class IntegrationTest(APITestCase):

    def setUp(self):
        cache.clear()  # ← clear Redis before each test

        self.author = Author.objects.create(
            name="Test Author",
            email="test@test.com"
        )

        self.book = Book.objects.create(
            author=self.author,
            title="Testing Django",
            price=100
        )

    def test_book_created(self):
        self.assertEqual(Book.objects.count(), 1)

    def test_signal_created_log(self):
        self.assertEqual(ActivityLog.objects.count(), 1)

    def test_books_api(self):
        response = self.client.get("/api/integration/books/")
        self.assertEqual(response.status_code, 200)

    def test_redis_cache(self):
        first = self.client.get("/api/integration/books/")
        self.assertEqual(first.data["source"], "database")

        second = self.client.get("/api/integration/books/")
        self.assertEqual(second.data["source"], "redis")

    def test_health_api(self):
        response = self.client.get("/api/integration/health/")
        self.assertEqual(response.status_code, 200)