# apps/reviews/serializers.py
from __future__ import annotations

"""
Review serializers — input validation and output formatting.

Responsibility:
    Input serializers validate incoming request data only.
    Output serializers format model instances for API responses.
    Zero business logic. Zero service calls. Zero DB queries.

Timestamp fields:
    TimestampFieldsMixin used on all output serializers that
    expose created_at or updated_at — never redefine manually.

N+1 prevention note:
    ReviewListSerializer.helpful_count and not_helpful_count
    call properties on the Review instance. These properties
    hit the DB if votes are not prefetched. The selector
    get_approved_reviews() always prefetches votes — views
    must always use that selector, never raw Review.objects.filter().
"""

from rest_framework import serializers

from apps.common.validators import phone_validator
from apps.core.mixins import TimestampFieldsMixin
from apps.reviews.models import Review, ReviewVote


class ReviewSubmitSerializer(serializers.Serializer):
    """
    Input — customer submitting a new review.

    order_item_id: PK of the OrderItem being reviewed.
                   Service validates ownership and delivery status.
    rating:        Integer 1-5. Validated here — no point calling
                   service with an out-of-range value.
    title:         Optional headline. Blank allowed.
    body:          Optional review text. Blank allowed.
    """

    order_item_id = serializers.IntegerField(
        min_value=1,
    )
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
    )
    title = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )
    body = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )


class ReviewVoteSerializer(serializers.Serializer):
    """
    Input — customer casting a helpful/not_helpful vote.

    vote: Must be exactly "helpful" or "not_helpful".
          Validated against ReviewVote.Vote choices.
    """

    vote = serializers.ChoiceField(
        choices=ReviewVote.Vote.choices,
    )


class ReviewerSerializer(serializers.Serializer):
    """
    Minimal user representation shown on public review list.

    Shows only first name for privacy — not full email.
    Computed from user.get_full_name() or email prefix as fallback.
    """

    display_name = serializers.SerializerMethodField()

    def get_display_name(self, obj) -> str:
        full_name = getattr(obj, "get_full_name", lambda: "")()
        if full_name and full_name.strip():
            return full_name.strip().split()[0]
        email = getattr(obj, "email", "")
        return email.split("@")[0] if email else "Customer"


class ReviewListSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
    """
    Output — single approved review on the public product page.

    helpful_count and not_helpful_count use Review properties.
    These require prefetch_related("votes") on the QuerySet —
    enforced by get_approved_reviews() selector.

    is_verified_purchase uses the Review.is_verified_purchase property.
    True when order_item_id is not null — no extra query needed.

    reviewer shows only first name for privacy.
    """

    reviewer         = ReviewerSerializer(source="user", read_only=True)
    helpful_count    = serializers.IntegerField(
        source="helpful_count",
        read_only=True,
    )
    not_helpful_count = serializers.IntegerField(
        source="not_helpful_count",
        read_only=True,
    )
    is_verified_purchase = serializers.BooleanField(
        source="is_verified_purchase",
        read_only=True,
    )

    class Meta:
        model  = Review
        fields = [
            "id",
            "reviewer",
            "rating",
            "title",
            "body",
            "is_verified_purchase",
            "helpful_count",
            "not_helpful_count",
            "created_at",
            "updated_at",
        ]


