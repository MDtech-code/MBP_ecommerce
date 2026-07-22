# apps/payments/tasks.py
from __future__ import annotations

"""
Payment Celery tasks — async processing of gateway webhooks.

Design rules:
    - Webhook view creates WebhookLog and returns 200 immediately.
    - This task does the actual processing: HMAC verify → parse → update.
    - Task failure does NOT affect the 200 response already sent to gateway.
    - If task fails, WebhookLog.processed_successfully stays False.
      Admin can see this in Django admin and re-trigger if needed.
    - max_retries=3, exponential backoff via countdown.
    - All exceptions are caught — task never raises to Celery as FAILURE
      for gateway-logic errors (only for unexpected Python errors).

Celery task naming:
    Uses explicit name= to avoid import path changes breaking
    registered task names in Redis task queue.
"""

import logging
import traceback

from celery import shared_task

from apps.payments.models import WebhookLog

logger = logging.getLogger("apps.payments")


@shared_task(
    name="apps.payments.tasks.process_payment_webhook",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    acks_late=True,
)
def process_payment_webhook(
    self,
    webhook_log_id: int,
    gateway_name: str,
) -> None:
    """
    Process a payment gateway webhook asynchronously.

    Flow:
        1. Load WebhookLog from DB.
        2. Get gateway client from registry.
        3. Call client.verify_webhook() — HMAC check.
        4. If not verified: log, update WebhookLog, return.
        5. Call client.parse_webhook() — extract payment data.
        6. Call PaymentService.handle_webhook_result().
        7. Update WebhookLog with final result.

    Retry behaviour:
        Retries on unexpected exceptions (DB errors, network issues).
        Does NOT retry on HMAC failure — fraudulent webhooks should
        not be retried.
        Does NOT retry on gateway logic errors — these are permanent.

    Args:
        self:           Celery task instance (bound=True).
        webhook_log_id: Primary key of the WebhookLog to process.
        gateway_name:   Gateway string — used to select client and
                        locate PaymentTransaction.
    """
    logger.info(
        "process_payment_webhook: started | "
        "webhook_log_id=%s gateway=%s attempt=%s",
        webhook_log_id,
        gateway_name,
        self.request.retries + 1,
    )

    # ── Load WebhookLog ───────────────────────────────────────────────────────

    try:
        webhook_log = WebhookLog.objects.get(pk=webhook_log_id)
    except WebhookLog.DoesNotExist:
        logger.error(
            "process_payment_webhook: WebhookLog not found | "
            "webhook_log_id=%s",
            webhook_log_id,
        )
        return

    # ── Get gateway client ────────────────────────────────────────────────────

    from apps.payments.gateways.registry import get_gateway_client
    client = get_gateway_client(gateway_name)

    if client is None:
        logger.error(
            "process_payment_webhook: unknown gateway | "
            "webhook_log_id=%s gateway=%s",
            webhook_log_id,
            gateway_name,
        )
        webhook_log.error_message = f"Unknown gateway: {gateway_name}"
        webhook_log.save(update_fields=[
            "processed_successfully",
            "error_message",
        ])
        return

    # ── Get webhook secret from settings ──────────────────────────────────────

    from django.conf import settings
    secret_map: dict[str, str] = {
        "jazzcash":  getattr(settings, "JAZZCASH_INTEGRITY_SALT",  ""),
        "easypaisa": getattr(settings, "EASYPAISA_HASH_KEY",       ""),
        "safepay":   getattr(settings, "SAFEPAY_WEBHOOK_SECRET",   ""),
    }
    secret = secret_map.get(gateway_name, "")

    payload: dict = webhook_log.payload
    headers: dict = webhook_log.headers

    # ── HMAC verification ─────────────────────────────────────────────────────

    try:
        is_verified = client.verify_webhook(
            payload=payload,
            headers=headers,
            secret=secret,
        )
    except Exception as exc:
        logger.exception(
            "process_payment_webhook: verify_webhook raised | "
            "webhook_log_id=%s exc=%s",
            webhook_log_id,
            str(exc),
        )
        is_verified = False

    if not is_verified:
        logger.warning(
            "process_payment_webhook: HMAC verification failed | "
            "webhook_log_id=%s gateway=%s — not retrying.",
            webhook_log_id,
            gateway_name,
        )
        webhook_log.is_verified            = False
        webhook_log.processed_successfully = False
        webhook_log.error_message          = "HMAC signature verification failed."
        webhook_log.save(update_fields=[
            "is_verified",
            "processed_successfully",
            "error_message",
        ])
        return

    # ── Parse webhook payload ─────────────────────────────────────────────────

    try:
        parse_result = client.parse_webhook(payload=payload)
    except Exception as exc:
        logger.exception(
            "process_payment_webhook: parse_webhook raised | "
            "webhook_log_id=%s exc=%s",
            webhook_log_id,
            str(exc),
        )
        webhook_log.is_verified            = True
        webhook_log.processed_successfully = False
        webhook_log.error_message          = f"Parse error: {exc}"
        webhook_log.exception_trace        = traceback.format_exc()
        webhook_log.save(update_fields=[
            "is_verified",
            "processed_successfully",
            "error_message",
            "exception_trace",
        ])
        return

    # ── Handle result via PaymentService ─────────────────────────────────────

    try:
        from apps.payments.services.payment_service import PaymentService
        PaymentService.handle_webhook_result(
            webhook_log=webhook_log,
            parse_result=parse_result,
            gateway_name=gateway_name,
        )
    except Exception as exc:
        logger.exception(
            "process_payment_webhook: handle_webhook_result raised | "
            "webhook_log_id=%s exc=%s",
            webhook_log_id,
            str(exc),
        )
        webhook_log.is_verified            = True
        webhook_log.processed_successfully = False
        webhook_log.error_message          = f"Processing error: {exc}"
        webhook_log.exception_trace        = traceback.format_exc()
        webhook_log.save(update_fields=[
            "is_verified",
            "processed_successfully",
            "error_message",
            "exception_trace",
        ])

        # Retry on unexpected errors — not on gateway logic errors
        try:
            raise self.retry(
                exc=exc,
                countdown=60 * (2 ** self.request.retries),
            )
        except self.MaxRetriesExceededError:
            logger.error(
                "process_payment_webhook: max retries exceeded | "
                "webhook_log_id=%s",
                webhook_log_id,
            )
        return

    logger.info(
        "process_payment_webhook: completed | "
        "webhook_log_id=%s gateway=%s",
        webhook_log_id,
        gateway_name,
    )