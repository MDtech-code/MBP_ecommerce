# apps/payments/models.py
from __future__ import annotations

import logging
import uuid
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimeStampedModel

logger = logging.getLogger("apps.payments")


class PaymentTransaction(TimeStampedModel):
    """
    Single payment attempt for an order.

    One order can have MULTIPLE transactions (retries after failure).
    Only one should reach SUCCESS — enforced at service layer.

    COD flow:
        PaymentTransaction(gateway=COD, status=PENDING) created at order placement.
        Celery task or admin updates to SUCCESS on delivery confirmation.

    Online flow:
        PaymentTransaction(gateway=SAFEPAY, status=PENDING) created.
        Gateway webhook updates status to SUCCESS or FAILED.

    idempotency_key:
        Auto-generated UUID passed to gateway on payment initiation.
        If network retry submits same key twice, gateway returns
        existing result instead of charging twice.

    user stored separately from order.user:
        SET_NULL preserves payment audit if user account is deleted.
    """

    class Gateway(models.TextChoices):
        COD       = "cod",       _("Cash on Delivery")
        SAFEPAY   = "safepay",   _("Safepay")
        PAYFAST   = "payfast",   _("PayFast")
        JAZZCASH  = "jazzcash",  _("JazzCash Mobile Wallet / Card")
        EASYPAISA = "easypaisa", _("Easypaisa")
        RAAST     = "raast",     _("Raast Instant Transfer")
        XPAY      = "xpay",      _("XPay by PostEx")

    class Status(models.TextChoices):
        PENDING            = "pending",            _("Pending")
        AUTHORIZED         = "authorized",         _("Authorized")
        SUCCESS            = "success",            _("Success")
        FAILED             = "failed",             _("Failed")
        REFUNDED           = "refunded",           _("Refunded")
        PARTIALLY_REFUNDED = "partially_refunded", _("Partially Refunded")

    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment_transactions",
        verbose_name=_("order"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payment_transactions",
        verbose_name=_("customer"),
        help_text=_("SET_NULL — payment audit survives user deletion."),
    )
    gateway = models.CharField(
        _("payment gateway"),
        max_length=20,
        choices=Gateway.choices,
        default=Gateway.COD,
    )
    status = models.CharField(
        _("status"),
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    amount_pkr = models.DecimalField(
        _("amount (PKR)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
    )
    transaction_reference = models.CharField(
        _("transaction reference"),
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        help_text=_("Gateway-assigned transaction ID. Null until gateway responds."),
    )
    idempotency_key = models.UUIDField(
        _("idempotency key"),
        unique=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_(
            "Auto-generated. Passed to gateway on payment initiation. "
            "Prevents double-charging on network retries."
        ),
    )
    error_message = models.TextField(
        _("error message"),
        blank=True,
        default="",
    )

    class Meta:
        verbose_name        = _("payment transaction")
        verbose_name_plural = _("payment transactions")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["order",   "status"]),
            models.Index(fields=["gateway", "status"]),
            models.Index(fields=["status",  "created_at"]),
            # COD delivery verification: pending COD transactions today
            models.Index(
                fields=["gateway", "status", "created_at"],
                name="payment_gateway_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.get_gateway_display()} — "
            f"Rs. {self.amount_pkr} ({self.status})"
        )

    def save(self, *args, **kwargs) -> None:
        # Validate user matches order.user — on creation only
        # Uses values_list to avoid loading full Order object
        if not self.pk and self.order_id and self.user_id:
            from apps.orders.models import Order
            order_user_id = (
                Order.objects
                .filter(pk=self.order_id)
                .values_list("user_id", flat=True)
                .first()
            )
            if order_user_id != self.user_id:
                raise ValueError(
                    "PaymentTransaction.user must match Order.user."
                )

        super().save(*args, **kwargs)
        logger.debug(
            "PaymentTransaction saved: order=%s gateway=%s status=%s",
            self.order_id,
            self.gateway,
            self.status,
        )


class RefundTransaction(TimeStampedModel):
    """
    Separate financial record for every refund event.

    Refund is a distinct financial transaction — not a status change
    on PaymentTransaction. Keeps payment and refund audit trails clean.

    Partial refunds supported — multiple RefundTransactions can exist
    for one PaymentTransaction, as long as total does not exceed
    original transaction amount (enforced in clean()).

    completed_at is auto-set in save() when status reaches COMPLETED.
    """

    class Reason(models.TextChoices):
        CUSTOMER_REQUEST = "customer_request", _("Customer Request")
        OUT_OF_STOCK     = "out_of_stock",     _("Item Out of Stock")
        DAMAGED_ITEM     = "damaged_item",     _("Damaged Item Received")
        WRONG_ITEM       = "wrong_item",       _("Wrong Item Delivered")
        OTHER            = "other",            _("Other")

    class Status(models.TextChoices):
        INITIATED  = "initiated",  _("Initiated")
        PROCESSING = "processing", _("Processing")
        COMPLETED  = "completed",  _("Completed")
        FAILED     = "failed",     _("Failed")

    original_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.PROTECT,
        related_name="refunds",
        verbose_name=_("original transaction"),
    )
    order = models.ForeignKey(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="refunds",
        verbose_name=_("order"),
    )
    initiated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="initiated_refunds",
        verbose_name=_("initiated by"),
    )
    amount_pkr = models.DecimalField(
        _("refund amount (PKR)"),
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    reason = models.CharField(
        _("reason"),
        max_length=20,
        choices=Reason.choices,
        default=Reason.OTHER,
    )
    reason_detail = models.TextField(
        _("reason detail"),
        blank=True,
        default="",
    )
    status = models.CharField(
        _("refund status"),
        max_length=20,
        choices=Status.choices,
        default=Status.INITIATED,
    )
    gateway_refund_reference = models.CharField(
        _("gateway refund reference"),
        max_length=150,
        blank=True,
        default="",
        help_text=_("Reference ID returned by payment gateway for this refund."),
    )
    completed_at = models.DateTimeField(
        _("completed at"),
        null=True,
        blank=True,
        help_text=_("Auto-set when status transitions to COMPLETED."),
    )

    class Meta:
        verbose_name        = _("refund transaction")
        verbose_name_plural = _("refund transactions")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["order",  "status"]),
            models.Index(fields=["status", "created_at"]),
            # Supports total-refunded validation query in clean()
            models.Index(
                fields=["original_transaction", "status"],
                name="payment_refund_txn_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"Refund Rs. {self.amount_pkr} — "
            f"{self.order.order_number} ({self.status})"
        )

    def clean(self) -> None:
        """
        Guards:
        1. Cannot refund a FAILED or PENDING transaction.
        2. Total refunds cannot exceed original transaction amount.

        Teaching note: Guard 2 fires a SUM query — acceptable here
        because refunds are low-frequency admin/service operations,
        not high-traffic customer actions.
        The checkout service adds a select_for_update() layer on top
        of this clean() check for concurrent refund safety.
        """
        if self.original_transaction_id:

            # Guard 1: Only refund completed transactions
            refundable_statuses = (
                PaymentTransaction.Status.SUCCESS,
                PaymentTransaction.Status.PARTIALLY_REFUNDED,
            )
            if self.original_transaction.status not in refundable_statuses:
                raise ValidationError({
                    "original_transaction": _(
                        "Can only refund transactions with SUCCESS or "
                        "PARTIALLY_REFUNDED status. "
                        "Current status: %(status)s."
                    ) % {"status": self.original_transaction.status}
                })

            # Guard 2: Total refunds cannot exceed original amount
            if self.amount_pkr:
                already_refunded = (
                    RefundTransaction.objects
                    .filter(
                        original_transaction=self.original_transaction,
                        status=self.Status.COMPLETED,
                    )
                    .exclude(pk=self.pk)
                    .aggregate(total=Sum("amount_pkr"))["total"]
                    or Decimal("0.00")
                )
                if already_refunded + self.amount_pkr > self.original_transaction.amount_pkr:
                    raise ValidationError({
                        "amount_pkr": _(
                            "Total refunds (Rs. %(total)s) would exceed "
                            "original transaction amount (Rs. %(original)s). "
                            "Rs. %(remaining)s remaining."
                        ) % {
                            "total":     already_refunded + self.amount_pkr,
                            "original":  self.original_transaction.amount_pkr,
                            "remaining": self.original_transaction.amount_pkr - already_refunded,
                        }
                    })

    def save(self, *args, **kwargs) -> None:
        self.full_clean()
        # Auto-set completed_at on COMPLETED transition
        if self.status == self.Status.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
        logger.debug(
            "RefundTransaction saved: order=%s amount=%s status=%s",
            self.order_id,
            self.amount_pkr,
            self.status,
        )


