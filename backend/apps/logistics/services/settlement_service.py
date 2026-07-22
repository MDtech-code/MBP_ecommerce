# apps/logistics/services/settlement_service.py
from __future__ import annotations

"""
Settlement service — business logic for COD settlement reconciliation.

Responsibility:
    Creating CourierSettlement records and marking them reconciled.
    All validation of settlement data lives here.
    Admin calls these methods from save_model() and admin actions.
    Zero DRF imports. Zero HTTP concerns.

Pakistani COD settlement reality:
    Courier collects cash from customer on delivery.
    Every 7-14 days courier transfers net amount to seller bank.
    Net = total_cod_collected - total_shipping_deducted
    Finance team creates settlement record when bank credit arrives.
    Finance team reconciles after verifying against bank statement.

Business rules enforced here:
    1. settlement_reference must be globally unique.
    2. All shipments_included must have status=DELIVERED.
    3. Each shipment can only appear in one settlement.
    4. Reconciliation is one-way — cannot unreconcile.
    5. net_payout_received is validated against the arithmetic difference
       of total_cod_collected - total_shipping_deducted.
       Mismatch is warned but not blocked — banks round differently.

Dependency direction:
    models → selectors → services → admin
"""

import logging
from decimal import Decimal

from django.db import transaction

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from apps.logistics.models import (
    CourierSettlement,
    Shipment,
)

logger = logging.getLogger("apps.logistics")


