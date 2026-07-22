# apps/logistics/tasks.py
from __future__ import annotations

"""
Logistics Celery tasks.

process_courier_webhook:
    The single task that processes all courier webhook events.
    Courier-agnostic — delegates to the correct handler via registry.

    Flow:
        1. Fetch WebhookLog by pk
        2. Get handler from registry
        3. Verify HMAC signature
        4. Parse tracking number and status
        5. Fetch Shipment by tracking number
        6. Call ShipmentService.update_status()
        7. Update WebhookLog result fields

    Error handling:
        Every failure path updates WebhookLog with the reason.
        No exception propagates out of the task without being logged.
        Celery will not retry by default — webhook retries are
        handled by the courier sending again if they get no 200.
        (We always return 200 from the view — courier never retries.)

    Security:
        HMAC verification happens before any state change.
        Unverified webhooks are logged as evidence, never acted upon.
        exc.internal data never reaches WebhookLog.error_message
        (that field is customer/admin visible).
"""

import logging
import traceback

from celery import shared_task
from django.conf import settings
from django.db import transaction

from apps.payments.models import WebhookLog
from apps.logistics.models import Shipment
from apps.logistics.webhooks.registry import get_handler
from apps.logistics.services.shipment_service import ShipmentService

logger = logging.getLogger("apps.logistics")


