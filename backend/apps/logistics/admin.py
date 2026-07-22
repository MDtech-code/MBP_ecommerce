import logging

from django.contrib import admin, messages
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
from apps.logistics.models import Shipment, ShipmentStatusLog
from apps.logistics.services.shipment_service import ShipmentService
from apps.core.exceptions import DomainError
# ─────────────────────────────────────────────────────────────────────────────
# ADD THESE IMPORTS to the existing import block at the top of admin.py
# ─────────────────────────────────────────────────────────────────────────────

# Add to existing imports:
from apps.logistics.models import Shipment, ShipmentStatusLog, CourierSettlement
from apps.logistics.services.settlement_service import SettlementService
logger = logging.getLogger("apps.logistics")


# ─────────────────────────────────────────────────────────────────────────────
# INLINE — status log history inside the Shipment change page
# ─────────────────────────────────────────────────────────────────────────────

class ShipmentStatusLogInline(admin.TabularInline):
    model         = ShipmentStatusLog
    extra         = 0
    can_delete    = False
    ordering      = ("-created_at",)
    readonly_fields = ("from_status", "to_status", "source", "raw_webhook_data", "created_at")
    fields          = readonly_fields

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False   # logs only written by service layer


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT ADMIN
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):

    # ── List ──────────────────────────────────────────────────────────────
    list_display  = (
        "tracking_number", "order", "shipment_type",
        "courier", "status_badge", "destination_city",
        "is_cod", "cod_amount", "shipping_cost_pkr",
        "estimated_delivery_date", "created_at",
    )
    list_filter   = ("status", "courier", "shipment_type", "is_cod", "destination_city")
    search_fields = ("tracking_number", "order__order_number", "destination_city")
    ordering      = ("-created_at",)
    list_per_page = 20
    inlines       = [ShipmentStatusLogInline]

    # ── Change form (existing record — all readonly, edit via actions) ─────
    readonly_fields = (
        "order", "shipment_type", "courier", "tracking_number",
        "status", "is_cod", "cod_amount", "shipping_cost_pkr",
        "destination_city", "weight_kg", "estimated_delivery_date",
        "actual_delivery_date", "raw_courier_response", "created_at", "updated_at",
    )
    fieldsets = (
        (_("Shipment"), {
            "fields": (
                "order", "shipment_type", "courier",
                "tracking_number", "status",
            ),
        }),
        (_("Financials"), {
            "fields": ("is_cod", "cod_amount", "shipping_cost_pkr"),
        }),
        (_("Logistics"), {
            "fields": (
                "destination_city", "weight_kg",
                "estimated_delivery_date", "actual_delivery_date",
            ),
        }),
        (_("Debug"), {
            "fields": ("raw_courier_response", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    # ── Add form (new record — editable fields only) ───────────────────────
    add_fieldsets = (
        (_("Order"), {
            "fields": ("order",),
        }),
        (_("Courier"), {
            "fields": (
                "courier", "shipment_type", "tracking_number",
                "weight_kg", "shipping_cost_pkr", "estimated_delivery_date",
            ),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()          # add form: nothing locked
        return self.readonly_fields

    # ── save_model → ShipmentService.create_shipment() ────────────────────

    def save_model(self, request, obj, form, change):
        if change:
            # Direct field edits on existing shipment not allowed.
            # All changes go through status actions.
            self.message_user(
                request,
                _("Use the status actions to update a shipment. Direct edits are disabled."),
                level=messages.WARNING,
            )
            return

        try:
            ShipmentService.create_shipment(
                order=obj.order,
                courier=obj.courier,
                tracking_number=obj.tracking_number,
                weight_kg=obj.weight_kg,
                shipping_cost_pkr=obj.shipping_cost_pkr,
                estimated_delivery_date=obj.estimated_delivery_date,
                created_by=request.user,
            )
            # Success message — Django admin does not auto-add one on save_model override
            self.message_user(
                request,
                _(
                    f"Shipment '{obj.tracking_number}' created successfully. "
                    f"Order is now PROCESSING."
                ),
                level=messages.SUCCESS,
            )
        except DomainError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
        except Exception as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            logger.exception(
            "ShipmentAdmin.save_model: unexpected error | "
            "order=%s tracking=%s admin=%s",
            getattr(obj.order, "order_number", "?"),
            obj.tracking_number,
            request.user.pk,
            )
            self.message_user(
                request,
                _(f"Unexpected error creating shipment: {exc}"),
                level=messages.ERROR,
            )
    # ── Status actions → ShipmentService.update_status() ──────────────────

    actions = [
        "mark_label_created",
        "mark_picked_up",
        "mark_in_transit",
        "mark_out_for_delivery",
        "mark_delivered",
        "mark_return_requested",
        "mark_rto_in_transit",
        "mark_rto_delivered",
        "mark_lost",
    ]

    def _apply_status(self, request, queryset, new_status):
        ok = fail = 0
        for shipment in queryset.select_related("order", "order__shipping_address"):
            try:
                ShipmentService.update_status(
                    shipment=shipment,
                    new_status=new_status,
                    source=ShipmentStatusLog.Source.MANUAL,
                    updated_by=request.user,
                )
                ok += 1
            except Exception as exc:
                fail += 1
                self.message_user(
                    request,
                    f"{shipment.tracking_number}: {exc}",
                    level=messages.ERROR,
                )
        if ok:
            self.message_user(
                request,
                _(f"{ok} shipment(s) → '{new_status}'."),
                level=messages.SUCCESS,
            )

    @admin.action(description=_("→ Label Created"))
    def mark_label_created(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.LABEL_CREATED)

    @admin.action(description=_("→ Picked Up"))
    def mark_picked_up(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.PICKED_UP)

    @admin.action(description=_("→ In Transit"))
    def mark_in_transit(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.IN_TRANSIT)

    @admin.action(description=_("→ Out for Delivery"))
    def mark_out_for_delivery(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.OUT_FOR_DELIVERY)

    @admin.action(description=_("→ Delivered"))
    def mark_delivered(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.DELIVERED)

    @admin.action(description=_("→ Return Requested"))
    def mark_return_requested(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.RETURN_REQUESTED)

    @admin.action(description=_("→ RTO In Transit"))
    def mark_rto_in_transit(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.RTO_IN_TRANSIT)

    @admin.action(description=_("→ RTO Delivered  ⚠ cancels order + restores stock"))
    def mark_rto_delivered(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.RTO_DELIVERED)

    @admin.action(description=_("→ Lost in Transit"))
    def mark_lost(self, request, queryset):
        self._apply_status(request, queryset, Shipment.Status.LOST)

    # ── Display helper ─────────────────────────────────────────────────────

    STATUS_COLOURS = {
        Shipment.Status.LABEL_CREATED:    "#6c757d",
        Shipment.Status.PICKED_UP:        "#0d6efd",
        Shipment.Status.IN_TRANSIT:       "#fd7e14",
        Shipment.Status.OUT_FOR_DELIVERY: "#ffc107",
        Shipment.Status.DELIVERED:        "#198754",
        Shipment.Status.RETURN_REQUESTED: "#e83e8c",
        Shipment.Status.RTO_IN_TRANSIT:   "#dc3545",
        Shipment.Status.RTO_DELIVERED:    "#343a40",
        Shipment.Status.LOST:             "#000000",
    }

    @admin.display(description=_("Status"), ordering="status")
    def status_badge(self, obj):
        colour = self.STATUS_COLOURS.get(obj.status, "#6c757d")
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 8px;'
            'border-radius:4px;font-size:0.8em">{}</span>',
            colour,
            obj.get_status_display(),
        )


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT STATUS LOG — read-only audit browser
# ─────────────────────────────────────────────────────────────────────────────

@admin.register(ShipmentStatusLog)
class ShipmentStatusLogAdmin(admin.ModelAdmin):
    list_display    = ("shipment", "from_status", "to_status", "source", "created_at")
    list_filter     = ("source", "to_status")
    search_fields   = ("shipment__tracking_number",)
    ordering        = ("-created_at",)
    readonly_fields = ("shipment", "from_status", "to_status", "source", "raw_webhook_data", "created_at")

    def has_add_permission(self, request):    return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False





# ─────────────────────────────────────────────────────────────────────────────
# COURIER SETTLEMENT ADMIN
# ─────────────────────────────────────────────────────────────────────────────


class DeliveredShipmentsFilter(admin.SimpleListFilter):
    """
    Custom filter for the shipments_included M2M widget.

    Limits the M2M selection widget to only show DELIVERED shipments.
    Finance team cannot accidentally select an in-transit shipment.

    This filter is applied to the formfield_for_manytomany override
    on CourierSettlementAdmin — not used as a list_filter.
    """

    title = _("shipment status")
    parameter_name = "shipment_status"

    def lookups(self, request, model_admin):
        return [
            ("delivered", _("Delivered only")),
        ]

    def queryset(self, request, queryset):
        if self.value() == "delivered":
            return queryset.filter(status=Shipment.Status.DELIVERED)
        return queryset


@admin.register(CourierSettlement)
class CourierSettlementAdmin(admin.ModelAdmin):
    """
    Admin interface for CourierSettlement management.

    Finance team workflow:
        1. Receive bank transfer from courier
        2. Open Add Settlement form
        3. Fill in bank transfer details and select covered shipments
        4. Save — SettlementService.create_settlement() validates everything
        5. After verifying bank statement: select settlement + reconcile action

    Design decisions:
        - save_model() calls SettlementService.create_settlement()
          for full validation — not bypassed by admin form
        - M2M widget filtered to DELIVERED shipments only
        - is_reconciled is readonly on change form — set via action only
        - mark_as_reconciled action calls SettlementService.reconcile()
        - has_delete_permission=False — financial records are permanent
        - has_change_permission returns False for reconciled settlements
    """

    # ── List view ──────────────────────────────────────────────────────────

    list_display = [
        "settlement_reference",
        "courier",
        "payout_date",
        "total_cod_collected",
        "total_shipping_deducted",
        "net_payout_received",
        "shipment_count",
        "reconciled_badge",
        "created_at",
    ]
    list_filter = [
        "courier",
        "is_reconciled",
        "payout_date",
    ]
    search_fields = [
        "settlement_reference",
    ]
    ordering = ["-payout_date"]
    list_per_page = 20

    # ── Change form ────────────────────────────────────────────────────────

    readonly_fields = [
        "courier",
        "settlement_reference",
        "total_cod_collected",
        "total_shipping_deducted",
        "net_payout_received",
        "payout_date",
        "is_reconciled",
        "created_at",
        "updated_at",
        "arithmetic_check",
    ]
    fieldsets = (
        (_("Bank Transfer Details"), {
            "fields": (
                "courier",
                "settlement_reference",
                "payout_date",
            ),
        }),
        (_("Financial Summary"), {
            "fields": (
                "total_cod_collected",
                "total_shipping_deducted",
                "net_payout_received",
                "arithmetic_check",
            ),
        }),
        (_("Status"), {
            "fields": (
                "is_reconciled",
                "created_at",
                "updated_at",
            ),
        }),
    )

    # ── Add form ───────────────────────────────────────────────────────────

    add_fieldsets = (
        (_("Bank Transfer Details"), {
            "fields": (
                "courier",
                "settlement_reference",
                "payout_date",
            ),
        }),
        (_("Financial Amounts"), {
            "fields": (
                "total_cod_collected",
                "total_shipping_deducted",
                "net_payout_received",
            ),
        }),
        (_("Shipments Covered"), {
            "fields": ("shipments_included",),
            "description": _(
                "Select all shipments covered by this bank transfer. "
                "Only DELIVERED shipments are shown. "
                "Match tracking numbers against the courier settlement report."
            ),
        }),
    )

    filter_horizontal = ["shipments_included"]

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return super().get_fieldsets(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            # Add form — nothing locked except is_reconciled
            return ["is_reconciled"]
        return self.readonly_fields

    # ── M2M widget — restrict to DELIVERED shipments only ─────────────────

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Limit shipments_included M2M widget to DELIVERED shipments
        that are not already in another settlement.

        This prevents finance team from accidentally selecting:
            - In-transit shipments (COD not yet collected)
            - Already-settled shipments (would duplicate the record)
        """
        if db_field.name == "shipments_included":
            kwargs["queryset"] = (
                Shipment.objects
                .filter(status=Shipment.Status.DELIVERED)
                .exclude(settlements__isnull=False)
                .select_related("order")
                .order_by("-created_at")
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    # ── save_model — delegates to SettlementService ───────────────────────

    def save_model(self, request, obj, form, change):
        """
        Route through SettlementService.create_settlement() on add.

        On change: settlement fields are all readonly — only M2M
        changes could come through here, which we do not allow
        after creation. has_change_permission blocks edits on
        reconciled settlements entirely.
        """
        if change:
            # Existing settlement — fields are readonly
            # This path should not be reachable for reconciled settlements
            # because has_change_permission returns False for them.
            # For non-reconciled settlements, admin form only shows
            # readonly fields so nothing can actually be changed.
            self.message_user(
                request,
                _(
                    "Settlement fields cannot be edited after creation. "
                    "Use the 'Mark as reconciled' action to reconcile."
                ),
                level=messages.WARNING,
            )
            return

        # ── New settlement ─────────────────────────────────────────────────

        # Extract M2M shipment IDs from the form
        # form.cleaned_data["shipments_included"] is a QuerySet
        shipment_ids = list(
            form.cleaned_data.get("shipments_included", [])
            .values_list("pk", flat=True)
        )

        try:
            settlement = SettlementService.create_settlement(
                courier=form.cleaned_data["courier"],
                settlement_reference=form.cleaned_data["settlement_reference"],
                total_cod_collected=form.cleaned_data["total_cod_collected"],
                total_shipping_deducted=form.cleaned_data["total_shipping_deducted"],
                net_payout_received=form.cleaned_data["net_payout_received"],
                payout_date=form.cleaned_data["payout_date"],
                shipment_ids=shipment_ids,
                created_by=request.user,
            )

            # Assign PK so Django admin redirects correctly
            obj.pk = settlement.pk

            self.message_user(
                request,
                _(
                    f"Settlement '{settlement.settlement_reference}' "
                    f"created successfully. "
                    f"{settlement.shipments_included.count()} shipment(s) "
                    f"linked. Net payout: Rs. {settlement.net_payout_received}."
                ),
                level=messages.SUCCESS,
            )

        except DomainError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)
            logger.warning(
                "CourierSettlementAdmin.save_model: DomainError | "
                "reference=%s admin=%s error=%s",
                form.cleaned_data.get("settlement_reference", "?"),
                request.user.pk,
                str(exc),
            )

        except Exception as exc:
            logger.exception(
                "CourierSettlementAdmin.save_model: unexpected error | "
                "reference=%s admin=%s",
                form.cleaned_data.get("settlement_reference", "?"),
                request.user.pk,
            )
            self.message_user(
                request,
                _(f"Unexpected error creating settlement: {exc}"),
                level=messages.ERROR,
            )

    # ── Permissions ────────────────────────────────────────────────────────

    def has_delete_permission(self, request, obj=None) -> bool:
        """
        Financial records are permanent — no deletion via admin.
        """
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        """
        Reconciled settlements are fully locked.
        Non-reconciled settlements show readonly fields only —
        change form exists solely to display details and run actions.
        """
        if obj is not None and obj.is_reconciled:
            return False
        return super().has_change_permission(request, obj)

    # ── Actions ────────────────────────────────────────────────────────────

    actions = ["mark_as_reconciled"]

    @admin.action(description=_("Mark selected settlements as reconciled ✓"))
    def mark_as_reconciled(self, request, queryset):
        """
        Mark selected settlements as reconciled.

        Called after finance team verifies net_payout_received
        against the actual bank statement credit.

        Calls SettlementService.reconcile() per settlement —
        enforces one-way rule and raises DomainError if already done.
        """
        reconciled = 0
        skipped = 0

        for settlement in queryset:
            try:
                SettlementService.reconcile(
                    settlement=settlement,
                    reconciled_by=request.user,
                )
                reconciled += 1
            except DomainError as exc:
                skipped += 1
                self.message_user(
                    request,
                    f"{settlement.settlement_reference}: {exc}",
                    level=messages.WARNING,
                )
            except Exception as exc:
                skipped += 1
                logger.exception(
                    "CourierSettlementAdmin.mark_as_reconciled: "
                    "unexpected error | reference=%s admin=%s",
                    settlement.settlement_reference,
                    request.user.pk,
                )
                self.message_user(
                    request,
                    _(
                        f"Unexpected error reconciling "
                        f"'{settlement.settlement_reference}': {exc}"
                    ),
                    level=messages.ERROR,
                )

        if reconciled:
            self.message_user(
                request,
                _(f"{reconciled} settlement(s) marked as reconciled."),
                level=messages.SUCCESS,
            )
        if skipped:
            self.message_user(
                request,
                _(f"{skipped} settlement(s) skipped — see warnings above."),
                level=messages.WARNING,
            )

    # ── Display helpers ────────────────────────────────────────────────────

    @admin.display(description=_("Shipments"), ordering=None)
    def shipment_count(self, obj: CourierSettlement) -> int:
        """Number of shipments linked to this settlement."""
        return obj.shipments_included.count()

    @admin.display(description=_("Reconciled"), ordering="is_reconciled")
    def reconciled_badge(self, obj: CourierSettlement) -> str:
        """Coloured badge for reconciliation status."""
        if obj.is_reconciled:
            return format_html(
                '<span style="background:#198754;color:#fff;'
                'padding:2px 8px;border-radius:4px;font-size:0.8em">'
                "✓ Reconciled</span>"
            )
        return format_html(
            '<span style="background:#ffc107;color:#000;'
            'padding:2px 8px;border-radius:4px;font-size:0.8em">'
            "Pending</span>"
        )

    @admin.display(description=_("Arithmetic Check"))
    def arithmetic_check(self, obj: CourierSettlement) -> str:
        """
        Shows expected net vs actual net_payout_received.
        Helps finance team spot discrepancies at a glance.
        """
        expected = obj.total_cod_collected - obj.total_shipping_deducted
        diff = obj.net_payout_received - expected

        if abs(diff) <= Decimal("1.00"):
            return format_html(
                '<span style="color:#198754">'
                "✓ Matches — Expected: Rs. {} | Received: Rs. {}"
                "</span>",
                expected,
                obj.net_payout_received,
            )
        return format_html(
            '<span style="color:#dc3545">'
            "⚠ Mismatch — Expected: Rs. {} | Received: Rs. {} | "
            "Difference: Rs. {}"
            "</span>",
            expected,
            obj.net_payout_received,
            diff,
        )
# # apps/logistics/admin.py
# from __future__ import annotations

# """
# Logistics app — Django admin registration.

# ShipmentStatusLog is immutable — no add, change, or delete permitted.
# Status changes go through ShipmentService.update_status() via the
# custom admin action — never via direct field edit.
# CourierSettlement is Phase 3 — not registered here yet.
# """

# from django.contrib import admin
# from django.utils.translation import gettext_lazy as _

# from .models import Shipment, ShipmentStatusLog
# from .services.shipment_service import ShipmentService


# # ─────────────────────────────────────────────────────────────────────────────
# # INLINES
# # ─────────────────────────────────────────────────────────────────────────────


# class ShipmentStatusLogInline(admin.TabularInline):
#     """
#     Displays the full audit trail of status transitions on Shipment page.
#     Append-only — ShipmentStatusLog.save() raises ValueError on update.
#     """

#     model = ShipmentStatusLog
#     can_delete = False
#     extra = 0
#     readonly_fields = [
#         "from_status",
#         "to_status",
#         "source",
#         "created_at",
#     ]

#     def has_add_permission(self, request, obj=None) -> bool:
#         return False


# # ─────────────────────────────────────────────────────────────────────────────
# # SHIPMENT ADMIN
# # ─────────────────────────────────────────────────────────────────────────────


# @admin.register(Shipment)
# class ShipmentAdmin(admin.ModelAdmin):
#     """
#     Admin interface for Shipment management.

#     Status changes are performed via the custom admin actions
#     which call ShipmentService.update_status() — never via direct
#     field edit. This ensures ShipmentStatusLog is always written
#     and Order status is always synchronized.
#     """

#     list_display = [
#         "tracking_number",
#         "order",
#         "courier",
#         "status",
#         "shipment_type",
#         "is_cod",
#         "cod_amount",
#         "destination_city",
#         "created_at",
#     ]
#     list_filter = [
#         "status",
#         "courier",
#         "shipment_type",
#         "is_cod",
#     ]
#     search_fields = [
#         "tracking_number",
#         "order__order_number",
#         "destination_city",
#     ]
#     readonly_fields = [
#         "order",
#         "tracking_number",
#         "courier",
#         "shipment_type",
#         "is_cod",
#         "cod_amount",
#         "destination_city",
#         "raw_courier_response",
#         "actual_delivery_date",
#         "created_at",
#         "updated_at",
#     ]
#     inlines = [ShipmentStatusLogInline]
#     actions = [
#         "action_mark_picked_up",
#         "action_mark_in_transit",
#         "action_mark_out_for_delivery",
#         "action_mark_delivered",
#         "action_mark_rto_delivered",
#     ]

#     def has_add_permission(self, request) -> bool:
#         """
#         Shipments created via POST /api/logistics/shipments/ only.
#         Manual admin creation bypasses service layer validation.
#         """
#         return True

#     def _bulk_status_action(self, request, queryset, new_status, label):
#         """
#         Shared helper for all bulk status update admin actions.

#         Calls ShipmentService.update_status() per shipment so that
#         ShipmentStatusLog is created and Order is synchronized for each.
#         Reports success and skip counts to admin interface.
#         """
#         updated = 0
#         skipped = 0
#         for shipment in queryset:
#             if shipment.status == new_status:
#                 skipped += 1
#                 continue
#             try:
#                 ShipmentService.update_status(
#                     shipment=shipment,
#                     new_status=new_status,
#                     source=ShipmentStatusLog.Source.MANUAL,
#                     updated_by=request.user,
#                 )
#                 updated += 1
#             except Exception as exc:
#                 logger_ref = __import__("logging").getLogger("apps.logistics")
#                 logger_ref.error(
#                     "ShipmentAdmin bulk action error | "
#                     "tracking=%s new_status=%s error=%s",
#                     shipment.tracking_number,
#                     new_status,
#                     str(exc),
#                 )
#                 skipped += 1

#         if updated:
#             self.message_user(
#                 request,
#                 _(f"{updated} shipment(s) marked as {label}."),
#             )
#         if skipped:
#             self.message_user(
#                 request,
#                 _(f"{skipped} shipment(s) skipped."),
#                 level="warning",
#             )

#     @admin.action(description=_("Mark selected as Picked Up"))
#     def action_mark_picked_up(self, request, queryset):
#         self._bulk_status_action(
#             request, queryset, Shipment.Status.PICKED_UP, "Picked Up"
#         )

#     @admin.action(description=_("Mark selected as In Transit"))
#     def action_mark_in_transit(self, request, queryset):
#         self._bulk_status_action(
#             request, queryset, Shipment.Status.IN_TRANSIT, "In Transit"
#         )

#     @admin.action(description=_("Mark selected as Out for Delivery"))
#     def action_mark_out_for_delivery(self, request, queryset):
#         self._bulk_status_action(
#             request, queryset, Shipment.Status.OUT_FOR_DELIVERY, "Out for Delivery"
#         )

#     @admin.action(description=_("Mark selected as Delivered"))
#     def action_mark_delivered(self, request, queryset):
#         self._bulk_status_action(
#             request, queryset, Shipment.Status.DELIVERED, "Delivered"
#         )

#     @admin.action(description=_("Mark selected as RTO Delivered (stock restored)"))
#     def action_mark_rto_delivered(self, request, queryset):
#         self._bulk_status_action(
#             request, queryset, Shipment.Status.RTO_DELIVERED, "RTO Delivered"
#         )


# # ─────────────────────────────────────────────────────────────────────────────
# # SHIPMENT STATUS LOG ADMIN
# # ─────────────────────────────────────────────────────────────────────────────


# @admin.register(ShipmentStatusLog)
# class ShipmentStatusLogAdmin(admin.ModelAdmin):
#     """
#     Admin interface for ShipmentStatusLog — fully immutable audit trail.
#     No add, change, or delete permitted.
#     """

#     list_display = [
#         "shipment",
#         "from_status",
#         "to_status",
#         "source",
#         "created_at",
#     ]
#     readonly_fields = [
#         "shipment",
#         "from_status",
#         "to_status",
#         "source",
#         "raw_webhook_data",
#         "created_at",
#     ]

#     def has_add_permission(self, request) -> bool:
#         return False

#     def has_change_permission(self, request, obj=None) -> bool:
#         return False

#     def has_delete_permission(self, request, obj=None) -> bool:
#         return False