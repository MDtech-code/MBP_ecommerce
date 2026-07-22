# apps/reviews/services/review_service.py
from __future__ import annotations

"""
Review service — business logic for review submission and voting.

Responsibility:
    ReviewService.submit_review() — validates eligibility and creates Review.
    ReviewService.vote_on_review() — creates or updates ReviewVote.
    ReviewService.approve_review() — admin moderation, creates log entry.
    ReviewService.reject_review()  — admin moderation, creates log entry.

    All eligibility validation lives here, not in serializers or views.
    Zero DRF imports. Zero HTTP concerns.

Verified purchase enforcement:
    submit_review() fetches the OrderItem and verifies:
        1. OrderItem belongs to the requesting user.
        2. Order status is DELIVERED.
        3. No existing review for this OrderItem (OneToOne).
        4. OrderItem.product matches the product being reviewed.
    If any check fails → DomainError raised, no Review created.

Moderation:
    All new reviews start with is_approved=False.
    approve_review() and reject_review() are called from Django admin
    actions. Each creates an immutable ReviewModerationLog entry.

Vote idempotency:
    vote_on_review() uses get_existing_vote() to check for an
    existing vote. If found, updates the vote field in place.
    unique_together on ReviewVote prevents duplicate rows.
    This means a customer can change their vote — helpful → not_helpful.

Dependency direction:
    models → selectors → services → views
"""

import logging

from django.db import transaction

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.reviews.models import Review, ReviewVote, ReviewModerationLog
from apps.reviews.selectors.review_selectors import (
    get_order_item_for_review,
    get_existing_vote,
)
from apps.orders.models import Order

logger = logging.getLogger("apps.reviews")