class SettlementService:
    """
    Business operations for CourierSettlement lifecycle.

    All methods are static — no instance state required.
    All methods raise DomainError for business rule violations.
    Admin save_model() and actions catch DomainError and surface
    the message to the finance user via self.message_user().
    """

    # ─────────────────────────────────────────────────────────────────────
    # CREATE SETTLEMENT
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def create_settlement(
        *,
        courier: str,
        settlement_reference: str,
        total_cod_collected: Decimal,
        total_shipping_deducted: Decimal,
        net_payout_received: Decimal,
        payout_date,
        shipment_ids: list[int],
        created_by,
    ) -> CourierSettlement:
        """
        Create a CourierSettlement record linking delivered shipments
        to a bank transfer from the courier.

        Pre-checks (outside atomic):
            - settlement_reference is unique
            - all shipment_ids resolve to existing Shipment records
            - all resolved shipments have status=DELIVERED
            - no shipment already belongs to another settlement

        Inside atomic:
            - CourierSettlement created
            - M2M shipments_included populated

        Args:
            courier:                 CourierPartner value string.
            settlement_reference:    Bank transfer ID or remittance number.
            total_cod_collected:     Total PKR collected from customers.
            total_shipping_deducted: Courier charges deducted.
            net_payout_received:     Actual bank deposit amount.
            payout_date:             Date bank credit was received.
            shipment_ids:            List of Shipment PKs to include.
            created_by:              Staff User creating this settlement.

        Returns:
            Created CourierSettlement instance.

        Raises:
            DomainError 409 — settlement_reference already exists.
            DomainError 400 — shipment_ids list is empty.
            DomainError 400 — one or more shipments not found.
            DomainError 400 — one or more shipments not DELIVERED.
            DomainError 409 — one or more shipments already settled.
        """

        # ── Pre-check 1 — settlement_reference uniqueness ─────────────────

        if CourierSettlement.objects.filter(
            settlement_reference=settlement_reference
        ).exists():
            raise DomainError(
                f"Settlement reference '{settlement_reference}' already "
                f"exists. Each bank transfer must have a unique reference.",
                code=ErrorCode.SETTLEMENT_ALREADY_EXISTS,
                status_code=409,
            )

        # ── Pre-check 2 — shipment list must not be empty ─────────────────

        if not shipment_ids:
            raise DomainError(
                "At least one shipment must be included in a settlement. "
                "Select the delivered shipments covered by this bank transfer.",
                code=ErrorCode.SHIPMENT_NOT_DELIVERED,
                status_code=400,
            )

        # ── Pre-check 3 — resolve and validate all shipments ──────────────

        # Fetch all at once — single query, not N queries
        shipments = list(
            Shipment.objects
            .filter(pk__in=shipment_ids)
            .prefetch_related("settlements")
        )

        # Verify all requested IDs were found
        found_ids = {s.pk for s in shipments}
        requested_ids = set(shipment_ids)
        missing_ids = requested_ids - found_ids

        if missing_ids:
            raise DomainError(
                f"Shipment(s) not found: {sorted(missing_ids)}. "
                f"Verify the shipment IDs and try again.",
                code=ErrorCode.SHIPMENT_NOT_DELIVERED,
                status_code=400,
            )

        # Verify all shipments are DELIVERED
        not_delivered = [
            s.tracking_number
            for s in shipments
            if s.status != Shipment.Status.DELIVERED
        ]

        if not_delivered:
            raise DomainError(
                f"The following shipments are not in DELIVERED status "
                f"and cannot be included in a settlement: "
                f"{not_delivered}. "
                f"Only DELIVERED shipments can be settled — the courier "
                f"only holds COD for confirmed deliveries.",
                code=ErrorCode.SHIPMENT_NOT_DELIVERED,
                status_code=400,
            )

        # Verify no shipment already belongs to another settlement
        already_settled = [
            s.tracking_number
            for s in shipments
            if s.settlements.exists()
        ]

        if already_settled:
            raise DomainError(
                f"The following shipments are already included in an "
                f"existing settlement: {already_settled}. "
                f"A shipment can only appear in one settlement.",
                code=ErrorCode.SHIPMENT_ALREADY_SETTLED,
                status_code=409,
            )

        # ── Pre-check 4 — warn on arithmetic mismatch (non-blocking) ──────

        expected_net = total_cod_collected - total_shipping_deducted
        tolerance = Decimal("1.00")  # allow Rs. 1 rounding difference

        if abs(expected_net - net_payout_received) > tolerance:
            logger.warning(
                "SettlementService.create_settlement: "
                "net payout mismatch | "
                "reference=%s expected_net=%s received=%s diff=%s "
                "created_by=%s",
                settlement_reference,
                expected_net,
                net_payout_received,
                abs(expected_net - net_payout_received),
                getattr(created_by, "email", "unknown"),
            )
            # Not raising — bank rounding differences are common.
            # Finance team will see this in the reconcile step.

        # ── Atomic block ──────────────────────────────────────────────────

        with transaction.atomic():

            settlement = CourierSettlement.objects.create(
                courier=courier,
                settlement_reference=settlement_reference,
                total_cod_collected=total_cod_collected,
                total_shipping_deducted=total_shipping_deducted,
                net_payout_received=net_payout_received,
                payout_date=payout_date,
                is_reconciled=False,
            )

            # Populate M2M — bulk add, single query
            settlement.shipments_included.set(shipments)

            logger.info(
                "SettlementService.create_settlement: created | "
                "reference=%s courier=%s shipments=%s "
                "net_payout=%s created_by=%s",
                settlement_reference,
                courier,
                len(shipments),
                net_payout_received,
                getattr(created_by, "email", "unknown"),
            )

        return settlement

    # ─────────────────────────────────────────────────────────────────────
    # RECONCILE SETTLEMENT
    # ─────────────────────────────────────────────────────────────────────

    @staticmethod
    def reconcile(
        *,
        settlement: CourierSettlement,
        reconciled_by,
    ) -> CourierSettlement:
        """
        Mark a settlement as reconciled after finance team verification.

        Reconciliation is one-way — once reconciled it cannot be
        reversed. This is a financial compliance requirement.

        Args:
            settlement:     CourierSettlement instance to reconcile.
            reconciled_by:  Staff User performing reconciliation.

        Returns:
            Updated CourierSettlement instance.

        Raises:
            DomainError 409 — settlement is already reconciled.
        """

        if settlement.is_reconciled:
            raise DomainError(
                f"Settlement '{settlement.settlement_reference}' is "
                f"already reconciled. "
                f"Reconciliation is a one-way operation — "
                f"it cannot be reversed.",
                code=ErrorCode.SETTLEMENT_ALREADY_RECONCILED,
                status_code=409,
            )

        settlement.is_reconciled = True
        settlement.save(update_fields=["is_reconciled"])

        logger.info(
            "SettlementService.reconcile: reconciled | "
            "reference=%s courier=%s net_payout=%s "
            "reconciled_by=%s",
            settlement.settlement_reference,
            settlement.courier,
            settlement.net_payout_received,
            getattr(reconciled_by, "email", "unknown"),
        )

        return settlement