class EligibleItemSerializer(serializers.Serializer):
    """
    Output — single OrderItem the customer can review.

    Shown on the "Write a Review" prompt on the product page
    and on the dashboard Pending Reviews section.

    Changes from original:
        Added product_slug — needed for dashboard navigation link.
        Added product_image — needed for dashboard card display.

    product_image uses is_primary=True filter on product.images.
    Requires prefetch_related("product__images") on the QuerySet —
    enforced by get_all_reviewable_items() selector.
    Single-product eligible endpoint (EligibleItemsAPIView) must
    also prefetch or accept the extra query cost (small list).

    order_item_id:  What to send in ReviewSubmitSerializer.
    order_number:   Human-readable order reference.
    product_name:   Snapshot from OrderItem.product_name.
    product_slug:   For navigation link to product page.
    product_image:  Primary image absolute URL or None.
    purchased_at:   OrderItem.created_at — when they bought it.
    """

    order_item_id = serializers.IntegerField(source="pk")
    order_number  = serializers.CharField(source="order.order_number")
    product_name  = serializers.SerializerMethodField()
    product_slug  = serializers.CharField(source="product.slug")
    product_image = serializers.SerializerMethodField()
    purchased_at  = serializers.DateTimeField(source="created_at")

    def get_product_name(self,obj)-> str | None:
        return obj.product_name


    def get_product_image(self, obj) -> str | None:
        """
        Return absolute URL of primary product image.

        Requires request in serializer context for build_absolute_uri.
        Falls back to None if no primary image or no request context.
        Caller views must pass context={"request": request}.
        """
        request = self.context.get("request")
        if not request:
            return None
        image = obj.product.images.filter(is_primary=True).first()
        if image:
            return request.build_absolute_uri(image.image.url)
        return None


class ReviewSubmitResponseSerializer(TimestampFieldsMixin,
                                     serializers.ModelSerializer):
    """
    Output — response after successful review submission.

    Minimal — customer just needs confirmation their review
    was received and is pending moderation.
    """

    class Meta:
        model  = Review
        fields = [
            "id",
            "rating",
            "title",
            "is_approved",
            "created_at",
        ]


class UserReviewHistorySerializer(TimestampFieldsMixin,
                                   serializers.ModelSerializer):
    """
    Output — user's own submitted review for dashboard history.

    Only served to the review author via GET /api/reviews/my-reviews/.
    Never shown publicly — includes is_approved status which is
    internal moderation state.

    product_name, product_slug, product_image — for dashboard card.
    order_number — links review back to the originating order.

    product fields use default="" because Review.product is SET_NULL —
    product may have been discontinued after review was submitted.
    order_number uses default="" because order_item is also SET_NULL.

    product_image:
        Requires prefetch_related("product__images") on QuerySet.
        get_reviews_by_user() selector does this automatically.
    """

    product_name  = serializers.CharField(
        source="product.name",
        read_only=True,
        default="",
    )
    product_slug  = serializers.CharField(
        source="product.slug",
        read_only=True,
        default="",
    )
    product_image = serializers.SerializerMethodField()
    order_number  = serializers.CharField(
        source="order_item.order.order_number",
        read_only=True,
        default="",
    )

    def get_product_image(self, obj) -> str | None:
        """
        Return absolute URL of primary product image.
        Returns None if product deleted or no primary image.
        """
        request = self.context.get("request")
        if not request or not obj.product:
            return None
        image = obj.product.images.filter(is_primary=True).first()
        if image:
            return request.build_absolute_uri(image.image.url)
        return None

    class Meta:
        model  = Review
        fields = [
            "id",
            "product_name",
            "product_slug",
            "product_image",
            "order_number",
            "rating",
            "title",
            "body",
            "is_approved",
            "created_at",
            "updated_at",
        ]
# # apps/reviews/serializers.py
# from __future__ import annotations

# """
# Review serializers — input validation and output formatting.

# Responsibility:
#     Input serializers validate incoming request data only.
#     Output serializers format model instances for API responses.
#     Zero business logic. Zero service calls. Zero DB queries.

# Timestamp fields:
#     TimestampFieldsMixin used on all output serializers that
#     expose created_at or updated_at — never redefine manually.

# N+1 prevention note:
#     ReviewListSerializer.helpful_count and not_helpful_count
#     call properties on the Review instance. These properties
#     hit the DB if votes are not prefetched. The selector
#     get_approved_reviews() always prefetches votes — views
#     must always use that selector, never raw Review.objects.filter().
# """

# from rest_framework import serializers

# from apps.core.mixins import TimestampFieldsMixin
# from apps.reviews.models import Review, ReviewVote


# class ReviewSubmitSerializer(serializers.Serializer):
#     """
#     Input — customer submitting a new review.

