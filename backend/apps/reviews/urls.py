# apps/reviews/urls.py
from django.urls import path

from apps.reviews.views import (
    ReviewSubmitAPIView,
    EligibleItemsAPIView,
    ProductReviewListAPIView,
    ReviewVoteAPIView,
)

app_name = "reviews"

urlpatterns = [
    # ── Customer actions ──────────────────────────────────────────────────
    path(
        "",
        ReviewSubmitAPIView.as_view(),
        name="review-submit",
    ),
    path(
        "eligible/",
        EligibleItemsAPIView.as_view(),
        name="review-eligible",
    ),
    path(
        "<int:review_id>/vote/",
        ReviewVoteAPIView.as_view(),
        name="review-vote",
    ),
]

# Product review list lives in products/urls.py:
# path("products/<slug:slug>/reviews/", ProductReviewListAPIView.as_view())
# Registered there because the URL is product-scoped, not review-scoped.