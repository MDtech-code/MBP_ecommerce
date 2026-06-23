from apps.core.api.serializers import BaseModelSerializer
from .models import Author, Book, ActivityLog
from rest_framework import serializers

class ActivityLogSerializer(BaseModelSerializer):
    class Meta:
        model = ActivityLog
        fields = ["id", "message", "created_at"]


class BookSerializer(BaseModelSerializer):
    author_name = serializers.CharField(
        source="author.name",
        read_only=True
    )
    price = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        min_value=0  # ← rejects negative prices
    )

    class Meta:
        model = Book
        fields = [
            "id", "title", "price",
            "author", "author_name",
            "created_at", "updated_at"
        ]
        extra_kwargs = {
            'author': {'write_only': True}
        }


class AuthorSerializer(BaseModelSerializer):
    total_books = serializers.IntegerField(
        source="books.count",
        read_only=True
    )
    books = BookSerializer(many=True, read_only=True)

    class Meta:
        model = Author
        fields = [
            "id", "name", "email",
            "total_books", "books",
            "created_at", "updated_at"
        ]


# from rest_framework import serializers

# from .models import (
#     Author,
#     Book,
#     ActivityLog
# )


# class ActivityLogSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = ActivityLog
#         fields = [
#             "id",
#             "message",
#             "created_at"
#         ]



# class BookSerializer(serializers.ModelSerializer):

#     author_name = serializers.CharField(
#         source="author.name",
#         read_only=True
#     )

#     class Meta:
#         model = Book
#         fields = [
#             "id",
#             "title",
#             "price",
#             "author",        # ← add this for write
#             "author_name",   # ← keep this for read
#             "created_at"
#         ]
#         extra_kwargs = {
#             'author': {'write_only': True}  # only used on create, not shown in list
#         }



# class AuthorSerializer(serializers.ModelSerializer):

#     total_books = serializers.IntegerField(
#         source="books.count",
#         read_only=True
#     )


#     books = BookSerializer(
#         many=True,
#         read_only=True
#     )


#     class Meta:

#         model = Author

#         fields = [
#             "id",
#             "name",
#             "email",
#             "total_books",
#             "books"
#         ]