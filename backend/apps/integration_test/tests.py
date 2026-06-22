from django.core.cache import cache
from rest_framework.test import APITestCase
from .models import Author, Book, ActivityLog


class IntegrationTest(APITestCase):

    def setUp(self):
        cache.clear()

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

    # ─── timestamp fields now exist from TimeStampedModel ───
    def test_timestamps_exist(self):
        self.assertIsNotNone(self.book.created_at)
        self.assertIsNotNone(self.book.updated_at)
        self.assertIsNotNone(self.author.created_at)

    def test_books_api(self):
        response = self.client.get("/api/integration/books/")
        self.assertEqual(response.status_code, 200)

    def test_redis_cache(self):
        first = self.client.get("/api/integration/books/")
        self.assertEqual(first.data["source"], "database")

        second = self.client.get("/api/integration/books/")
        self.assertEqual(second.data["source"], "redis")

    # ─── health now uses BaseAPIView response format ───
    def test_health_api(self):
        response = self.client.get("/api/integration/health/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["success"])         # ← new structure
        self.assertEqual(response.data["message"], "All systems operational")
        self.assertIn("celery_task_id", response.data["data"])
        self.assertIn("database", response.data["data"])

    # ─── new test — create book and verify cache invalidation ───
    def test_create_book_invalidates_cache(self):
        # warm up cache
        self.client.get("/api/integration/books/")

        # create new book
        self.client.post("/api/integration/books/create/", {
            "title": "New Book",
            "price": 200,
            "author": self.author.id
        }, format='json')

        # next load should come from database not cache
        response = self.client.get("/api/integration/books/")
        self.assertEqual(response.data["source"], "database")

    # ─── new test — author serializer shows total_books ───
    def test_author_total_books(self):
        response = self.client.get("/api/integration/authors/")
        self.assertEqual(response.status_code, 200)
        author_data = response.data["results"][0]  # paginated now
        self.assertEqual(author_data["total_books"], 1)
# from django.test import TestCase
# from django.urls import reverse
# from django.core.cache import cache
# from rest_framework.test import APITestCase
# from .models import Author, Book, ActivityLog


# class IntegrationTest(APITestCase):

#     def setUp(self):
#         cache.clear()  # ← clear Redis before each test

#         self.author = Author.objects.create(
#             name="Test Author",
#             email="test@test.com"
#         )

#         self.book = Book.objects.create(
#             author=self.author,
#             title="Testing Django",
#             price=100
#         )

#     def test_book_created(self):
#         self.assertEqual(Book.objects.count(), 1)

#     def test_signal_created_log(self):
#         self.assertEqual(ActivityLog.objects.count(), 1)

#     def test_books_api(self):
#         response = self.client.get("/api/integration/books/")
#         self.assertEqual(response.status_code, 200)

#     def test_redis_cache(self):
#         first = self.client.get("/api/integration/books/")
#         self.assertEqual(first.data["source"], "database")

#         second = self.client.get("/api/integration/books/")
#         self.assertEqual(second.data["source"], "redis")

#     def test_health_api(self):
#         response = self.client.get("/api/integration/health/")
#         self.assertEqual(response.status_code, 200)