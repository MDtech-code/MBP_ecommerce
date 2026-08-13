# apps/reviews/views.py
from __future__ import annotations

"""
Review views — HTTP layer for the reviews app.

All views inherit from BaseAPIView.
All business logic delegated to ReviewService.
All DB reads delegated to selectors.
Views handle: auth, request parsing, response formatting.

Endpoints:
    POST /api/reviews/
         Submit a verified purchase review.
         Auth: IsAuthenticated + IsVerified.

    GET  /api/reviews/eligible/?product_id=<id>
         List OrderItems the requesting user can review
         for a specific product.
         Auth: IsAuthenticated.

    GET  /api/reviews/pending/
         List ALL OrderItems the requesting user can review
         across all their delivered orders.
         No product filter — used for dashboard.
         Auth: IsAuthenticated.

    GET  /api/reviews/my-reviews/
         List all reviews the requesting user has submitted.
         Includes pending moderation reviews.
         Auth: IsAuthenticated.

    GET  /api/products/<slug>/reviews/
         Public paginated list of approved reviews for a product.
         No auth required — public endpoint.

    POST /api/reviews/<id>/vote/
         Cast or update a helpful/not_helpful vote.
         Auth: IsAuthenticated.
"""

import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.request import Request

from apps.core.api.views import BaseAPIView
from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.core.pagination import get_pagination_params, build_pagination_meta
from apps.core.permissions import IsVerified

from apps.reviews.models import Review
from apps.reviews.serializers import (
    ReviewSubmitSerializer,
    ReviewSubmitResponseSerializer,
    ReviewVoteSerializer,
    ReviewListSerializer,
    EligibleItemSerializer,
    UserReviewHistorySerializer,
)
from apps.reviews.services.review_service import ReviewService
from apps.reviews.selectors.review_selectors import (
    get_approved_reviews_for_product_slug,
    get_review_by_id,
    get_reviewable_items,
    get_all_reviewable_items,
    get_reviews_by_user,
)
from apps.products.models import Product

logger = logging.getLogger("apps.reviews")


# ─────────────────────────────────────────────────────────────────────────────
# SUBMIT REVIEW
# ─────────────────────────────────────────────────────────────────────────────