class WebhookLog(TimeStampedModel):
    """
    Append-on-receipt, update-on-processing log for gateway webhooks.

    Immutability rules:
        IMMUTABLE (after INSERT):
            gateway, payload, headers, ip_address
            These are evidence of what the gateway sent.
            Changing them would be tampering with audit data.

        MUTABLE (via save(update_fields=[...])):
            payment_transaction, is_verified,
            processed_successfully, error_message, exception_trace
            These are our processing RESULT — updated by Celery task
            after the raw webhook is saved.

    Flow:
        1. Webhook received → WebhookLog created immediately (raw INSERT)
           is_verified=False, processed_successfully=False
        2. Celery task processes it → updates result fields via update_fields
        3. Admin can see full audit trail of every callback

    Records ALL webhooks including fraudulent/malformed ones —
    critical for detecting fake gateway callbacks.
    """

    gateway = models.CharField(
        _("gateway"),
        max_length=50,
        db_index=True,
    )
    payment_transaction = models.ForeignKey(
        PaymentTransaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="webhook_logs",
        verbose_name=_("payment transaction"),
        help_text=_(
            "Linked after webhook is matched to a transaction. "
            "Null for unrecognized or fraudulent webhooks."
        ),
    )
    payload = models.JSONField(
        _("payload"),
        help_text=_("Raw JSON payload received from gateway. Immutable."),
    )
    headers = models.JSONField(
        _("headers"),
        help_text=_(
            "HTTP request headers — used for HMAC signature verification. "
            "Immutable."
        ),
    )
    ip_address = models.GenericIPAddressField(
        _("IP address"),
        null=True,
        blank=True,
    )
    is_verified = models.BooleanField(
        _("signature verified"),
        default=False,
        help_text=_("True if HMAC signature matched gateway secret."),
    )
    processed_successfully = models.BooleanField(
        _("processed successfully"),
        default=False,
    )
    error_message = models.TextField(
        _("error message"),
        blank=True,
        default="",
    )
    exception_trace = models.TextField(
        _("exception trace"),
        blank=True,
        default="",
    )

    class Meta:
        verbose_name        = _("webhook log")
        verbose_name_plural = _("webhook logs")
        ordering            = ["-created_at"]
        indexes = [
            models.Index(fields=["gateway",     "created_at"]),
            models.Index(fields=["is_verified", "processed_successfully"]),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.gateway}] webhook — "
            f"verified={self.is_verified} "
            f"processed={self.processed_successfully} "
            f"@ {self.created_at}"
        )

    def save(self, *args, **kwargs) -> None:
        """
        Enforces immutability on evidence fields.

        First save (INSERT): all fields written freely.
        Subsequent saves (UPDATE): only processing result fields
        may be updated via update_fields.
        """
        if self.pk:
            update_fields = kwargs.get("update_fields")
            if not update_fields:
                raise ValueError(
                    "WebhookLog core fields are immutable after creation. "
                    "Use save(update_fields=[...]) with only mutable fields: "
                    "payment_transaction_id, is_verified, "
                    "processed_successfully, error_message, exception_trace."
                )
            immutable = {
                "gateway", "payload", "headers", "ip_address",
            }
            attempted = immutable.intersection(set(update_fields))
            if attempted:
                raise ValueError(
                    f"WebhookLog fields are immutable after creation: "
                    f"{attempted}"
                )
        super().save(*args, **kwargs)
        logger.debug(
            "WebhookLog saved: gateway=%s verified=%s processed=%s",
            self.gateway,
            self.is_verified,
            self.processed_successfully,
        )