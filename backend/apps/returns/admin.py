# apps/returns/admin.py
from __future__ import annotations

"""
Return admin — Django admin configuration for the returns app.

Admin handles all state transitions:
    approve_returns      PENDING → APPROVED
    reject_returns       PENDING → REJECTED (requires rejection_reason)
    mark_items_received  APPROVED → ITEM_RECEIVED
    initiate_refunds     ITEM_RECEIVED → REFUND_INITIATED
    complete_returns     REFUND_INITIATED → COMPLETED

All transitions call ReturnService methods — admin never mutates
status fields directly. This ensures all guards, timestamps, and
logging in the service layer fire correctly.

ReturnItemPhoto displayed as inline — admin sees photos alongside
the return request when reviewing customer evidence.

Design rules:
    - Admin actions call service methods, not model saves directly.
    - Feedback messages use modeladmin.message_user() with
      messages.SUCCESS / messages.ERROR / messages.WARNING.
    - Bulk actions report success count and error count.
    - Financial records (ReturnRequest, RefundTransaction linkage)
      are never deleted from admin — no delete_selected action.
"""

import logging
from decimal import Decimal, InvalidOperation
from typing import Any

from django.contrib import admin, messages
from django.db import models
from django.http import HttpRequest
from django.utils.html import format_html

from apps.core.exceptions import DomainError
from apps.returns.models import ReturnItemPhoto, ReturnRequest
from apps.returns.services.return_service import ReturnService

logger = logging.getLogger("apps.returns")


class ReturnItemPhotoInline(admin.TabularInline):
    """
    Inline display of customer-uploaded photos on ReturnRequest detail page.

    Read-only in admin — photos are evidence submitted by the customer
    and must not be altered by staff.
    Photo displayed as thumbnail for quick visual review.
    """

    model          = ReturnItemPhoto
    extra          = 0
    readonly_fields = ["thumbnail", "caption", "created_at"]
    fields          = ["thumbnail", "caption", "created_at"]
    can_delete      = False

    def thumbnail(self, obj: ReturnItemPhoto) -> str:
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height:120px; max-width:160px; '
                'object-fit:contain; border:1px solid #ddd; border-radius:4px;" />',
                obj.image.url,
            )
        return "—"

    thumbnail.short_description = "Photo"  # type: ignore[attr-defined]


