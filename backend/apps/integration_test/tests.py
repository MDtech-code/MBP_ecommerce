import pytest
from django.core.cache import caches
from rest_framework.test import APIClient
from .models import Author, Book, ActivityLog


@pytest.fixture(autouse=True)
def clear_cache():
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


# ─── Response structure tests ─────────────────────────
@pytest.mark.django_db
@pytest.mark.parametrize("url", [
    "/api/integration/books/",
    "/api/integration/authors/",
    "/api/integration/logs/",
])
def test_all_list_views_have_consistent_structure(api_client, book, url):
    """Every list view must return success, data, meta with pagination."""
    response = api_client.get(url)
    assert response.status_code == 200
    assert response.data["success"] is True
    assert "data" in response.data
    assert "message" in response.data
    assert "meta" in response.data
    # pagination fields always present
    assert "page" in response.data["meta"]
    assert "page_size" in response.data["meta"]
    assert "total_items" in response.data["meta"]
    assert "total_pages" in response.data["meta"]
    # cache source always present
    assert "source" in response.data["meta"]


# ─── Cache source tests ────────────────────────────────
@pytest.mark.django_db
@pytest.mark.parametrize("url", [
    "/api/integration/books/",
    "/api/integration/authors/",
    "/api/integration/logs/",
])
def test_first_request_hits_database(api_client, book, url):
    response = api_client.get(url)
    assert response.data["meta"]["source"] == "database"


@pytest.mark.django_db
@pytest.mark.parametrize("url", [
    "/api/integration/books/",
    "/api/integration/authors/",
    "/api/integration/logs/",
])
def test_second_request_hits_l1_memory(api_client, book, url):
    api_client.get(url)
    response = api_client.get(url)
    assert response.data["meta"]["source"] == "l1_memory"


# ─── Cache invalidation ───────────────────────────────
@pytest.mark.django_db
def test_create_book_invalidates_books_cache(api_client, book, author):
    api_client.get("/api/integration/books/")
    api_client.post("/api/integration/books/create/", {
        "title": "New Book",
        "price": 200,
        "author": author.id
    }, format='json')
    response = api_client.get("/api/integration/books/")
    assert response.data["meta"]["source"] == "database"


# ─── Pagination tests ──────────────────────────────────
@pytest.mark.django_db
def test_pagination_page_param(api_client, author):
    # create 15 books
    for i in range(15):
        Book.objects.create(author=author, title=f"Book {i}", price=100)

    response = api_client.get("/api/integration/books/?page=1&page_size=5")
    assert response.status_code == 200
    assert len(response.data["data"]) == 5
    assert response.data["meta"]["total_items"] == 15
    assert response.data["meta"]["total_pages"] == 3
    assert response.data["meta"]["page"] == 1


@pytest.mark.django_db
def test_pagination_second_page(api_client, author):
    for i in range(15):
        Book.objects.create(author=author, title=f"Book {i}", price=100)

    response = api_client.get("/api/integration/books/?page=2&page_size=5")
    assert response.status_code == 200
    assert len(response.data["data"]) == 5
    assert response.data["meta"]["page"] == 2


# ─── Author tests ─────────────────────────────────────
@pytest.mark.django_db
def test_author_total_books(api_client, book, author):
    response = api_client.get("/api/integration/authors/")
    assert response.status_code == 200
    author_data = response.data["data"][0]
    assert author_data["total_books"] == 1


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
    assert response.data["meta"]["source"] == "database"


@pytest.mark.django_db
def test_health_api_cached_on_second_request(api_client, book):
    api_client.get("/api/integration/health/")
    response = api_client.get("/api/integration/health/")
    assert response.data["meta"]["source"] in ["l1_memory", "l2_redis"]


# ─── Create book ──────────────────────────────────────
@pytest.mark.django_db
def test_create_book_returns_201_with_correct_structure(api_client, author):
    response = api_client.post("/api/integration/books/create/", {
        "title": "New Book",
        "price": 150,
        "author": author.id
    }, format='json')
    assert response.status_code == 201
    assert response.data["success"] is True
    assert response.data["data"]["title"] == "New Book"
    assert response.data["errors"] is None


@pytest.mark.django_db
def test_create_book_validation_error_structure(api_client, author):
    response = api_client.post("/api/integration/books/create/", {
        "title": "",   # invalid
        "price": 150,
        "author": author.id
    }, format='json')
    assert response.status_code == 400
    assert response.data["success"] is False
    assert response.data["errors"] is not None
    assert response.data["data"] is None


# ─── Signal test ──────────────────────────────────────
@pytest.mark.django_db
def test_signal_creates_log_on_book_create(author):
    initial_count = ActivityLog.objects.count()
    Book.objects.create(author=author, title="Signal Test Book", price=50)
    assert ActivityLog.objects.count() == initial_count + 1


# ─── Price validation ─────────────────────────────────
@pytest.mark.django_db
@pytest.mark.parametrize("price,expected_status", [
    (100, 201),
    (-1, 400),
    (0, 201),
])
def test_create_book_price_validation(api_client, author, price, expected_status):
    response = api_client.post("/api/integration/books/create/", {
        "title": "Price Test Book",
        "price": price,
        "author": author.id
    }, format='json')
    assert response.status_code == expected_status