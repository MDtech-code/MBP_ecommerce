# apps/payments/admin.py
from __future__ import annotations

"""
Payment admin — Django admin for PaymentTransaction, RefundTransaction,
and WebhookLog.

Design rules:
    PaymentTransactionAdmin — fully readonly. Financial audit record.
        No create, no edit, no delete from admin.
        Admin can view all transactions for investigation purposes.

    RefundTransactionAdmin — readonly fields for financial data.
        One action: mark_refunds_completed — manually completes
        an INITIATED refund after admin has done the bank transfer.
        No delete permission.

    WebhookLogAdmin — fully readonly. Evidence record.
        No create, no edit, no delete from admin.
        Admin can see every gateway callback including fraudulent ones.
"""

import logging

from django.contrib import admin, messages
from django.http import HttpRequest

from apps.payments.models import PaymentTransaction, RefundTransaction, WebhookLog

logger = logging.getLogger("apps.payments")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """
    PaymentTransaction — read-only financial audit view.

    No mutations allowed from admin. Status changes happen via:
        - Logistics webhook (COD → SUCCESS on DELIVERED).
        - Payment webhook Celery task (online → SUCCESS/FAILED).
        - Order cancellation service (PENDING → FAILED on cancel).
    """

    list_display = [
        "id",
        "order_link",
        "gateway",
        "status",
        "amount_pkr",
        "transaction_reference",
        "idempotency_key",
        "created_at",
    ]
    list_filter  = [
        "gateway",
        "status",
        "created_at",
    ]
    search_fields = [
        "order__order_number",
        "transaction_reference",
        "user__email",
    ]
    ordering       = ["-created_at"]
    readonly_fields = [
        "order",
        "user",
        "gateway",
        "status",
        "amount_pkr",
        "transaction_reference",
        "idempotency_key",
        "error_message",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: PaymentTransaction | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: PaymentTransaction | None = None
    ) -> bool:
        return False

    def order_link(self, obj: PaymentTransaction) -> str:
        from django.utils.html import format_html
        return format_html(
            '<a href="/admin/orders/order/?q={}">{}</a>',
            obj.order.order_number,
            obj.order.order_number,
        )

    order_link.short_description = "Order"  # type: ignore[attr-defined]


@admin.register(RefundTransaction)
class RefundTransactionAdmin(admin.ModelAdmin):
    """
    RefundTransaction — admin with manual complete action.

    Admin uses mark_refunds_completed after physically transferring
    money to the customer via bank/Easypaisa.
    clean() guards on the model prevent over-refunding.
    """

    list_display = [
        "id",
        "order_link",
        "amount_pkr",
        "reason",
        "status",
        "initiated_by",
        "completed_at",
        "created_at",
    ]
    list_filter  = [
        "status",
        "reason",
        "created_at",
    ]
    search_fields = [
        "order__order_number",
        "original_transaction__transaction_reference",
    ]
    ordering       = ["-created_at"]
    readonly_fields = [
        "original_transaction",
        "order",
        "initiated_by",
        "amount_pkr",
        "reason",
        "reason_detail",
        "completed_at",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"

    def has_delete_permission(
        self, request: HttpRequest, obj: RefundTransaction | None = None
    ) -> bool:
        return False

    def order_link(self, obj: RefundTransaction) -> str:
        from django.utils.html import format_html
        return format_html(
            '<a href="/admin/orders/order/?q={}">{}</a>',
            obj.order.order_number,
            obj.order.order_number,
        )

    order_link.short_description = "Order"  # type: ignore[attr-defined]

    actions = ["mark_refunds_completed"]

    @admin.action(description="✔️ Mark selected refunds as completed")
    def mark_refunds_completed(
        self,
        request: HttpRequest,
        queryset,
    ) -> None:
        """
        Manually mark INITIATED refunds as COMPLETED.

        Called after admin has physically transferred money to customer.
        RefundTransaction.save() auto-sets completed_at when status
        reaches COMPLETED — defined in model save() override.
        full_clean() runs inside save() — guards are enforced.
        """
        success = 0
        errors  = 0

        for refund in queryset:
            if refund.status != RefundTransaction.Status.INITIATED:
                errors += 1
                self.message_user(
                    request,
                    f"Refund #{refund.pk}: cannot complete — "
                    f"current status is {refund.get_status_display()}.",
                    level=messages.ERROR,
                )
                continue

            try:
                refund.status = RefundTransaction.Status.COMPLETED
                refund.save(update_fields=["status"])

                # Now update the PaymentTransaction status
                from decimal import Decimal
                from django.db.models import Sum

                original = refund.original_transaction
                total_refunded = (
                    RefundTransaction.objects
                    .filter(
                        original_transaction=original,
                        status=RefundTransaction.Status.COMPLETED,
                    )
                    .aggregate(total=Sum("amount_pkr"))["total"]
                    or Decimal("0.00")
                )

                if total_refunded >= original.amount_pkr:
                    original.status = PaymentTransaction.Status.REFUNDED
                else:
                    original.status = PaymentTransaction.Status.PARTIALLY_REFUNDED

                original.save(update_fields=["status"])

                success += 1
                logger.info(
                    "RefundTransactionAdmin.mark_refunds_completed: "
                    "refund completed | refund_id=%s amount=%s "
                    "payment_status=%s admin=%s",
                    refund.pk,
                    refund.amount_pkr,
                    original.status,
                    request.user.email,
                )

            except Exception as exc:
                errors += 1
                logger.exception(
                    "RefundTransactionAdmin.mark_refunds_completed: "
                    "error | refund_id=%s exc=%s",
                    refund.pk,
                    str(exc),
                )
                self.message_user(
                    request,
                    f"Refund #{refund.pk}: error — {exc}",
                    level=messages.ERROR,
                )

        if success:
            self.message_user(
                request,
                f"{success} refund(s) marked as completed.",
                level=messages.SUCCESS,
            )
        if errors:
            self.message_user(
                request,
                f"{errors} refund(s) could not be completed.",
                level=messages.WARNING,
            )


@admin.register(WebhookLog)
class WebhookLogAdmin(admin.ModelAdmin):
    """
    WebhookLog — fully read-only evidence view.

    Every gateway callback is recorded here — including fraudulent
    and malformed ones. Admin uses this for debugging and investigation.
    No mutations. No delete. Evidence must be preserved.
    """

    list_display = [
        "id",
        "gateway",
        "is_verified",
        "processed_successfully",
        "ip_address",
        "payment_transaction",
        "created_at",
    ]
    list_filter  = [
        "gateway",
        "is_verified",
        "processed_successfully",
        "created_at",
    ]
    search_fields = [
        "gateway",
        "ip_address",
        "payment_transaction__order__order_number",
    ]
    ordering       = ["-created_at"]
    readonly_fields = [
        "gateway",
        "payment_transaction",
        "payload",
        "headers",
        "ip_address",
        "is_verified",
        "processed_successfully",
        "error_message",
        "exception_trace",
        "created_at",
        "updated_at",
    ]
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(
        self, request: HttpRequest, obj: WebhookLog | None = None
    ) -> bool:
        return False

    def has_delete_permission(
        self, request: HttpRequest, obj: WebhookLog | None = None
    ) -> bool:
        return False