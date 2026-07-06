from decimal import Decimal
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from apps.common.models import TimeStampedModel




class UserInteractionLog(TimeStampedModel):
    """
    High-throughput event log. This table is ingested by machine learning pipelines
    to train collaborative filtering algorithms or generate embeddings.
    """
    class EventType(models.TextChoices):
        VIEW_PRODUCT = 'VIEW_PRODUCT', _('Viewed Product Page')
        ADD_TO_CART = 'ADD_TO_CART', _('Added to Cart')
        REMOVE_FROM_CART = 'REMOVE_FROM_CART', _('Removed from Cart')
        ADD_TO_WISHLIST = 'ADD_TO_WISHLIST', _('Added to Wishlist')
        PURCHASED = 'PURCHASED', _('Purchased Product')
        SEARCH_QUERY = 'SEARCH_QUERY', _('Executed Search')

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True, help_text=_("For anonymous guest tracking"))
    
    event_type = models.CharField(max_length=20, choices=EventType.choices, db_index=True)
    product_id = models.CharField(max_length=100, null=True, blank=True, db_index=True)
    search_query = models.CharField(max_length=255, null=True, blank=True)
    
    metadata = models.JSONField(blank=True, null=True, help_text=_("e.g., {'time_spent_seconds': 45, 'device': 'mobile'}"))

    class Meta:
        verbose_name = _("User Interaction Log")
        verbose_name_plural = _("User Interaction Logs")
        indexes = [
            models.Index(fields=['product_id', 'event_type']),
            models.Index(fields=['user', 'event_type', '-created_at']),
        ]


class PersonalizedRecommendation(TimeStampedModel):
    """
    Stores pre-computed or real-time ML recommendations for rapid frontend querying.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recommendations')
    recommended_product_id = models.CharField(max_length=100, db_index=True)
    score = models.FloatField(help_text=_("Confidence score from ML model (0.0 to 1.0)"))
    model_version = models.CharField(max_length=50, help_text=_("e.g., 'collab-filtering-v2.1'"))
    is_clicked = models.BooleanField(default=False)

    class Meta:
        verbose_name = _("Personalized Recommendation")
        verbose_name_plural = _("Personalized Recommendations")
        unique_together = ('user', 'recommended_product_id', 'model_version')
        ordering = ['-score']