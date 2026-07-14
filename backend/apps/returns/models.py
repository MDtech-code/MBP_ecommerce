# apps/returns/models.py
from __future__ import annotations
import logging

from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel
from apps.orders.models import Order, OrderItem

logger = logging.getLogger("apps.returns")


class ReturnRequest(TimeStampedModel):
    """
    Customer-initiated return or exchange request.

    Separate from RefundTransaction — return is a logistics event,
    refund is a financial event. Return triggers refund but they
    are tracked independently.

    Status flow:
        PENDING → APPROVED → ITEM_RECEIVED → REFUND_INITIATED → COMPLETED
        PENDING → REJECTED (invalid reason / outside return window)
    """

    class Reason(models.TextChoices):
        WRONG_ITEM      = 'wrong_item',      _('Wrong Item Delivered')
        DAMAGED         = 'damaged',         _('Item Damaged / Defective')
        NOT_AS_DESCRIBED = 'not_described',  _('Not as Described')
        CHANGED_MIND    = 'changed_mind',    _('Changed Mind')
        OTHER           = 'other',           _('Other')

    class Resolution(models.TextChoices):
        REFUND   = 'refund',   _('Refund to Original Payment Method')
        EXCHANGE = 'exchange', _('Exchange for Same Item')
        STORE_CREDIT = 'store_credit', _('Store Credit')

    class Status(models.TextChoices):
        PENDING          = 'pending',          _('Pending Review')
        APPROVED         = 'approved',         _('Approved — Awaiting Item')
        REJECTED         = 'rejected',         _('Rejected')
        ITEM_RECEIVED    = 'item_received',    _('Item Received at Warehouse')
        REFUND_INITIATED = 'refund_initiated', _('Refund Initiated')
        COMPLETED        = 'completed',        _('Completed')

    order = models.ForeignKey(
        Order,
        on_delete=models.PROTECT,
        related_name="return_requests",
        verbose_name=_("order"),
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.PROTECT,
        related_name="return_requests",
        verbose_name=_("order item"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="return_requests",
        verbose_name=_("requested by"),
    )
    reason = models.CharField(
        _("reason"),
        max_length=20,
        choices=Reason.choices,
    )
    reason_detail = models.TextField(
        _("reason detail"),
        blank=True,
        default="",
        help_text=_("Customer explanation in their own words."),
    )
    resolution_requested = models.CharField(
        _("resolution requested"),
        max_length=15,
        choices=Resolution.choices,
        default=Resolution.REFUND,
    )
    status = models.CharField(
        _("status"),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_returns",
        verbose_name=_("reviewed by admin"),
    )
    rejection_reason = models.TextField(
        _("rejection reason"),
        blank=True,
        default="",
        help_text=_("Required when status=REJECTED."),
    )
    approved_at  = models.DateTimeField(_("approved at"),       null=True, blank=True)
    received_at  = models.DateTimeField(_("item received at"),  null=True, blank=True)
    completed_at = models.DateTimeField(_("completed at"),      null=True, blank=True)

    class Meta:
        verbose_name        = _("return request")
        verbose_name_plural = _("return requests")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["order",  "status"]),
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"Return #{self.pk} — {self.order.order_number} "
            f"({self.get_status_display()})"
        )


class ReturnItemPhoto(TimeStampedModel):
    """
    Customer-uploaded photo evidence for return request.
    Required for DAMAGED and NOT_AS_DESCRIBED reasons.
    """
    return_request = models.ForeignKey(
        ReturnRequest,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("return request"),
    )
    image = models.ImageField(
        _("photo"),
        upload_to="returns/%Y/%m/",
    )
    caption = models.CharField(
        _("caption"),
        max_length=255,
        blank=True,
        default="",
    )

    class Meta:
        verbose_name        = _("return item photo")
        verbose_name_plural = _("return item photos")
        ordering            = ["created_at"]

    def __str__(self) -> str:
        return f"Photo for return #{self.return_request_id}"