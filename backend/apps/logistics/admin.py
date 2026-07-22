import logging

from django.contrib import admin, messages
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.logistics.models import Shipment, ShipmentStatusLog
from apps.logistics.services.shipment_service import ShipmentService
from apps.core.exceptions import DomainError
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