# apps/reviews/selectors/review_selectors.py
from __future__ import annotations

"""
Review selectors — all database reads for the reviews app.

Responsibility:
    Every query that touches Review, ReviewVote, or
    ReviewModerationLog lives here.
    Returns model instances or QuerySets only.
    Zero business logic. Zero HTTP concerns. Zero DRF imports.

Ownership enforcement:
    Customer-facing selectors always scope by user to prevent
    one customer seeing or acting on another customer's data.

N+1 prevention:
    All list selectors prefetch votes so helpful_count and
    not_helpful_count properties work without extra queries.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db.models import Count, QuerySet

from apps.reviews.models import Review, ReviewVote
from apps.orders.models import OrderItem
from apps.products.models import Product

logger = logging.getLogger("apps.reviews")


def get_reviewable_items(user, product: Product) -> QuerySet:
    """
    Return OrderItems the user can still review for a specific product.

    Eligibility rules enforced here:
        1. OrderItem belongs to the requesting user.
        2. Order status is DELIVERED — cannot review undelivered items.
        3. No review already submitted for this OrderItem.
           (order_item OneToOne — review__isnull=True means not yet reviewed)
        4. OrderItem is for the specific product being reviewed.

    Args:
        user:    Authenticated user requesting the list.
        product: Product instance the customer wants to review.

    Returns:
        QuerySet of OrderItem instances the user can review.
        Empty QuerySet if none eligible — never raises.
    """
    return (
        OrderItem.objects
        .select_related("order", "product")
        .filter(
            order__user=user,
            order__status="delivered",
            product=product,
            review__isnull=True,
        )
    )


def get_approved_reviews(product: Product) -> QuerySet:
    """
    Return all approved reviews for a product, ordered by helpfulness.

    Prefetches votes for helpful_count and not_helpful_count properties.
    Annotates helpful_count directly in SQL for ordering — avoids
    Python-level sorting which would require loading all votes.

    Args:
        product: Product instance whose reviews to retrieve.

    Returns:
        QuerySet of approved Review instances, most helpful first.
    """
    return (
        Review.objects
        .select_related("user")
        .prefetch_related("votes")
        .filter(
            product=product,
            is_approved=True,
        )
        .annotate(
            helpful_votes=Count(
                "votes",
                filter=__import__("django.db.models", fromlist=["Q"]).Q(
                    votes__vote=ReviewVote.Vote.HELPFUL
                ),
            )
        )
        .order_by("-helpful_votes", "-created_at")
    )


def get_approved_reviews_for_product_slug(slug: str) -> QuerySet:
    """
    Return approved reviews by product slug.

    Used by the public product review list endpoint where the
    URL contains the product slug, not the product pk.

    Args:
        slug: Product slug from URL.

    Returns:
        QuerySet of approved Review instances.

    Raises:
        Product.DoesNotExist — caller returns 404.
    """
    from apps.products.models import Product as ProductModel
    product = ProductModel.objects.get(slug=slug)
    return get_approved_reviews(product)


def get_review_by_id(review_id: int, user) -> Review:
    """
    Fetch a single review by pk, scoped to the requesting user.

    Used before voting to confirm the review exists.
    Does NOT scope by user — reviews are public records.
    User scoping only applies to submit and vote actions.

    Args:
        review_id: Review primary key.
        user:      Authenticated user (used for vote ownership check
                   in the service layer, not here).

    Returns:
        Review instance with votes prefetched.

    Raises:
        Review.DoesNotExist — caller returns 404.
    """
    return (
        Review.objects
        .prefetch_related("votes")
        .select_related("user", "product", "order_item")
        .get(pk=review_id)
    )


def get_existing_vote(review: Review, user) -> ReviewVote | None:
    """
    Return the user's existing vote on a review, or None.

    Used by ReviewService.vote_on_review() to decide
    whether to create a new vote or update an existing one.

    Args:
        review: Review instance being voted on.
        user:   Authenticated user casting the vote.

    Returns:
        ReviewVote instance or None if user has not voted yet.
    """
    return (
        ReviewVote.objects
        .filter(review=review, user=user)
        .first()
    )


def get_order_item_for_review(order_item_id: int, user) -> OrderItem:
    """
    Fetch an OrderItem and verify it belongs to the requesting user.

    Used by ReviewService.submit_review() to validate the
    purchase before creating a review.

    Loads order and product in one query to avoid N+1 on
    the eligibility checks in the service layer.

    Args:
        order_item_id: OrderItem primary key from review submission.
        user:          Authenticated user submitting the review.

    Returns:
        OrderItem with order and product loaded.

    Raises:
        OrderItem.DoesNotExist — caller returns 404.
                                  Ownership enforced by user filter —
                                  valid item belonging to another user
                                  raises DoesNotExist, not 403.
                                  Prevents order item enumeration attacks.
    """
    return (
        OrderItem.objects
        .select_related("order", "product")
        .get(pk=order_item_id, order__user=user)
    )