#     order_item_id: PK of the OrderItem being reviewed.
#                    Service validates ownership and delivery status.
#     rating:        Integer 1-5. Validated here — no point calling
#                    service with an out-of-range value.
#     title:         Optional headline. Blank allowed.
#     body:          Optional review text. Blank allowed.
#     """

#     order_item_id = serializers.IntegerField(
#         min_value=1,
#     )
#     rating = serializers.IntegerField(
#         min_value=1,
#         max_value=5,
#     )
#     title = serializers.CharField(
#         max_length=100,
#         required=False,
#         allow_blank=True,
#         default="",
#     )
#     body = serializers.CharField(
#         required=False,
#         allow_blank=True,
#         default="",
#     )


# class ReviewVoteSerializer(serializers.Serializer):
#     """
#     Input — customer casting a helpful/not_helpful vote.

#     vote: Must be exactly "helpful" or "not_helpful".
#           Validated against ReviewVote.Vote choices.
#     """

#     vote = serializers.ChoiceField(
#         choices=ReviewVote.Vote.choices,
#     )


# class ReviewerSerializer(serializers.Serializer):
#     """
#     Minimal user representation shown on public review list.

#     Shows only first name for privacy — not full email.
#     Computed from user.get_full_name() or email prefix as fallback.
#     """

#     display_name = serializers.SerializerMethodField()

#     def get_display_name(self, obj) -> str:
#         full_name = getattr(obj, "get_full_name", lambda: "")()
#         if full_name and full_name.strip():
#             return full_name.strip().split()[0]
#         email = getattr(obj, "email", "")
#         return email.split("@")[0] if email else "Customer"


# class ReviewListSerializer(TimestampFieldsMixin, serializers.ModelSerializer):
#     """
#     Output — single approved review on the public product page.

#     helpful_count and not_helpful_count use Review properties.
#     These require prefetch_related("votes") on the QuerySet —
#     enforced by get_approved_reviews() selector.

#     is_verified_purchase uses the Review.is_verified_purchase property.
#     True when order_item_id is not null — no extra query needed.

#     reviewer shows only first name for privacy.
#     """

#     reviewer         = ReviewerSerializer(source="user", read_only=True)
#     helpful_count    = serializers.IntegerField(
#         source="helpful_count",
#         read_only=True,
#     )
#     not_helpful_count = serializers.IntegerField(
#         source="not_helpful_count",
#         read_only=True,
#     )
#     is_verified_purchase = serializers.BooleanField(
#         source="is_verified_purchase",
#         read_only=True,
#     )

#     class Meta:
#         model  = Review
#         fields = [
#             "id",
#             "reviewer",
#             "rating",
#             "title",
#             "body",
#             "is_verified_purchase",
#             "helpful_count",
#             "not_helpful_count",
#             "created_at",
#             "updated_at",
#         ]


# class EligibleItemSerializer(serializers.Serializer):
#     """
#     Output — single OrderItem the customer can review.

#     Shown on the "Write a Review" prompt on the product page.
#     Tells the customer which of their purchases is eligible.

#     order_item_id:  What to send in ReviewSubmitSerializer.
#     order_number:   Human-readable order reference.
#     product_name:   Snapshot from OrderItem.product_name.
#     purchased_at:   OrderItem.created_at — when they bought it.
#     """

#     order_item_id = serializers.IntegerField(source="pk")
#     order_number  = serializers.CharField(source="order.order_number")
#     product_name  = serializers.CharField(source="product_name")
#     purchased_at  = serializers.DateTimeField(source="created_at")


# class ReviewSubmitResponseSerializer(TimestampFieldsMixin,
#                                      serializers.ModelSerializer):
#     """
#     Output — response after successful review submission.

#     Minimal — customer just needs confirmation their review
#     was received and is pending moderation.
#     """

#     class Meta:
#         model  = Review
#         fields = [
#             "id",
#             "rating",
#             "title",
#             "is_approved",
#             "created_at",
#         ]