# apps/reviews/admin.py
from __future__ import annotations

"""
Reviews app — Django admin registration.

Design decisions:
    Reviews created exclusively via ReviewSubmitAPIView.
    has_add_permission=False on ReviewAdmin — no manual creation.
    Moderation happens via approve_reviews and reject_reviews actions.
    Both actions call ReviewService methods — never direct field edits.
    ReviewModerationLog: fully immutable — no add, change, delete.
    ReviewVote: readonly — vote data is customer-generated evidence.
"""

import logging

from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from apps.reviews.models import Review, ReviewVote, ReviewModerationLog
from apps.reviews.services.review_service import ReviewService
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.reviews")


# ─────────────────────────────────────────────────────────────────────────────
# INLINES
# ─────────────────────────────────────────────────────────────────────────────

class ReviewModerationLogInline(admin.TabularInline):
    """
    Immutable moderation history inline on Review change page.
    All fields readonly — ReviewModerationLog.save() raises ValueError on update.
    """
    model           = ReviewModerationLog
    extra           = 0
    can_delete      = False
    ordering        = ("-created_at",)
    readonly_fields = ("action", "moderated_by", "reason", "created_at")
    fields          = readonly_fields

    def has_add_permission(self, request, obj=None) -> bool:
        return False


class ReviewVoteInline(admin.TabularInline):
    """
    Read-only vote summary inline on Review change page.
    """
    model           = ReviewVote
    extra           = 0
    can_delete      = False
    readonly_fields = ("user", "vote", "created_at")
    fields          = readonly_fields

    def has_add_permission(self, request, obj=None) -> bool:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """
    Admin interface for Review moderation.

    Reviews are created via API only — has_add_permission=False.
    Moderation via approve_reviews and reject_reviews actions.
    Both call ReviewService — never direct field edits in admin.
    """

    list_display = [
        "id",
        "product",
        "user",
        "rating",
        "title",
        "is_approved",
        "is_verified_purchase",
        "created_at",
    ]
    list_filter = [
        "is_approved",
        "rating",
        "created_at",
    ]
    search_fields = [
        "user__email",
        "product__name",
        "title",
        "body",
    ]
    ordering      = ["-created_at"]
    list_per_page = 25
    inlines       = [ReviewModerationLogInline, ReviewVoteInline]

    readonly_fields = [
        "product",
        "user",
        "order_item",
        "rating",
        "title",
        "body",
        "is_approved",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (_("Review"), {
            "fields": (
                "product",
                "user",
                "order_item",
                "rating",
                "title",
                "body",
            ),
        }),
        (_("Moderation"), {
            "fields": (
                "is_approved",
                "created_at",
                "updated_at",
            ),
        }),
    )

    actions = ["approve_reviews", "reject_reviews"]

    def has_add_permission(self, request) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False

    @admin.display(description=_("Verified Purchase"), boolean=True)
    def is_verified_purchase(self, obj: Review) -> bool:
        return obj.is_verified_purchase

    @admin.action(description=_("Approve selected reviews ✓"))
    def approve_reviews(self, request, queryset):
        approved = skipped = 0
        for review in queryset:
            try:
                ReviewService.approve_review(
                    review=review,
                    moderated_by=request.user,
                )
                approved += 1
            except Exception as exc:
                skipped += 1
                logger.exception(
                    "ReviewAdmin.approve_reviews: error | "
                    "review_id=%s admin=%s",
                    review.pk,
                    request.user.pk,
                )
                self.message_user(
                    request,
                    _(f"Review #{review.pk}: {exc}"),
                    level=messages.ERROR,
                )
        if approved:
            self.message_user(
                request,
                _(f"{approved} review(s) approved and now publicly visible."),
                level=messages.SUCCESS,
            )

    @admin.action(description=_("Reject selected reviews ✗"))
    def reject_reviews(self, request, queryset):
        """
        Reject selected reviews.

        Note: This action uses a fixed rejection reason.
        For per-review rejection with custom reason, open the
        review detail page and use the reject action there.
        The admin note pattern (custom intermediate page) can
        be added as a future enhancement.
        """
        rejected = skipped = 0
        default_reason = "Does not meet community guidelines."
        for review in queryset:
            try:
                ReviewService.reject_review(
                    review=review,
                    moderated_by=request.user,
                    reason=default_reason,
                )
                rejected += 1
            except DomainError as exc:
                skipped += 1
                self.message_user(
                    request,
                    _(f"Review #{review.pk}: {exc}"),
                    level=messages.WARNING,
                )
            except Exception as exc:
                skipped += 1
                logger.exception(
                    "ReviewAdmin.reject_reviews: error | "
                    "review_id=%s admin=%s",
                    review.pk,
                    request.user.pk,
                )
        if rejected:
            self.message_user(
                request,
                _(f"{rejected} review(s) rejected."),
                level=messages.SUCCESS,
            )


# ─────────────────────────────────────────────────────────────────────────────
# REVIEW MODERATION LOG ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ReviewModerationLog)
class ReviewModerationLogAdmin(admin.ModelAdmin):
    """
    Fully immutable moderation audit trail.
    No add, change, or delete permitted.
    """

    list_display  = ["review", "action", "moderated_by", "created_at"]
    list_filter   = ["action", "created_at"]
    search_fields = ["review__product__name", "moderated_by__email"]
    readonly_fields = [
        "review", "action", "moderated_by", "reason", "created_at"
    ]

    def has_add_permission(self, request)            -> bool: return False
    def has_change_permission(self, request, obj=None) -> bool: return False
    def has_delete_permission(self, request, obj=None) -> bool: return False