@admin.register(ReturnRequest)
class ReturnRequestAdmin(admin.ModelAdmin):
    """
    ReturnRequest admin with full lifecycle action support.

    List display shows the most important fields for triage:
        - Return ID and order number for identification.
        - Reason and resolution for quick context.
        - Status with colour-coded badge.
        - Requested date for SLA tracking.

    Detail view shows all fields with appropriate read-only guards
    on financial and immutable fields.

    Inline photos visible on detail page — staff can see customer
    evidence without leaving the return request record.
    """

    # ── List display ──────────────────────────────────────────────────────────
    list_display = [
        "id",
        "order_link",
        "requested_by_email",
        "reason",
        "resolution_requested",
        "status_badge",
        "created_at",
        "approved_at",
        "completed_at",
    ]
    list_filter  = [
        "status",
        "reason",
        "resolution_requested",
        "created_at",
    ]
    search_fields = [
        "order__order_number",
        "requested_by__email",
        "rejection_reason",
    ]
    ordering      = ["-created_at"]
    date_hierarchy = "created_at"

    # ── Detail view ───────────────────────────────────────────────────────────
    readonly_fields = [
        "order",
        "order_item",
        "requested_by",
        "reason",
        "reason_detail",
        "resolution_requested",
        "created_at",
        "updated_at",
        "approved_at",
        "received_at",
        "completed_at",
    ]
    fieldsets = [
        (
            "Return Request",
            {
                "fields": [
                    "order",
                    "order_item",
                    "requested_by",
                    "reason",
                    "reason_detail",
                    "resolution_requested",
                    "created_at",
                    "updated_at",
                ]
            },
        ),
        (
            "Status & Review",
            {
                "fields": [
                    "status",
                    "reviewed_by",
                    "rejection_reason",
                    "approved_at",
                    "received_at",
                    "completed_at",
                ]
            },
        ),
    ]
    inlines = [ReturnItemPhotoInline]

    # Prevent deletion of return records — financial audit trail.
    def has_delete_permission(
        self, request: HttpRequest, obj: ReturnRequest | None = None
    ) -> bool:
        return False

    # ── Custom list display methods ───────────────────────────────────────────

    def order_link(self, obj: ReturnRequest) -> str:
        return format_html(
            '<a href="/admin/orders/order/?q={}">{}</a>',
            obj.order.order_number,
            obj.order.order_number,
        )

    order_link.short_description = "Order"  # type: ignore[attr-defined]

    def requested_by_email(self, obj: ReturnRequest) -> str:
        return getattr(obj.requested_by, "email", "—")

    requested_by_email.short_description = "Customer"  # type: ignore[attr-defined]

    def status_badge(self, obj: ReturnRequest) -> str:
        colours: dict[str, str] = {
            ReturnRequest.Status.PENDING:          "#f0ad4e",
            ReturnRequest.Status.APPROVED:         "#5bc0de",
            ReturnRequest.Status.REJECTED:         "#d9534f",
            ReturnRequest.Status.ITEM_RECEIVED:    "#5cb85c",
            ReturnRequest.Status.REFUND_INITIATED: "#337ab7",
            ReturnRequest.Status.COMPLETED:        "#3c763d",
        }
        colour = colours.get(obj.status, "#999")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:3px;font-size:11px;font-weight:bold;">{}</span>',
            colour,
            obj.get_status_display(),
        )

    status_badge.short_description = "Status"  # type: ignore[attr-defined]

    # ── Admin actions ─────────────────────────────────────────────────────────

    actions = [
        "approve_returns",
        "reject_returns",
        "mark_items_received",
        "initiate_refunds",
        "complete_returns",
    ]

    @admin.action(description="✅ Approve selected return requests")
    def approve_returns(
        self,
        request: HttpRequest,
        queryset: models.QuerySet,
    ) -> None:
        success = 0
        errors  = 0
        for return_request in queryset:
            try:
                ReturnService.approve_return(
                    return_request=return_request,
                    reviewed_by=request.user,
                )
                success += 1
            except DomainError as exc:
                errors += 1
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: {exc.message}",
                    level=messages.ERROR,
                )
        if success:
            self.message_user(
                request,
                f"{success} return request(s) approved successfully.",
                level=messages.SUCCESS,
            )
        if errors:
            self.message_user(
                request,
                f"{errors} return request(s) could not be approved.",
                level=messages.WARNING,
            )

    @admin.action(description="❌ Reject selected return requests")
    def reject_returns(
        self,
        request: HttpRequest,
        queryset: models.QuerySet,
    ) -> None:
        """
        Rejection requires a reason. Admin must enter it in the
        rejection_reason field on the detail page before using this action,
        or this action will report an error for requests with empty reason.
        """
        success = 0
        errors  = 0
        for return_request in queryset:
            rejection_reason = request.POST.get(
                "rejection_reason", ""
            ) or return_request.rejection_reason
            try:
                ReturnService.reject_return(
                    return_request=return_request,
                    reviewed_by=request.user,
                    rejection_reason=rejection_reason,
                )
                success += 1
            except DomainError as exc:
                errors += 1
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: {exc.message}",
                    level=messages.ERROR,
                )
        if success:
            self.message_user(
                request,
                f"{success} return request(s) rejected.",
                level=messages.SUCCESS,
            )
        if errors:
            self.message_user(
                request,
                f"{errors} return request(s) could not be rejected. "
                f"Ensure rejection_reason is filled on the record first.",
                level=messages.WARNING,
            )

    @admin.action(description="📦 Mark selected returns as item received")
    def mark_items_received(
        self,
        request: HttpRequest,
        queryset: models.QuerySet,
    ) -> None:
        success = 0
        errors  = 0
        for return_request in queryset:
            try:
                ReturnService.mark_item_received(
                    return_request=return_request,
                    reviewed_by=request.user,
                )
                success += 1
            except DomainError as exc:
                errors += 1
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: {exc.message}",
                    level=messages.ERROR,
                )
        if success:
            self.message_user(
                request,
                f"{success} return(s) marked as item received.",
                level=messages.SUCCESS,
            )
        if errors:
            self.message_user(
                request,
                f"{errors} return(s) could not be updated.",
                level=messages.WARNING,
            )

    @admin.action(description="💸 Initiate refund for selected returns")
    def initiate_refunds(
        self,
        request: HttpRequest,
        queryset: models.QuerySet,
    ) -> None:
        """
        Initiates refund for each selected ITEM_RECEIVED return.
        Refund amount defaults to the full order total_price.
        For partial refunds, use the detail page directly.
        """
        success = 0
        errors  = 0
        for return_request in queryset:
            try:
                refund_amount = return_request.order_item.subtotal
                ReturnService.initiate_refund(
                    return_request=return_request,
                    initiated_by=request.user,
                    refund_amount=refund_amount,
                    reason="customer_request",
                )
                success += 1
            except DomainError as exc:
                errors += 1
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: {exc.message}",
                    level=messages.ERROR,
                )
            except Exception as exc:
                errors += 1
                logger.exception(
                    "ReturnRequestAdmin.initiate_refunds: unexpected error | "
                    "return_id=%s error=%s",
                    return_request.pk,
                    str(exc),
                )
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: Unexpected error — "
                    f"check server logs.",
                    level=messages.ERROR,
                )
        if success:
            self.message_user(
                request,
                f"{success} refund(s) initiated successfully.",
                level=messages.SUCCESS,
            )
        if errors:
            self.message_user(
                request,
                f"{errors} refund(s) could not be initiated.",
                level=messages.WARNING,
            )

    @admin.action(description="✔️ Complete selected returns")
    def complete_returns(
        self,
        request: HttpRequest,
        queryset: models.QuerySet,
    ) -> None:
        """
        Completes returns in REFUND_INITIATED status.
        Locates the most recent INITIATED RefundTransaction for each
        return and marks it COMPLETED, then closes the ReturnRequest.
        """
        success = 0
        errors  = 0
        for return_request in queryset:
            refund_transaction = (
                return_request.order.refunds
                .filter(status="initiated")
                .order_by("-created_at")
                .first()
            )
            if refund_transaction is None:
                errors += 1
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: No initiated refund "
                    f"transaction found for this return.",
                    level=messages.ERROR,
                )
                continue
            try:
                ReturnService.complete_return(
                    return_request=return_request,
                    refund_transaction=refund_transaction,
                    completed_by=request.user,
                )
                success += 1
            except DomainError as exc:
                errors += 1
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: {exc.message}",
                    level=messages.ERROR,
                )
            except Exception as exc:
                errors += 1
                logger.exception(
                    "ReturnRequestAdmin.complete_returns: unexpected error | "
                    "return_id=%s error=%s",
                    return_request.pk,
                    str(exc),
                )
                self.message_user(
                    request,
                    f"Return #{return_request.pk}: Unexpected error — "
                    f"check server logs.",
                    level=messages.ERROR,
                )
        if success:
            self.message_user(
                request,
                f"{success} return(s) completed successfully.",
                level=messages.SUCCESS,
            )
        if errors:
            self.message_user(
                request,
                f"{errors} return(s) could not be completed.",
                level=messages.WARNING,
            )