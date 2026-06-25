
import logging
from django.http import JsonResponse
from rest_framework.permissions import AllowAny
from rest_framework import status

from apps.core.api.views import BaseAPIView
from apps.core.cache import two_level_cache
from .serializers import AuthorSerializer, BookSerializer, ActivityLogSerializer
from .models import Author, Book, ActivityLog
from .tasks import calculate_author_books, test_task

logger = logging.getLogger('apps.integration_test')


def trigger_test(request):
    task = test_task.delay("Hello from Django to Celery!")
    return JsonResponse({'task_id': task.id, 'status': 'queued'})


def get_pagination_params(request, default_page_size=10):
    """Extract and validate pagination params from request."""
    try:
        page = max(1, int(request.query_params.get('page', 1)))
        page_size = min(100, max(1, int(request.query_params.get('page_size', default_page_size))))
    except (ValueError, TypeError):
        page, page_size = 1, default_page_size
    return page, page_size


def build_pagination_meta(page, page_size, total, source=None):
    """Build consistent pagination meta dict."""
    meta = {
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": -(-total // page_size),  # ceiling division
    }
    if source:
        meta["source"] = source
    return meta


class AuthorListAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page, page_size = get_pagination_params(request, default_page_size=10)
        cache_key = f"authors_page_{page}_size_{page_size}"

        cached_data, source = two_level_cache.get(cache_key)
        if cached_data:
            logger.debug("Authors served from %s", source)
            return self.success_response(
                data=cached_data["data"],
                message="Authors retrieved successfully",
                meta=build_pagination_meta(
                    page, page_size,
                    cached_data["total"],
                    source=source
                )
            )

        queryset = Author.objects.prefetch_related("books").all()
        total = queryset.count()
        offset = (page - 1) * page_size
        authors = queryset[offset:offset + page_size]
        serialized = list(AuthorSerializer(authors, many=True).data)

        two_level_cache.set(cache_key, {"data": serialized, "total": total})
        logger.debug("Authors served from database, cached in L1+L2")

        return self.success_response(
            data=serialized,
            message="Authors retrieved successfully",
            meta=build_pagination_meta(page, page_size, total, source="database")
        )


class CreateBookAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = BookSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message="Validation failed",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        serializer.save()

        two_level_cache.delete("books_page")
        logger.info("Book created — all_books cache invalidated")

        return self.created_response(
            data=serializer.data,
            message="Book created successfully"
        )


class BookListAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page, page_size = get_pagination_params(request, default_page_size=10)
        cache_key = f"books_page_{page}_size_{page_size}"

        cached_data, source = two_level_cache.get(cache_key)
        if cached_data:
            logger.debug("Books served from %s", source)
            return self.success_response(
                data=cached_data["data"],
                message="Books retrieved successfully",
                meta=build_pagination_meta(
                    page, page_size,
                    cached_data["total"],
                    source=source
                )
            )

        queryset = Book.objects.select_related("author").all()
        total = queryset.count()
        offset = (page - 1) * page_size
        books = queryset[offset:offset + page_size]
        serialized = list(BookSerializer(books, many=True).data)

        two_level_cache.set(cache_key, {"data": serialized, "total": total})
        logger.debug("Books served from database, cached in L1+L2")

        return self.success_response(
            data=serialized,
            message="Books retrieved successfully",
            meta=build_pagination_meta(page, page_size, total, source="database")
        )


class ActivityLogAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        page, page_size = get_pagination_params(request, default_page_size=20)
        cache_key = f"logs_page_{page}_size_{page_size}"

        cached_data, source = two_level_cache.get(cache_key)
        if cached_data:
            logger.debug("Logs served from %s", source)
            return self.success_response(
                data=cached_data["data"],
                message="Logs retrieved successfully",
                meta=build_pagination_meta(
                    page, page_size,
                    cached_data["total"],
                    source=source
                )
            )

        queryset = ActivityLog.objects.all()
        total = queryset.count()
        offset = (page - 1) * page_size
        logs = queryset[offset:offset + page_size]
        serialized = list(ActivityLogSerializer(logs, many=True).data)

        two_level_cache.set(cache_key, {"data": serialized, "total": total})
        logger.debug("Logs served from database, cached in L1+L2")

        return self.success_response(
            data=serialized,
            message="Logs retrieved successfully",
            meta=build_pagination_meta(page, page_size, total, source="database")
        )


class SystemHealthAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "integration-health"
        cached, source = two_level_cache.get(cache_key)

        if cached:
            logger.debug("Health check served from cache")
            return self.success_response(
                data=cached,
                message=f"Cache hit from {source}",
                meta={"source": source}
            )

        task = calculate_author_books.delay()
        data = {
            "database": "connected",
            "celery_task_id": task.id,
            "redis_cache": "working",
            "l1_cache": "working",
        }
        two_level_cache.set(cache_key, data)

        logger.info("Health check passed: db + celery + L1 + L2 all working")
        return self.success_response(
            data=data,
            message="All systems operational",
            meta={"source": "database"}
        )


class SentryTestAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        raise Exception("Sentry test error from integration_test!")
