# apps/returns/services/return_service.py
from __future__ import annotations
from typing import TYPE_CHECKING


"""
Return service — business logic for the full return lifecycle.

Responsibility:
    ReturnService.create_return_request() — customer submission with eligibility checks.
    ReturnService.approve_return()        — admin approves, sets approved_at.
    ReturnService.reject_return()         — admin rejects with mandatory reason.
    ReturnService.mark_item_received()    — admin marks physical item received.
    ReturnService.initiate_refund()       — admin creates RefundTransaction.
    ReturnService.complete_return()       — admin completes, updates PaymentTransaction.

    All eligibility validation lives here, not in serializers or views.
    Zero DRF imports. Zero HTTP concerns.

Return window:
    7 days from Order.delivered_at — not from placed_at.
    delivered_at is set by Order.transition_to(DELIVERED).
    If delivered_at is None on a DELIVERED order, the window
    check is skipped with a WARNING log — defensive behaviour
    for data integrity edge cases.

Status transition enforcement:
    Every transition method validates current status before
    proceeding. Attempting an invalid transition raises DomainError.
    No status is set directly — always via the named transition methods.

Photo requirement:
    DAMAGED and NOT_AS_DESCRIBED reasons require at least one photo.
    Validated before ReturnRequest is created — photos list is
    passed into create_return_request() and validated at service layer.

RefundTransaction linkage:
    initiate_refund() creates a RefundTransaction linked to the
    original PaymentTransaction for the order.
    RefundTransaction.clean() guards prevent over-refunding.
    complete_return() updates PaymentTransaction.status to
    REFUNDED or PARTIALLY_REFUNDED based on refund amount.

Dependency direction:
    models → selectors → services → views
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import transaction
from django.utils import timezone

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.orders.models import Order
from apps.payments.models import PaymentTransaction, RefundTransaction
from apps.returns.models import ReturnRequest, ReturnItemPhoto
from apps.returns.selectors.return_selectors import (
    get_order_item_for_return,
    get_existing_return_for_order_item,
)

if TYPE_CHECKING:
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import InMemoryUploadedFile
    from apps.orders.models import OrderItem
    from apps.accounts.models import User

logger = logging.getLogger("apps.returns")

RETURN_WINDOW_DAYS: int = 7


class ReturnService:
    """
    Business operations for the full return request lifecycle.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    Status transitions follow strict ordering:
        PENDING → APPROVED → ITEM_RECEIVED → REFUND_INITIATED → COMPLETED
        PENDING → REJECTED
    """

    # ─────────────────────────────────────────────────────────────────────────
    # CREATE RETURN REQUEST
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def create_return_request(
        *,
        user: "User",
        order_item_id: int,
        reason: str,
        reason_detail: str = "",
        resolution_requested: str = ReturnRequest.Resolution.REFUND,
        photos: list["InMemoryUploadedFile"] | None = None,
    ) -> ReturnRequest:
        """
        Submit a customer return request for a delivered order item.

        Validates:
            1. OrderItem exists and belongs to requesting user.
            2. Order status is DELIVERED.
            3. Within 7-day return window from Order.delivered_at.
            4. No existing ReturnRequest for this OrderItem
               (includes REJECTED requests — admin must intervene).
            5. Photos provided for DAMAGED and NOT_AS_DESCRIBED reasons.

        Creates ReturnRequest with status=PENDING and associated
        ReturnItemPhoto records inside a single atomic transaction.

        Args:
            user:                 Authenticated customer submitting the request.
            order_item_id:        PK of the OrderItem being returned.
            reason:               ReturnRequest.Reason choice value.
            reason_detail:        Customer explanation in their own words.
            resolution_requested: ReturnRequest.Resolution choice value.
            photos:               List of uploaded image files. Required
                                  for DAMAGED and NOT_AS_DESCRIBED reasons.

        Returns:
            Created ReturnRequest instance with photos accessible
            via return_request.photos.all().

        Raises:
            DomainError 400 — OrderItem not found or not owned by user.
            DomainError 400 — Order not yet delivered.
            DomainError 400 — Return window expired (> 7 days).
            DomainError 400 — Photos required but not provided.
            DomainError 409 — Return request already exists for this item.
        """
        photos = photos or []

        # ── Fetch and verify ownership ────────────────────────────────────────

        try:
            order_item = get_order_item_for_return(order_item_id, user)
        except Exception:
            raise DomainError(
                "Order item not found or does not belong to your account.",
                code=ErrorCode.NOT_FOUND,
                status_code=400,
            )

        order: Order = order_item.order

        # ── Check order is delivered ──────────────────────────────────────────

        if order.status != Order.Status.DELIVERED:
            raise DomainError(
                "Returns can only be requested for delivered orders. "
                "Your order has not been delivered yet.",
                code=ErrorCode.ORDER_NOT_DELIVERED,
                status_code=400,
            )

        # ── Check return window ───────────────────────────────────────────────

        if order.delivered_at is None:
            # Defensive: DELIVERED order with no delivered_at timestamp.
            # Log warning and skip window check rather than crashing.
            logger.warning(
                "ReturnService.create_return_request: order %s has "
                "status=DELIVERED but delivered_at is None — "
                "skipping return window check. order_id=%s",
                order.order_number,
                order.pk,
            )
        else:
            window = timedelta(days=RETURN_WINDOW_DAYS)
            elapsed = timezone.now() - order.delivered_at
            if elapsed > window:
                raise DomainError(
                    f"The return window for this order has expired. "
                    f"Returns must be requested within {RETURN_WINDOW_DAYS} days "
                    f"of delivery.",
                    code=ErrorCode.RETURN_WINDOW_EXPIRED,
                    status_code=400,
                )

        # ── Check no existing return for this order item ──────────────────────

        existing: ReturnRequest | None = get_existing_return_for_order_item(
            order_item
        )
        if existing is not None:
            raise DomainError(
                "A return request already exists for this item. "
                "Each order item can only have one return request. "
                "Please contact support if you need further assistance.",
                code=ErrorCode.RETURN_ALREADY_EXISTS,
                status_code=409,
            )

        # ── Validate photos for reasons that require them ─────────────────────

        photo_required_reasons = {
            ReturnRequest.Reason.DAMAGED,
            ReturnRequest.Reason.NOT_AS_DESCRIBED,
        }
        if reason in photo_required_reasons and not photos:
            raise DomainError(
                "Photos are required when the reason is damaged or "
                "not as described. Please upload at least one photo "
                "showing the issue.",
                code=ErrorCode.PHOTOS_REQUIRED,
                status_code=400,
            )

        # ── Create ReturnRequest and photos atomically ────────────────────────

        with transaction.atomic():
            return_request = ReturnRequest.objects.create(
                order=order,
                order_item=order_item,
                requested_by=user,
                reason=reason,
                reason_detail=reason_detail,
                resolution_requested=resolution_requested,
                status=ReturnRequest.Status.PENDING,
            )

            if photos:
                ReturnItemPhoto.objects.bulk_create([
                    ReturnItemPhoto(
                        return_request=return_request,
                        image=photo,
                        caption="",
                    )
                    for photo in photos
                ])

        logger.info(
            "ReturnService.create_return_request: created | "
            "return_id=%s user=%s order=%s order_item=%s reason=%s photos=%d",
            return_request.pk,
            user.pk,
            order.order_number,
            order_item_id,
            reason,
            len(photos),
        )

        return return_request

    # ─────────────────────────────────────────────────────────────────────────
    # APPROVE RETURN
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def approve_return(
        *,
        return_request: ReturnRequest,
        reviewed_by: "User",
    ) -> ReturnRequest:
        """
        Approve a pending return request.

        Sets status to APPROVED, records approved_at timestamp,
        and records the admin who actioned it.

        Only PENDING requests can be approved. Attempting to approve
        a request in any other status raises DomainError 409.

        Args:
            return_request: ReturnRequest instance to approve.
            reviewed_by:    Staff User performing the approval.

        Returns:
            Updated ReturnRequest instance with status=APPROVED.

        Raises:
            DomainError 409 — return_request is not in PENDING status.
        """
        if return_request.status != ReturnRequest.Status.PENDING:
            raise DomainError(
                f"Only pending return requests can be approved. "
                f"Current status: {return_request.get_status_display()}.",
                code=ErrorCode.RETURN_NOT_APPROVED,
                status_code=409,
            )

        return_request.status      = ReturnRequest.Status.APPROVED
        return_request.approved_at = timezone.now()
        return_request.reviewed_by = reviewed_by
        return_request.save(update_fields=[
            "status",
            "approved_at",
            "reviewed_by",
        ])

        logger.info(
            "ReturnService.approve_return: approved | "
            "return_id=%s reviewed_by=%s",
            return_request.pk,
            getattr(reviewed_by, "email", "system"),
        )

        return return_request

    # ─────────────────────────────────────────────────────────────────────────
    # REJECT RETURN
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def reject_return(
        *,
        return_request: ReturnRequest,
        reviewed_by: "User",
        rejection_reason: str,
    ) -> ReturnRequest:
        """
        Reject a pending return request.

        Rejection reason is mandatory — stored on the ReturnRequest
        model directly (no separate log model for returns).

        Only PENDING requests can be rejected. Attempting to reject
        a request in any other status raises DomainError 409.

        Args:
            return_request:   ReturnRequest instance to reject.
            reviewed_by:      Staff User performing the rejection.
            rejection_reason: Required explanation for the rejection.
                              Stored on the record and visible to admin.

        Returns:
            Updated ReturnRequest instance with status=REJECTED.

        Raises:
            DomainError 400 — rejection_reason is empty.
            DomainError 409 — return_request is not in PENDING status.
        """
        if not rejection_reason or not rejection_reason.strip():
            raise DomainError(
                "A rejection reason is required. "
                "The reason is stored on the return request record.",
                code=ErrorCode.VALIDATION_ERROR,
                status_code=400,
            )

        if return_request.status != ReturnRequest.Status.PENDING:
            raise DomainError(
                f"Only pending return requests can be rejected. "
                f"Current status: {return_request.get_status_display()}.",
                code=ErrorCode.CONFLICT_ERROR,
                status_code=409,
            )

        return_request.status           = ReturnRequest.Status.REJECTED
        return_request.reviewed_by      = reviewed_by
        return_request.rejection_reason = rejection_reason.strip()
        return_request.save(update_fields=[
            "status",
            "reviewed_by",
            "rejection_reason",
        ])

        logger.info(
            "ReturnService.reject_return: rejected | "
            "return_id=%s reviewed_by=%s reason=%s",
            return_request.pk,
            getattr(reviewed_by, "email", "system"),
            rejection_reason[:100],
        )

        return return_request

    # ─────────────────────────────────────────────────────────────────────────
    # MARK ITEM RECEIVED
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def mark_item_received(
        *,
        return_request: ReturnRequest,
        reviewed_by: "User",
    ) -> ReturnRequest:
        """
        Mark the returned physical item as received at the warehouse.

        Only APPROVED requests can be moved to ITEM_RECEIVED.
        Status transitions strictly follow:
            PENDING → APPROVED → ITEM_RECEIVED

        Args:
            return_request: ReturnRequest instance to update.
            reviewed_by:    Staff User marking the item received.

        Returns:
            Updated ReturnRequest with status=ITEM_RECEIVED
            and received_at set to current time.

        Raises:
            DomainError 409 — return_request is not in APPROVED status.
        """
        if return_request.status != ReturnRequest.Status.APPROVED:
            raise DomainError(
                f"Only approved return requests can be marked as item received. "
                f"Current status: {return_request.get_status_display()}.",
                code=ErrorCode.CONFLICT_ERROR,
                status_code=409,
            )

        return_request.status      = ReturnRequest.Status.ITEM_RECEIVED
        return_request.received_at = timezone.now()
        return_request.reviewed_by = reviewed_by
        return_request.save(update_fields=[
            "status",
            "received_at",
            "reviewed_by",
        ])

        logger.info(
            "ReturnService.mark_item_received: item received | "
            "return_id=%s reviewed_by=%s",
            return_request.pk,
            getattr(reviewed_by, "email", "system"),
        )

        return return_request

    # ─────────────────────────────────────────────────────────────────────────
    # INITIATE REFUND
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def initiate_refund(
        *,
        return_request: ReturnRequest,
        initiated_by: "User",
        refund_amount: Decimal,
        reason: str = RefundTransaction.Reason.CUSTOMER_REQUEST,
        reason_detail: str = "",
    ) -> RefundTransaction:
        """
        Create a RefundTransaction and advance return to REFUND_INITIATED.

        Only ITEM_RECEIVED requests can proceed to refund initiation.
        The original PaymentTransaction for the order is located and
        linked to the RefundTransaction.

        RefundTransaction.clean() is called inside RefundTransaction.save()
        via full_clean() — it guards against:
            - Refunding a FAILED or PENDING transaction.
            - Total refunds exceeding the original transaction amount.

        Both the ReturnRequest status update and the RefundTransaction
        creation happen inside a single atomic transaction — either
        both succeed or neither does.

        Args:
            return_request: ReturnRequest instance in ITEM_RECEIVED status.
            initiated_by:   Staff User initiating the refund.
            refund_amount:  Decimal amount to refund in PKR.
            reason:         RefundTransaction.Reason choice value.
            reason_detail:  Optional detail text.

        Returns:
            Created RefundTransaction instance.

        Raises:
            DomainError 409 — return_request not in ITEM_RECEIVED status.
            DomainError 400 — no SUCCESS/PARTIALLY_REFUNDED PaymentTransaction
                              found for this order.
            DomainError 400 — refund amount exceeds original transaction
                              (surfaced from RefundTransaction.clean()).
        """
        if return_request.status != ReturnRequest.Status.ITEM_RECEIVED:
            raise DomainError(
                f"Refund can only be initiated after the item has been "
                f"received at the warehouse. "
                f"Current status: {return_request.get_status_display()}.",
                code=ErrorCode.CONFLICT_ERROR,
                status_code=409,
            )

        # ── Locate the original PaymentTransaction ────────────────────────────

        refundable_statuses = (
            PaymentTransaction.Status.SUCCESS,
            PaymentTransaction.Status.PARTIALLY_REFUNDED,
        )
        original_transaction: PaymentTransaction | None = (
            PaymentTransaction.objects
            .filter(
                order=return_request.order,
                status__in=refundable_statuses,
            )
            .order_by("-created_at")
            .first()
        )

        if original_transaction is None:
            raise DomainError(
                "No completed payment transaction found for this order. "
                "A refund can only be issued against a successful payment.",
                code=ErrorCode.REFUND_EXCEEDS_ORIGINAL,
                status_code=400,
            )

        # ── Create RefundTransaction and update ReturnRequest atomically ──────

        with transaction.atomic():
            refund_transaction = RefundTransaction(
                original_transaction=original_transaction,
                order=return_request.order,
                initiated_by=initiated_by,
                amount_pkr=refund_amount,
                reason=reason,
                reason_detail=reason_detail,
                status=RefundTransaction.Status.INITIATED,
            )
            # full_clean() is called inside RefundTransaction.save()
            # which runs clean() — guards over-refund and status checks.
            refund_transaction.save()

            return_request.status = ReturnRequest.Status.REFUND_INITIATED
            return_request.save(update_fields=["status"])

        logger.info(
            "ReturnService.initiate_refund: refund initiated | "
            "return_id=%s refund_id=%s amount=%s order=%s initiated_by=%s",
            return_request.pk,
            refund_transaction.pk,
            refund_amount,
            return_request.order.order_number,
            getattr(initiated_by, "email", "system"),
        )

        return refund_transaction

    # ─────────────────────────────────────────────────────────────────────────
    # COMPLETE RETURN
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def complete_return(
        *,
        return_request: ReturnRequest,
        refund_transaction: RefundTransaction,
        completed_by: "User",
    ) -> ReturnRequest:
        """
        Complete the return — mark refund done and close the return request.

        Marks RefundTransaction.status as COMPLETED (which auto-sets
        completed_at via RefundTransaction.save()).

        Updates PaymentTransaction.status:
            Full refund  → REFUNDED
            Partial      → PARTIALLY_REFUNDED

        Advance ReturnRequest.status to COMPLETED and set completed_at.

        All three updates happen inside a single atomic transaction.

        Only REFUND_INITIATED requests can be completed.

        Args:
            return_request:     ReturnRequest instance in REFUND_INITIATED.
            refund_transaction: RefundTransaction instance to mark COMPLETED.
            completed_by:       Staff User completing the return.

        Returns:
            Updated ReturnRequest with status=COMPLETED.

        Raises:
            DomainError 409 — return_request not in REFUND_INITIATED status.
            DomainError 409 — refund_transaction already COMPLETED.
        """
        if return_request.status != ReturnRequest.Status.REFUND_INITIATED:
            raise DomainError(
                f"Only return requests in refund_initiated status can be "
                f"completed. "
                f"Current status: {return_request.get_status_display()}.",
                code=ErrorCode.CONFLICT_ERROR,
                status_code=409,
            )

        if refund_transaction.status == RefundTransaction.Status.COMPLETED:
            raise DomainError(
                "This refund transaction has already been completed.",
                code=ErrorCode.CONFLICT_ERROR,
                status_code=409,
            )

        with transaction.atomic():
            # ── Mark RefundTransaction COMPLETED ──────────────────────────────
            # RefundTransaction.save() auto-sets completed_at when
            # status reaches COMPLETED — defined in its save() override.
            refund_transaction.status = RefundTransaction.Status.COMPLETED
            refund_transaction.save(update_fields=["status"])

            # ── Update PaymentTransaction status ──────────────────────────────
            original: PaymentTransaction = refund_transaction.original_transaction

            from django.db.models import Sum as _Sum
            total_refunded: Decimal = (
                RefundTransaction.objects
                .filter(
                    original_transaction=original,
                    status=RefundTransaction.Status.COMPLETED,
                )
                .aggregate(total=_Sum("amount_pkr"))["total"]
                or Decimal("0.00")
            )

            if total_refunded >= original.amount_pkr:
                original.status = PaymentTransaction.Status.REFUNDED
            else:
                original.status = PaymentTransaction.Status.PARTIALLY_REFUNDED

            original.save(update_fields=["status"])

            # ── Complete the ReturnRequest ─────────────────────────────────────
            return_request.status       = ReturnRequest.Status.COMPLETED
            return_request.completed_at = timezone.now()
            return_request.save(update_fields=["status", "completed_at"])

        logger.info(
            "ReturnService.complete_return: completed | "
            "return_id=%s refund_id=%s total_refunded=%s "
            "payment_status=%s completed_by=%s",
            return_request.pk,
            refund_transaction.pk,
            total_refunded,
            original.status,
            getattr(completed_by, "email", "system"),
        )

        return return_request