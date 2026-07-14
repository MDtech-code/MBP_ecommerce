# apps/reviews/models.py
from __future__ import annotations
import logging

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.common.models import TimeStampedModel
from apps.products.models import Product
from apps.orders.models import OrderItem

logger = logging.getLogger("apps.reviews")


class Review(TimeStampedModel):
    """
    Customer product review — tied to a verified purchase via order_item.

    Design decisions:
    - product uses SET_NULL — review survives product discontinuation.
    - order_item OneToOne — one review per purchase line (Daraz model).
    - is_approved defaults False — all reviews moderated before display.
    - Moderation history tracked in ReviewModerationLog.
    - Helpful votes tracked in ReviewVote.
    - user CASCADE — review deleted if user deletes account (GDPR intent).
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews",
        verbose_name=_("product"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("reviewer"),
    )
    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="review",
        verbose_name=_("verified purchase item"),
    )
    rating = models.SmallIntegerField(
        _("rating"),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
    )
    title = models.CharField(
        _("title"),
        max_length=100,
        blank=True,
        default="",
    )
    body = models.TextField(
        _("body"),
        blank=True,
        default="",
    )
    is_approved = models.BooleanField(
        _("approved"),
        default=False,
        help_text=_(
            "Review shown to customers only after approval. "
            "Moderation history tracked in ReviewModerationLog."
        ),
    )

    class Meta:
        verbose_name        = _("customer review")
        verbose_name_plural = _("customer reviews")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["product",  "is_approved"]),
            models.Index(fields=["user",     "created_at"]),
            models.Index(fields=["rating"]),
        ]

    def save(self, *args, **kwargs) -> None:
        super().save(*args, **kwargs)
        logger.debug(
            "Review saved: product=%s user=%s rating=%s approved=%s",
            self.product_id,
            self.user_id,
            self.rating,
            self.is_approved,
        )

    # ─── Properties ───────────────────────────────────────────────────────────

    @property
    def is_verified_purchase(self) -> bool:
        """
        True when review is linked to a real delivered OrderItem.
        Shown as Verified Purchase badge on product page.
        """
        return self.order_item_id is not None

    @property
    def helpful_count(self) -> int:
        """Requires prefetch_related('votes') to avoid N+1."""
        return self.votes.filter(vote=ReviewVote.Vote.HELPFUL).count()

    @property
    def not_helpful_count(self) -> int:
        """Requires prefetch_related('votes') to avoid N+1."""
        return self.votes.filter(vote=ReviewVote.Vote.NOT_HELPFUL).count()

    def __str__(self) -> str:
        user_email   = getattr(self.user,    "email", "deleted user")
        product_name = getattr(self.product, "name",  "deleted product")
        return f"{self.rating}★ by {user_email} for {product_name}"


class ReviewVote(TimeStampedModel):
    """
    Customer vote on whether a review was helpful.

    One vote per user per review — unique_together enforces this.
    Used to sort reviews by helpfulness on product page.
    Changing vote = update existing row (no duplicate).
    """

    class Vote(models.TextChoices):
        HELPFUL     = 'helpful',     _('Helpful')
        NOT_HELPFUL = 'not_helpful', _('Not Helpful')

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='votes',
        verbose_name=_('review'),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='review_votes',
        verbose_name=_('voter'),
    )
    vote = models.CharField(
        _('vote'),
        max_length=15,
        choices=Vote.choices,
    )

    class Meta:
        verbose_name        = _('review vote')
        verbose_name_plural = _('review votes')
        unique_together     = [['review', 'user']]
        ordering            = ['-created_at']

    def __str__(self) -> str:
        return (
            f"{self.get_vote_display()} on review#{self.review_id} "
            f"by {self.user.email}"
        )


class ReviewModerationLog(models.Model):
    """
    Immutable audit trail of every moderation action on a review.

    Records who approved or rejected a review, when, and why.
    INSERT only — save() guard prevents updates.
    """

    class Action(models.TextChoices):
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')
        FLAGGED  = 'flagged',  _('Flagged for Re-review')

    review = models.ForeignKey(
        Review,
        on_delete=models.CASCADE,
        related_name='moderation_logs',
        verbose_name=_('review'),
    )
    action = models.CharField(
        _('action'),
        max_length=10,
        choices=Action.choices,
    )
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderation_actions',
        verbose_name=_('moderated by'),
        help_text=_('Null means system-automated moderation.'),
    )
    reason = models.TextField(
        _('reason'),
        blank=True,
        default='',
        help_text=_('Required when action is REJECTED or FLAGGED.'),
    )
    created_at = models.DateTimeField(
        _('actioned at'),
        auto_now_add=True,
        db_index=True,
    )

    class Meta:
        verbose_name        = _('review moderation log')
        verbose_name_plural = _('review moderation logs')
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['review',      'created_at']),
            models.Index(fields=['moderated_by', 'created_at']),
        ]

    def save(self, *args, **kwargs) -> None:
        if self.pk:
            raise ValueError(
                "ReviewModerationLog records are immutable "
                "and cannot be updated."
            )
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return (
            f"{self.get_action_display()} — review#{self.review_id} "
            f"by {getattr(self.moderated_by, 'email', 'system')}"
        )