@shared_task(
    bind=True,
    max_retries=0,        # Couriers always get 200 — they do not retry.
                          # Our WebhookLog is the retry audit trail.
    ignore_result=True,   # We do not need the return value in any chain.
    name="logistics.process_courier_webhook",
)
def process_courier_webhook(
    self,
    *,
    webhook_log_id: int,
    courier: str,
) -> None:
    """
    Process a single courier webhook event.

    Args:
        webhook_log_id: PK of the WebhookLog record saved by the view.
        courier:        CourierPartner value string e.g. "postex".
    """

    logger.info(
        "process_courier_webhook: started | "
        "webhook_log_id=%s courier=%s",
        webhook_log_id,
        courier,
    )

    # ── Step 1 — Fetch WebhookLog ─────────────────────────────────────────

    try:
        webhook_log = WebhookLog.objects.get(pk=webhook_log_id)
    except WebhookLog.DoesNotExist:
        logger.error(
            "process_courier_webhook: WebhookLog not found | "
            "webhook_log_id=%s courier=%s",
            webhook_log_id,
            courier,
        )
        return

    # ── Step 2 — Get handler from registry ───────────────────────────────

    handler = get_handler(courier)
    if handler is None:
        logger.error(
            "process_courier_webhook: no handler registered | "
            "courier=%s webhook_log_id=%s",
            courier,
            webhook_log_id,
        )
        _fail_webhook_log(
    webhook_log,
    error=f"No webhook handler registered for courier: {courier}",
)
        return

    # ── Step 3 — HMAC verification ────────────────────────────────────────

    secret = _get_courier_secret(courier)

    is_verified = handler.verify_signature(
        payload=webhook_log.payload,
        headers=webhook_log.headers,
        secret=secret,
    )

    webhook_log.is_verified = is_verified
    webhook_log.save(update_fields=["is_verified"])

    if not is_verified:
        logger.warning(
            "process_courier_webhook: HMAC verification FAILED | "
            "courier=%s webhook_log_id=%s — "
            "webhook logged as evidence, no state change.",
            courier,
            webhook_log_id,
        )
        _fail_webhook_log(
            webhook_log,
            error="HMAC signature verification failed. "
                  "Possible fake or tampered webhook.",
        )
        return

    logger.info(
        "process_courier_webhook: HMAC verified | "
        "webhook_log_id=%s courier=%s",
        webhook_log_id,
        courier,
    )

    # ── Step 4 — Parse payload ────────────────────────────────────────────

    tracking_number = handler.parse_tracking_number(webhook_log.payload)
    if not tracking_number:
        logger.warning(
            "process_courier_webhook: tracking number missing | "
            "courier=%s webhook_log_id=%s",
            courier,
            webhook_log_id,
        )
        _fail_webhook_log(
            webhook_log,
            error="Tracking number missing or empty in webhook payload.",
        )
        return

    new_status = handler.parse_status(webhook_log.payload)
    if not new_status:
        logger.warning(
            "process_courier_webhook: unmappable status | "
            "courier=%s webhook_log_id=%s",
            courier,
            webhook_log_id,
        )
        _fail_webhook_log(
            webhook_log,
            error=(
                f"Courier status could not be mapped to a known "
                f"Shipment.Status value. "
                f"Raw payload: {webhook_log.payload}"
            ),
        )
        return

    # ── Step 5 — Fetch Shipment ───────────────────────────────────────────

    try:
        shipment = (
            Shipment.objects
            .select_related(
                "order",
                "order__shipping_address",
                "order__user",
            )
            .get(tracking_number=tracking_number)
        )
    except Shipment.DoesNotExist:
        logger.warning(
            "process_courier_webhook: shipment not found | "
            "tracking_number=%s courier=%s webhook_log_id=%s",
            tracking_number,
            courier,
            webhook_log_id,
        )
        _fail_webhook_log(
            webhook_log,
            error=(
                f"No Shipment found with tracking_number='{tracking_number}'. "
                f"Webhook may be for a shipment not in our system."
            ),
        )
        return

    # ── Step 6 — Update shipment status via service ───────────────────────

    try:
        from apps.logistics.models import ShipmentStatusLog

        ShipmentService.update_status(
            shipment=shipment,
            new_status=new_status,
            source=ShipmentStatusLog.Source.WEBHOOK,
            updated_by=None,          # system-driven, no human user
            raw_webhook_data=webhook_log.payload,
        )

    except Exception as exc:
        logger.exception(
            "process_courier_webhook: ShipmentService.update_status FAILED | "
            "tracking=%s new_status=%s courier=%s webhook_log_id=%s",
            tracking_number,
            new_status,
            courier,
            webhook_log_id,
        )
        _fail_webhook_log(
            webhook_log,
            error=f"ShipmentService.update_status raised: {type(exc).__name__}: {exc}",
            exc=exc,
        )
        return

    # ── Step 7 — Mark webhook as successfully processed ───────────────────

    webhook_log.processed_successfully = True
    webhook_log.save(update_fields=["processed_successfully"])

    logger.info(
        "process_courier_webhook: completed successfully | "
        "tracking=%s new_status=%s courier=%s webhook_log_id=%s",
        tracking_number,
        new_status,
        courier,
        webhook_log_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _get_courier_secret(courier: str) -> str:
    """
    Return the HMAC secret for the given courier from settings.

    Returns empty string if not configured — verification will
    fail gracefully with a warning log.
    """
    secret_map = {
        "postex":   getattr(settings, "POSTEX_WEBHOOK_SECRET",   ""),
        "tcs":      getattr(settings, "TCS_WEBHOOK_SECRET",      ""),
        "leopards": getattr(settings, "LEOPARDS_WEBHOOK_SECRET",  ""),
    }
    return secret_map.get(courier, "")


def _fail_webhook_log(
    webhook_log: WebhookLog,
    *,
    error: str,
    exc: Exception | None = None,
) -> None:
    """
    Mark a WebhookLog as failed with error details.

    Respects WebhookLog immutability rules — only updates
    mutable fields via update_fields.

    Args:
        webhook_log: WebhookLog instance to update.
        error:       Human-readable error message.
        exc:         Optional exception for traceback capture.
    """
    webhook_log.processed_successfully = False
    webhook_log.error_message = error

    if exc is not None:
        webhook_log.exception_trace = traceback.format_exc()
    
    update_fields = ["processed_successfully", "error_message"]
    if exc is not None:
        update_fields.append("exception_trace")

    webhook_log.save(update_fields=update_fields)