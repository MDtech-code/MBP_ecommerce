import os
import django
from decimal import Decimal

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.integration_test.models import Author, Book, ActivityLog


# ✅ 15 Well-Known Authors and Their Famous Books
authors_books_data = {
    "Robert C. Martin": {
        "email": "unclebob@example.com",
        "books": [
            "Clean Code",
            "Clean Architecture",
            "Agile Software Development",
            "The Clean Coder",
        ],
    },
    "Martin Fowler": {
        "email": "fowler@example.com",
        "books": [
            "Refactoring",
            "Patterns of Enterprise Application Architecture",
            "Domain-Specific Languages",
            "UML Distilled",
        ],
    },
    "Kent Beck": {
        "email": "kentbeck@example.com",
        "books": [
            "Test-Driven Development",
            "Extreme Programming Explained",
            "Implementation Patterns",
        ],
    },
    "Eric Evans": {
        "email": "evans@example.com",
        "books": [
            "Domain-Driven Design",
        ],
    },
    "Andrew Hunt": {
        "email": "andyhunt@example.com",
        "books": [
            "The Pragmatic Programmer",
            "Pragmatic Thinking and Learning",
        ],
    },
    "David Thomas": {
        "email": "dthomas@example.com",
        "books": [
            "The Pragmatic Programmer",
            "Programming Ruby",
        ],
    },
    "Donald Knuth": {
        "email": "knuth@example.com",
        "books": [
            "The Art of Computer Programming Vol 1",
            "The Art of Computer Programming Vol 2",
            "The Art of Computer Programming Vol 3",
        ],
    },
    "Bjarne Stroustrup": {
        "email": "bjarne@example.com",
        "books": [
            "The C++ Programming Language",
            "Programming: Principles and Practice Using C++",
        ],
    },
    "Brian Kernighan": {
        "email": "kernighan@example.com",
        "books": [
            "The C Programming Language",
            "The Practice of Programming",
        ],
    },
    "Dennis Ritchie": {
        "email": "ritchie@example.com",
        "books": [
            "The C Programming Language",
        ],
    },
    "James Clear": {
        "email": "jamesclear@example.com",
        "books": [
            "Atomic Habits",
        ],
    },
    "Cal Newport": {
        "email": "calnewport@example.com",
        "books": [
            "Deep Work",
            "Digital Minimalism",
        ],
    },
    "Robert Sedgewick": {
        "email": "sedgewick@example.com",
        "books": [
            "Algorithms",
            "Algorithms in C",
        ],
    },
    "Thomas H. Cormen": {
        "email": "cormen@example.com",
        "books": [
            "Introduction to Algorithms",
        ],
    },
    "Steve McConnell": {
        "email": "mcconnell@example.com",
        "books": [
            "Code Complete",
            "Rapid Development",
        ],
    },
}


print("🚀 Starting database population...\n")

total_books = 0
total_authors = 0

for author_name, data in authors_books_data.items():

    author, created = Author.objects.get_or_create(
        email=data["email"],
        defaults={"name": author_name},
    )

    if created:
        total_authors += 1
        ActivityLog.objects.create(
            message=f"Author '{author_name}' was added to the system."
        )

    for index, book_title in enumerate(data["books"]):

        book, book_created = Book.objects.get_or_create(
            author=author,
            title=book_title,
            defaults={
                "price": Decimal("39.99") + Decimal(index * 5)
            },
        )

        if book_created:
            total_books += 1
            ActivityLog.objects.create(
                message=f"Book '{book_title}' by {author_name} was added with price ${book.price}."
            )


ActivityLog.objects.create(
    message=f"Database population completed successfully. "
            f"{total_authors} authors and {total_books} books were added."
)

print("✅ Database populated successfully!")
print(f"   Authors added: {total_authors}")
print(f"   Books added: {total_books}")
print("   Activity logs created ✅")