class ReviewService:
    """
    Business operations for Review lifecycle management.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    """

    # ─────────────────────────────────────────────────────────────────────
    # SUBMIT REVIEW
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def submit_review(
        *,
        user,
        order_item_id: int,
        rating: int,
        title: str = "",
        body: str = "",
    ) -> Review:
        """
        Submit a verified purchase review for a delivered order item.

        Validates purchase ownership, delivery status, and uniqueness
        before creating the review. All new reviews start unapproved.

        Args:
            user:          Authenticated customer submitting the review.
            order_item_id: PK of the OrderItem being reviewed.
            rating:        Integer 1-5.
            title:         Optional review headline.
            body:          Optional review body text.

        Returns:
            Created Review instance with is_approved=False.

        Raises:
            DomainError 404 — OrderItem not found or not owned by user.
            DomainError 400 — Order not yet delivered.
            DomainError 409 — Review already submitted for this item.
        """

        # ── Fetch and verify ownership ─────────────────────────────────────

        try:
            order_item = get_order_item_for_review(order_item_id, user)
        except Exception:
            raise DomainError(
                "Order item not found or does not belong to your account.",
                code=ErrorCode.NOT_FOUND,
                status_code=400,
            )

        # ── Check order is delivered ───────────────────────────────────────

        if order_item.order.status != Order.Status.DELIVERED:
            raise DomainError(
                "You can only review items from delivered orders. "
                "Your order has not been delivered yet.",
                code=ErrorCode.ORDER_NOT_DELIVERED,
                status_code=400,
            )

        # ── Check no existing review for this order item ───────────────────

        if hasattr(order_item, "review") and order_item.review is not None:
            raise DomainError(
                "You have already submitted a review for this item. "
                "Each purchase can only be reviewed once.",
                code=ErrorCode.REVIEW_ALREADY_EXISTS,
                status_code=409,
            )

        # Also check via DB to handle edge case where related object
        # accessor cache may not be fresh
        if Review.objects.filter(order_item=order_item).exists():
            raise DomainError(
                "You have already submitted a review for this item. "
                "Each purchase can only be reviewed once.",
                code=ErrorCode.REVIEW_ALREADY_EXISTS,
                status_code=409,
            )

        # ── Create review ──────────────────────────────────────────────────

        with transaction.atomic():
            review = Review.objects.create(
                product=order_item.product,
                user=user,
                order_item=order_item,
                rating=rating,
                title=title,
                body=body,
                is_approved=False,
            )

        logger.info(
            "ReviewService.submit_review: created | "
            "review_id=%s user=%s product=%s rating=%s order_item=%s",
            review.pk,
            user.pk,
            order_item.product_id,
            rating,
            order_item_id,
        )

        return review

    # ─────────────────────────────────────────────────────────────────────
    # VOTE ON REVIEW
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def vote_on_review(
        *,
        user,
        review: Review,
        vote: str,
    ) -> ReviewVote:
        """
        Submit or update a helpful / not_helpful vote on a review.

        Customers cannot vote on their own reviews.
        Changing vote is allowed — updates existing row.
        unique_together(review, user) prevents duplicate rows at DB level.

        Args:
            user:   Authenticated customer casting the vote.
            review: Review instance being voted on.
            vote:   ReviewVote.Vote value: "helpful" or "not_helpful".

        Returns:
            ReviewVote instance (created or updated).

        Raises:
            DomainError 400 — user is the review author.
            DomainError 400 — review is not approved (cannot vote on
                              reviews that are not publicly visible).
        """

        # ── Cannot vote on own review ──────────────────────────────────────

        if review.user_id == user.pk:
            raise DomainError(
                "You cannot vote on your own review.",
                code=ErrorCode.CANNOT_VOTE_OWN_REVIEW,
                status_code=400,
            )

        # ── Can only vote on approved reviews ──────────────────────────────

        if not review.is_approved:
            raise DomainError(
                "This review is not available for voting.",
                code=ErrorCode.REVIEW_NOT_APPROVED,
                status_code=400,
            )

        # ── Create or update vote ──────────────────────────────────────────

        existing_vote = get_existing_vote(review, user)

        if existing_vote:
            existing_vote.vote = vote
            existing_vote.save(update_fields=["vote"])
            review_vote = existing_vote
            logger.info(
                "ReviewService.vote_on_review: updated | "
                "vote_id=%s user=%s review=%s vote=%s",
                existing_vote.pk,
                user.pk,
                review.pk,
                vote,
            )
        else:
            review_vote = ReviewVote.objects.create(
                review=review,
                user=user,
                vote=vote,
            )
            logger.info(
                "ReviewService.vote_on_review: created | "
                "vote_id=%s user=%s review=%s vote=%s",
                review_vote.pk,
                user.pk,
                review.pk,
                vote,
            )

        return review_vote

    # ─────────────────────────────────────────────────────────────────────
    # APPROVE REVIEW
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def approve_review(
        *,
        review: Review,
        moderated_by,
    ) -> Review:
        """
        Approve a review — makes it publicly visible.

        Called from Django admin action approve_reviews().
        Creates an immutable ReviewModerationLog entry.
        Idempotent — approving an already-approved review
        still creates a log entry (admin may re-approve after flag).

        Args:
            review:       Review instance to approve.
            moderated_by: Staff User performing the moderation.

        Returns:
            Updated Review instance with is_approved=True.
        """

        with transaction.atomic():
            review.is_approved = True
            review.save(update_fields=["is_approved"])

            ReviewModerationLog.objects.create(
                review=review,
                action=ReviewModerationLog.Action.APPROVED,
                moderated_by=moderated_by,
                reason="",
            )

        logger.info(
            "ReviewService.approve_review: approved | "
            "review_id=%s moderated_by=%s",
            review.pk,
            getattr(moderated_by, "email", "system"),
        )

        return review

    # ─────────────────────────────────────────────────────────────────────
    # REJECT REVIEW
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def reject_review(
        *,
        review: Review,
        moderated_by,
        reason: str,
    ) -> Review:
        """
        Reject a review — keeps it hidden from public view.

        Called from Django admin action reject_reviews().
        Reason is required — admin must explain the rejection.
        Creates an immutable ReviewModerationLog entry.

        Args:
            review:       Review instance to reject.
            moderated_by: Staff User performing the moderation.
            reason:       Required explanation for rejection.

        Returns:
            Updated Review instance with is_approved=False.

        Raises:
            DomainError 400 — reason is empty.
        """

        if not reason or not reason.strip():
            raise DomainError(
                "A reason is required when rejecting a review. "
                "The reason is stored in the moderation log.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        with transaction.atomic():
            review.is_approved = False
            review.save(update_fields=["is_approved"])

            ReviewModerationLog.objects.create(
                review=review,
                action=ReviewModerationLog.Action.REJECTED,
                moderated_by=moderated_by,
                reason=reason.strip(),
            )

        logger.info(
            "ReviewService.reject_review: rejected | "
            "review_id=%s moderated_by=%s reason=%s",
            review.pk,
            getattr(moderated_by, "email", "system"),
            reason[:100],
        )

        return review