class ReviewSubmitAPIView(BaseAPIView):
    """
    POST /api/reviews/

    Customer submits a verified purchase review.
    Service validates ownership and delivery status.
    All new reviews start with is_approved=False — pending moderation.
    """

    permission_classes = [IsAuthenticated, IsVerified]

    def post(self, request: Request):

        serializer = ReviewSubmitSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message=_("Review submission failed."),
                errors=serializer.errors,
                status_code=400,
            )

        review = ReviewService.submit_review(
            user=request.user,
            order_item_id=serializer.validated_data["order_item_id"],
            rating=serializer.validated_data["rating"],
            title=serializer.validated_data.get("title", ""),
            body=serializer.validated_data.get("body", ""),
        )

        logger.info(
            "ReviewSubmitAPIView: created | "
            "review_id=%s user=%s request_id=%s",
            review.pk,
            request.user.pk,
            getattr(request, "id", "n/a"),
        )

        return self.created_response(
            data=ReviewSubmitResponseSerializer(review).data,
            message=_(
                "Your review has been submitted and is pending moderation. "
                "It will appear on the product page once approved."
            ),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ELIGIBLE ITEMS — per product (existing, updated to pass request context)
# ─────────────────────────────────────────────────────────────────────────────

class EligibleItemsAPIView(BaseAPIView):
    """
    GET /api/reviews/eligible/?product_id=<id>

    Returns OrderItems the requesting user can review for a product.
    Frontend uses this to decide whether to show the "Write a Review"
    button and which order_item_id to pass in the submit request.

    Returns empty list if user has no eligible purchases — not a 404.
    product_id query param is required.

    Change from original:
        EligibleItemSerializer now receives context={"request": request}
        so get_product_image() can build absolute image URLs.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request):

        product_id = request.query_params.get("product_id")
        if not product_id:
            raise DomainError(
                "product_id query parameter is required.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        try:
            product = Product.objects.get(pk=product_id)
        except Product.DoesNotExist:
            return self.not_found_response(
                message=_("Product not found.")
            )

        items = get_reviewable_items(request.user, product)

        logger.info(
            "EligibleItemsAPIView: OK | "
            "product_id=%s user=%s eligible_count=%s request_id=%s",
            product_id,
            request.user.pk,
            items.count(),
            getattr(request, "id", "n/a"),
        )

        return self.list_response(
            data=EligibleItemSerializer(
                items,
                many=True,
                context={"request": request},  # ← ADDED for image URLs
            ).data,
            message=_("Eligible items retrieved successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# PENDING REVIEWS — all reviewable items across all products (NEW)
# ─────────────────────────────────────────────────────────────────────────────

class PendingReviewsAPIView(BaseAPIView):
    """
    GET /api/reviews/pending/

    Returns ALL OrderItems the requesting user can review across
    all their delivered orders. No product filter.

    Used by the dashboard Pending Reviews section — user sees every
    product they have purchased and delivered but not yet reviewed.

    Reuses EligibleItemSerializer — same shape as eligible endpoint
    so frontend can use identical component for both contexts.

    Auth: IsAuthenticated (no IsVerified — display only, no mutation).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request):

        items = get_all_reviewable_items(request.user)

        logger.info(
            "PendingReviewsAPIView: OK | "
            "user=%s pending_count=%s request_id=%s",
            request.user.pk,
            items.count(),
            getattr(request, "id", "n/a"),
        )

        return self.list_response(
            data=EligibleItemSerializer(
                items,
                many=True,
                context={"request": request},
            ).data,
            message=_("Pending reviews retrieved successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# USER REVIEW HISTORY (NEW)
# ─────────────────────────────────────────────────────────────────────────────

class UserReviewHistoryAPIView(BaseAPIView):
    """
    GET /api/reviews/my-reviews/

    Returns all reviews submitted by the requesting user.
    Includes both approved and pending moderation reviews.

    Only the review author sees their own pending reviews.
    Public endpoints (ProductReviewListAPIView) only return
    is_approved=True reviews.

    Used by dashboard Review History section.

    Auth: IsAuthenticated (no IsVerified — read only).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request):

        reviews = get_reviews_by_user(request.user)

        logger.info(
            "UserReviewHistoryAPIView: OK | "
            "user=%s review_count=%s request_id=%s",
            request.user.pk,
            reviews.count(),
            getattr(request, "id", "n/a"),
        )

        return self.list_response(
            data=UserReviewHistorySerializer(
                reviews,
                many=True,
                context={"request": request},
            ).data,
            message=_("Your reviews retrieved successfully."),
        )


# ─────────────────────────────────────────────────────────────────────────────
# PUBLIC PRODUCT REVIEW LIST
# ─────────────────────────────────────────────────────────────────────────────

class ProductReviewListAPIView(BaseAPIView):
    """
    GET /api/products/<slug>/reviews/

    Public paginated list of approved reviews for a product.
    No authentication required — visible to all visitors.
    Ordered by helpfulness (most helpful votes first), then newest.
    Supports ?rating=<1-5> filter and standard pagination params.
    """

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str):

        # ── Pagination ─────────────────────────────────────────────────────

        params = get_pagination_params(request, default_page_size=10)
        if not params.is_valid:
            return self.error_response(
                message=_("Invalid pagination parameters."),
            )

        # ── Fetch product ──────────────────────────────────────────────────

        try:
            reviews_qs = get_approved_reviews_for_product_slug(slug)
        except Product.DoesNotExist:
            return self.not_found_response(
                message=_("Product not found.")
            )

        # ── Optional rating filter ─────────────────────────────────────────

        rating_filter = request.query_params.get("rating")
        if rating_filter:
            try:
                rating_int = int(rating_filter)
                if 1 <= rating_int <= 5:
                    reviews_qs = reviews_qs.filter(rating=rating_int)
            except (ValueError, TypeError):
                pass

        # ── Paginate ───────────────────────────────────────────────────────

        total = reviews_qs.count()
        offset = (params.page - 1) * params.page_size
        reviews = reviews_qs[offset: offset + params.page_size]

        meta = build_pagination_meta(
            params.page,
            params.page_size,
            total,
        )

        logger.info(
            "ProductReviewListAPIView: OK | "
            "slug=%s page=%s total=%s request_id=%s",
            slug,
            params.page,
            total,
            getattr(request, "id", "n/a"),
        )

        return self.list_response(
            data=ReviewListSerializer(reviews, many=True).data,
            message=_("Reviews retrieved successfully."),
            meta=meta,
        )


# ─────────────────────────────────────────────────────────────────────────────
# VOTE ON REVIEW
# ─────────────────────────────────────────────────────────────────────────────

class ReviewVoteAPIView(BaseAPIView):
    """
    POST /api/reviews/<id>/vote/

    Cast or update a helpful / not_helpful vote on a review.
    Customers cannot vote on their own reviews.
    Changing a vote updates the existing row — no duplicate votes.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, review_id: int):

        # ── Fetch review ───────────────────────────────────────────────────

        try:
            review = get_review_by_id(review_id, request.user)
        except Review.DoesNotExist:
            return self.not_found_response(
                message=_("Review not found.")
            )

        # ── Validate input ─────────────────────────────────────────────────

        serializer = ReviewVoteSerializer(data=request.data)
        if not serializer.is_valid():
            return self.error_response(
                message=_("Invalid vote data."),
                errors=serializer.errors,
                status_code=400,
            )

        ReviewService.vote_on_review(
            user=request.user,
            review=review,
            vote=serializer.validated_data["vote"],
        )

        logger.info(
            "ReviewVoteAPIView: OK | "
            "review_id=%s user=%s vote=%s request_id=%s",
            review_id,
            request.user.pk,
            serializer.validated_data["vote"],
            getattr(request, "id", "n/a"),
        )

        return self.success_response(
            message=_("Vote recorded successfully."),
        )
# # apps/reviews/views.py
# from __future__ import annotations

# """
# Review views — HTTP layer for the reviews app.

# All views inherit from BaseAPIView.
# All business logic delegated to ReviewService.
# All DB reads delegated to selectors.
# Views handle: auth, request parsing, response formatting.

# Endpoints:
#     POST /api/reviews/
#          Submit a verified purchase review.
#          Auth: IsAuthenticated + IsVerified.

#     GET  /api/reviews/eligible/?product_id=<id>
#          List OrderItems the requesting user can review
#          for a specific product.
#          Auth: IsAuthenticated.

#     GET  /api/products/<slug>/reviews/
#          Public paginated list of approved reviews for a product.
#          No auth required — public endpoint.

#     POST /api/reviews/<id>/vote/
#          Cast or update a helpful/not_helpful vote.
#          Auth: IsAuthenticated.
# """

# import logging

# from django.utils.translation import gettext_lazy as _
# from rest_framework.permissions import IsAuthenticated, AllowAny
# from rest_framework.request import Request

# from apps.core.api.views import BaseAPIView
# from apps.core.exceptions import DomainError
# from apps.core.error_codes import ErrorCode
# from apps.core.pagination import get_pagination_params, build_pagination_meta
# from apps.core.permissions import IsVerified

# from apps.reviews.models import Review
# from apps.reviews.serializers import (
#     ReviewSubmitSerializer,
#     ReviewSubmitResponseSerializer,
#     ReviewVoteSerializer,
#     ReviewListSerializer,
#     EligibleItemSerializer,
# )
# from apps.reviews.services.review_service import ReviewService
# from apps.reviews.selectors.review_selectors import (
#     get_approved_reviews_for_product_slug,
#     get_review_by_id,
#     get_reviewable_items,
# )
# from apps.products.models import Product

# logger = logging.getLogger("apps.reviews")


# # ─────────────────────────────────────────────────────────────────────────────
# # SUBMIT REVIEW
# # ─────────────────────────────────────────────────────────────────────────────

# class ReviewSubmitAPIView(BaseAPIView):
#     """
#     POST /api/reviews/

#     Customer submits a verified purchase review.
#     Service validates ownership and delivery status.
#     All new reviews start with is_approved=False — pending moderation.
#     """

#     permission_classes = [IsAuthenticated, IsVerified]

#     def post(self, request: Request):

#         serializer = ReviewSubmitSerializer(data=request.data)
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Review submission failed."),
#                 errors=serializer.errors,
#                 status_code=400,
#             )

#         review = ReviewService.submit_review(
#             user=request.user,
#             order_item_id=serializer.validated_data["order_item_id"],
#             rating=serializer.validated_data["rating"],
#             title=serializer.validated_data.get("title", ""),
#             body=serializer.validated_data.get("body", ""),
#         )

#         logger.info(
#             "ReviewSubmitAPIView: created | "
#             "review_id=%s user=%s request_id=%s",
#             review.pk,
#             request.user.pk,
#             getattr(request, "id", "n/a"),
#         )

#         return self.created_response(
#             data=ReviewSubmitResponseSerializer(review).data,
#             message=_(
#                 "Your review has been submitted and is pending moderation. "
#                 "It will appear on the product page once approved."
#             ),
#         )


# # ─────────────────────────────────────────────────────────────────────────────
# # ELIGIBLE ITEMS
# # ─────────────────────────────────────────────────────────────────────────────

# class EligibleItemsAPIView(BaseAPIView):
#     """
#     GET /api/reviews/eligible/?product_id=<id>

#     Returns OrderItems the requesting user can review for a product.
#     Frontend uses this to decide whether to show the "Write a Review"
#     button and which order_item_id to pass in the submit request.

#     Returns empty list if user has no eligible purchases — not a 404.
#     product_id query param is required.
#     """

#     permission_classes = [IsAuthenticated]

#     def get(self, request: Request):

#         product_id = request.query_params.get("product_id")
#         if not product_id:
#             raise DomainError(
#                 "product_id query parameter is required.",
#                 code=ErrorCode.VALIDATION_ERROR,
#                 status_code=400,
#             )

#         try:
#             product = Product.objects.get(pk=product_id)
#         except Product.DoesNotExist:
#             return self.not_found_response(
#                 message=_("Product not found.")
#             )

#         items = get_reviewable_items(request.user, product)

#         logger.info(
#             "EligibleItemsAPIView: OK | "
#             "product_id=%s user=%s eligible_count=%s request_id=%s",
#             product_id,
#             request.user.pk,
#             items.count(),
#             getattr(request, "id", "n/a"),
#         )

#         return self.success_response(
#             data=EligibleItemSerializer(items, many=True).data,
#             message=_("Eligible items retrieved successfully."),
#         )


# # ─────────────────────────────────────────────────────────────────────────────
# # PUBLIC PRODUCT REVIEW LIST
# # ─────────────────────────────────────────────────────────────────────────────

# class ProductReviewListAPIView(BaseAPIView):
#     """
#     GET /api/products/<slug>/reviews/

#     Public paginated list of approved reviews for a product.
#     No authentication required — visible to all visitors.
#     Ordered by helpfulness (most helpful votes first), then newest.
#     Supports ?rating=<1-5> filter and standard pagination params.
#     """

#     permission_classes = [AllowAny]

#     def get(self, request: Request, slug: str):

#         # ── Pagination ─────────────────────────────────────────────────────

#         params = get_pagination_params(request, default_page_size=10)
#         if not params.is_valid:
#             return self.error_response(
#                 message=_("Invalid pagination parameters."),
#             )

#         # ── Fetch product ──────────────────────────────────────────────────

#         try:
#             reviews_qs = get_approved_reviews_for_product_slug(slug)
#         except Product.DoesNotExist:
#             return self.not_found_response(
#                 message=_("Product not found.")
#             )

#         # ── Optional rating filter ─────────────────────────────────────────

#         rating_filter = request.query_params.get("rating")
#         if rating_filter:
#             try:
#                 rating_int = int(rating_filter)
#                 if 1 <= rating_int <= 5:
#                     reviews_qs = reviews_qs.filter(rating=rating_int)
#             except (ValueError, TypeError):
#                 pass

#         # ── Paginate ───────────────────────────────────────────────────────

#         total = reviews_qs.count()
#         offset = (params.page - 1) * params.page_size
#         reviews = reviews_qs[offset: offset + params.page_size]

#         meta = build_pagination_meta(
#             params.page,
#             params.page_size,
#             total,
#         )

#         logger.info(
#             "ProductReviewListAPIView: OK | "
#             "slug=%s page=%s total=%s request_id=%s",
#             slug,
#             params.page,
#             total,
#             getattr(request, "id", "n/a"),
#         )

#         return self.success_response(
#             data=ReviewListSerializer(reviews, many=True).data,
#             message=_("Reviews retrieved successfully."),
#             meta=meta,
#         )


# # ─────────────────────────────────────────────────────────────────────────────
# # VOTE ON REVIEW
# # ─────────────────────────────────────────────────────────────────────────────

# class ReviewVoteAPIView(BaseAPIView):
#     """
#     POST /api/reviews/<id>/vote/

#     Cast or update a helpful / not_helpful vote on a review.
#     Customers cannot vote on their own reviews.
#     Changing a vote updates the existing row — no duplicate votes.
#     """

#     permission_classes = [IsAuthenticated]

#     def post(self, request: Request, review_id: int):

#         # ── Fetch review ───────────────────────────────────────────────────

#         try:
#             review = get_review_by_id(review_id, request.user)
#         except Review.DoesNotExist:
#             return self.not_found_response(
#                 message=_("Review not found.")
#             )

#         # ── Validate input ─────────────────────────────────────────────────

#         serializer = ReviewVoteSerializer(data=request.data)
#         if not serializer.is_valid():
#             return self.error_response(
#                 message=_("Invalid vote data."),
#                 errors=serializer.errors,
#                 status_code=400,
#             )

#         ReviewService.vote_on_review(
#             user=request.user,
#             review=review,
#             vote=serializer.validated_data["vote"],
#         )

#         logger.info(
#             "ReviewVoteAPIView: OK | "
#             "review_id=%s user=%s vote=%s request_id=%s",
#             review_id,
#             request.user.pk,
#             serializer.validated_data["vote"],
#             getattr(request, "id", "n/a"),
#         )

#         return self.success_response(
#             message=_("Vote recorded successfully."),
#         )