
import logging
from django.core.cache import cache
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, CreateAPIView

from apps.core.api.views import BaseAPIView
from .serializers import AuthorSerializer, BookSerializer, ActivityLogSerializer
from .models import Author, Book, ActivityLog
from .tasks import calculate_author_books
from apps.core.cache import two_level_cache

logger = logging.getLogger('apps.integration_test')


class AuthorListAPIView(ListAPIView):
    permission_classes = [AllowAny]
    queryset = Author.objects.prefetch_related("books").all()
    serializer_class = AuthorSerializer


class CreateBookAPIView(CreateAPIView):
    permission_classes = [AllowAny]
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def perform_create(self, serializer):
        serializer.save()
        # cache.delete("all_books")
        two_level_cache.delete("all_books")
        logger.info("Book created, cache invalidated")


class BookListAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "all_books"
        # data = cache.get(cache_key)
        data, source = two_level_cache.get(cache_key)

        if data:
            logger.debug("Books served from Redis cache")
            return Response({"source": source, "books": data})

        books = Book.objects.select_related("author").all()
        serialized = BookSerializer(books, many=True).data
        # cache.set(cache_key, serialized, timeout=300)
        two_level_cache.set(cache_key, serialized)

        logger.debug("Books served from database, cached in L1+L2")
        return Response({"source": "database", "books": serialized})


class ActivityLogAPIView(ListAPIView):
    permission_classes = [AllowAny]
    queryset = ActivityLog.objects.all()
    serializer_class = ActivityLogSerializer


class SystemHealthAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cache_key = "integration-health"
        # cached = cache.get(cache_key)
        cached, source = two_level_cache.get(cache_key)

        if cached:
            logger.debug("Health check served from cache")
            return self.success_response(data={**cached,"served_from": source}, message=f"Cache hit from {source}")

        task = calculate_author_books.delay()
        data = {
            "database": "connected",
            "celery_task_id": task.id,
            "redis_cache": "working",
            "l1_cache": "working", 
            "served_from": "database"
        }
        # cache.set(cache_key, data, 60)
        two_level_cache.set(cache_key, data)

        logger.info("Health check passed: db + celery + L1 + L2 all working")
        return self.success_response(data=data, message="All systems operational")

class SentryTestAPIView(BaseAPIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # deliberately raise an error to test Sentry
        raise Exception("Sentry test error from integration_test!")
# from django.core.cache import cache

# from rest_framework.generics import (
#     ListAPIView
# )
# from rest_framework.permissions import AllowAny

# from rest_framework.response import Response
# from rest_framework.views import APIView
# from rest_framework.generics import CreateAPIView

# from .serializers import BookSerializer


# from .models import (
#     Author,
#     Book,
#     ActivityLog
# )

# from .serializers import (
#     AuthorSerializer,
#     BookSerializer,
#     ActivityLogSerializer
# )

# from .tasks import calculate_author_books



# class AuthorListAPIView(ListAPIView):
#     permission_classes=[AllowAny]

#     queryset = Author.objects.prefetch_related(
#         "books"
#     ).all()

#     serializer_class = AuthorSerializer


# class CreateBookAPIView(CreateAPIView):

#     permission_classes = [AllowAny]

#     queryset = Book.objects.all()

#     serializer_class = BookSerializer

#     def perform_create(self, serializer):
#         serializer.save()
#         cache.delete("all_books")



# class BookListAPIView(APIView):


#     permission_classes = [AllowAny]


#     def get(self, request):


#         cache_key = "all_books"



#         data = cache.get(cache_key)


#         if data:


#             return Response({

#                 "source":"redis",

#                 "books":data

#             })



#         books = Book.objects.select_related(
#             "author"
#         ).all()



#         serialized = BookSerializer(
#             books,
#             many=True
#         ).data



#         cache.set(

#             cache_key,

#             serialized,

#             timeout=300

#         )


#         return Response({

#             "source":"database",

#             "books":serialized

#         })




# class ActivityLogAPIView(ListAPIView):
#     permission_classes=[AllowAny]
#     queryset = ActivityLog.objects.all()

#     serializer_class = ActivityLogSerializer



# class SystemHealthAPIView(APIView):

#     permission_classes = [AllowAny] 
#     def get(self, request):


#         cache_key = "integration-health"



#         cached = cache.get(cache_key)


#         if cached:

#             return Response(
#                 {
#                     "cache":
#                     "redis",

#                     "data":
#                     cached
#                 }
#             )


#         task = calculate_author_books.delay()



#         data = {

#             "database":
#             "connected",

#             "celery_task_id":
#             task.id,


#             "redis_cache":
#             "working"
#         }



#         cache.set(
#             cache_key,
#             data,
#             60
#         )


#         return Response(data)