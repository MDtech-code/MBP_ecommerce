import pytest
from django.core.cache import caches
from rest_framework.test import APIClient
from .models import Author, Book, ActivityLog


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear both cache levels before each test."""
    caches['default'].clear()
    caches['local'].clear()
    yield
    caches['default'].clear()
    caches['local'].clear()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def author(db):
    return Author.objects.create(
        name="Test Author",
        email="test@test.com"
    )


@pytest.fixture
def book(author):
    return Book.objects.create(
        author=author,
        title="Testing Django",
        price=100
    )


# ─── Basic model tests ────────────────────────────────
@pytest.mark.django_db
def test_book_created(book):
    assert Book.objects.count() == 1


@pytest.mark.django_db
def test_signal_created_log(book):
    assert ActivityLog.objects.count() == 1


@pytest.mark.django_db
def test_timestamps_exist(book, author):
    assert book.created_at is not None
    assert book.updated_at is not None
    assert author.created_at is not None


# ─── API tests ────────────────────────────────────────
@pytest.mark.django_db
def test_books_api(api_client, book):
    response = api_client.get("/api/integration/books/")
    assert response.status_code == 200


# ─── Two-level cache tests ─────────────────────────────
@pytest.mark.django_db
def test_first_request_hits_database(api_client, book):
    response = api_client.get("/api/integration/books/")
    assert response.data["source"] == "database"


@pytest.mark.django_db
def test_second_request_hits_l1_memory(api_client, book):
    api_client.get("/api/integration/books/")
    response = api_client.get("/api/integration/books/")
    assert response.data["source"] == "l1_memory"


@pytest.mark.django_db
def test_cache_invalidation_on_create(api_client, book, author):
    api_client.get("/api/integration/books/")
    api_client.post("/api/integration/books/create/", {
        "title": "New Book",
        "price": 200,
        "author": author.id
    }, format='json')
    response = api_client.get("/api/integration/books/")
    assert response.data["source"] == "database"


# ─── Health API ───────────────────────────────────────
@pytest.mark.django_db
def test_health_api_structure(api_client, book):
    response = api_client.get("/api/integration/health/")
    assert response.status_code == 200
    assert response.data["success"] is True
    assert response.data["message"] == "All systems operational"
    assert "celery_task_id" in response.data["data"]
    assert "database" in response.data["data"]
    assert "l1_cache" in response.data["data"]


@pytest.mark.django_db
def test_health_api_cached_on_second_request(api_client, book):
    api_client.get("/api/integration/health/")
    response = api_client.get("/api/integration/health/")
    assert response.data["data"]["served_from"] in ["l1_memory", "l2_redis"]


# ─── Author tests ─────────────────────────────────────
@pytest.mark.django_db
def test_author_total_books(api_client, book, author):
    response = api_client.get("/api/integration/authors/")
    assert response.status_code == 200
    author_data = response.data["data"][0]
    assert author_data["total_books"] == 1


# ─── Signal test ──────────────────────────────────────
@pytest.mark.django_db
def test_signal_creates_log_on_book_create(author):
    initial_count = ActivityLog.objects.count()
    Book.objects.create(
        author=author,
        title="Signal Test Book",
        price=50
    )
    assert ActivityLog.objects.count() == initial_count + 1


# ─── Parametrize example — pytest superpower ──────────
@pytest.mark.django_db
@pytest.mark.parametrize("price,expected_status", [
    (100, 201),    # valid price
    (-1, 400),     # invalid price
    (0, 201),      # zero price — valid
])
def test_create_book_price_validation(api_client, author, price, expected_status):
    response = api_client.post("/api/integration/books/create/", {
        "title": "Price Test Book",
        "price": price,
        "author": author.id
    }, format='json')
    assert response.status_code == expected_status
# from django.core.cache import caches
# from rest_framework.test import APITestCase
# from .models import Author, Book, ActivityLog


# class IntegrationTest(APITestCase):

#     def setUp(self):
#         # Clear both L1 and L2 cache before each test
#         caches['default'].clear()   # Redis
#         caches['local'].clear()     # Memory

#         self.author = Author.objects.create(
#             name="Test Author",
#             email="test@test.com"
#         )
#         self.book = Book.objects.create(
#             author=self.author,
#             title="Testing Django",
#             price=100
#         )

#     # ─── Basic model tests ────────────────────────────
#     def test_book_created(self):
#         self.assertEqual(Book.objects.count(), 1)

#     def test_signal_created_log(self):
#         self.assertEqual(ActivityLog.objects.count(), 1)

#     def test_timestamps_exist(self):
#         self.assertIsNotNone(self.book.created_at)
#         self.assertIsNotNone(self.book.updated_at)
#         self.assertIsNotNone(self.author.created_at)

#     # ─── API tests ────────────────────────────────────
#     def test_books_api(self):
#         response = self.client.get("/api/integration/books/")
#         self.assertEqual(response.status_code, 200)

#     # ─── Two-level cache tests ─────────────────────────
#     def test_first_request_hits_database(self):
#         response = self.client.get("/api/integration/books/")
#         self.assertEqual(response.data["source"], "database")

#     def test_second_request_hits_l1_memory(self):
#         # warm up — first request populates both L1 and L2
#         self.client.get("/api/integration/books/")
#         # second request — same process, L1 should hit
#         response = self.client.get("/api/integration/books/")
#         self.assertEqual(response.data["source"], "l1_memory")

#     def test_cache_invalidation_on_create(self):
#         # warm up cache
#         self.client.get("/api/integration/books/")

#         # create new book — should invalidate both L1 and L2
#         self.client.post("/api/integration/books/create/", {
#             "title": "New Book",
#             "price": 200,
#             "author": self.author.id
#         }, format='json')

#         # next request must hit database again
#         response = self.client.get("/api/integration/books/")
#         self.assertEqual(response.data["source"], "database")

#     # ─── Health API ───────────────────────────────────
#     def test_health_api_structure(self):
#         response = self.client.get("/api/integration/health/")
#         self.assertEqual(response.status_code, 200)
#         self.assertTrue(response.data["success"])
#         self.assertEqual(response.data["message"], "All systems operational")
#         self.assertIn("celery_task_id", response.data["data"])
#         self.assertIn("database", response.data["data"])
#         self.assertIn("l1_cache", response.data["data"])

#     def test_health_api_cached_on_second_request(self):
#         self.client.get("/api/integration/health/")
#         response = self.client.get("/api/integration/health/")
#         # second request should be served from cache
#         self.assertIn(
#             response.data["data"]["served_from"],
#             ["l1_memory", "l2_redis"]
#         )

#     # ─── Author tests ─────────────────────────────────
#     def test_author_total_books(self):
#         response = self.client.get("/api/integration/authors/")
#         self.assertEqual(response.status_code, 200)
#         # BaseAPIView pagination → data key not results
#         author_data = response.data["data"][0]
#         self.assertEqual(author_data["total_books"], 1)

#     # ─── Signal test ──────────────────────────────────
#     def test_signal_creates_log_on_book_create(self):
#         initial_count = ActivityLog.objects.count()
#         Book.objects.create(
#             author=self.author,
#             title="Signal Test Book",
#             price=50
#         )
#         self.assertEqual(ActivityLog.objects.count(), initial_count + 1)