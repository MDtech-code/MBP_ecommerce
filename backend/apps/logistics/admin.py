# apps/logistics/admin.py
from __future__ import annotations

"""
Logistics app — Django admin registration.

ShipmentStatusLog is immutable — no add, change, or delete permitted.
Status changes go through ShipmentService.update_status() via the
custom admin action — never via direct field edit.
CourierSettlement is Phase 3 — not registered here yet.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Shipment, ShipmentStatusLog
from .services.shipment_service import ShipmentService


# ─────────────────────────────────────────────────────────────────────────────
# INLINES
# ─────────────────────────────────────────────────────────────────────────────


class ShipmentStatusLogInline(admin.TabularInline):
    """
    Displays the full audit trail of status transitions on Shipment page.
    Append-only — ShipmentStatusLog.save() raises ValueError on update.
    """

    model = ShipmentStatusLog
    can_delete = False
    extra = 0
    readonly_fields = [
        "from_status",
        "to_status",
        "source",
        "created_at",
    ]

    def has_add_permission(self, request, obj=None) -> bool:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(Shipment)
class ShipmentAdmin(admin.ModelAdmin):
    """
    Admin interface for Shipment management.

    Status changes are performed via the custom admin actions
    which call ShipmentService.update_status() — never via direct
    field edit. This ensures ShipmentStatusLog is always written
    and Order status is always synchronized.
    """

    list_display = [
        "tracking_number",
        "order",
        "courier",
        "status",
        "shipment_type",
        "is_cod",
        "cod_amount",
        "destination_city",
        "created_at",
    ]
    list_filter = [
        "status",
        "courier",
        "shipment_type",
        "is_cod",
    ]
    search_fields = [
        "tracking_number",
        "order__order_number",
        "destination_city",
    ]
    readonly_fields = [
        "order",
        "tracking_number",
        "courier",
        "shipment_type",
        "is_cod",
        "cod_amount",
        "destination_city",
        "raw_courier_response",
        "actual_delivery_date",
        "created_at",
        "updated_at",
    ]
    inlines = [ShipmentStatusLogInline]
    actions = [
        "action_mark_picked_up",
        "action_mark_in_transit",
        "action_mark_out_for_delivery",
        "action_mark_delivered",
        "action_mark_rto_delivered",
    ]

    def has_add_permission(self, request) -> bool:
        """
        Shipments created via POST /api/logistics/shipments/ only.
        Manual admin creation bypasses service layer validation.
        """
        return False

    def _bulk_status_action(self, request, queryset, new_status, label):
        """
        Shared helper for all bulk status update admin actions.

        Calls ShipmentService.update_status() per shipment so that
        ShipmentStatusLog is created and Order is synchronized for each.
        Reports success and skip counts to admin interface.
        """
        updated = 0
        skipped = 0
        for shipment in queryset:
            if shipment.status == new_status:
                skipped += 1
                continue
            try:
                ShipmentService.update_status(
                    shipment=shipment,
                    new_status=new_status,
                    source=ShipmentStatusLog.Source.MANUAL,
                    updated_by=request.user,
                )
                updated += 1
            except Exception as exc:
                logger_ref = __import__("logging").getLogger("apps.logistics")
                logger_ref.error(
                    "ShipmentAdmin bulk action error | "
                    "tracking=%s new_status=%s error=%s",
                    shipment.tracking_number,
                    new_status,
                    str(exc),
                )
                skipped += 1

        if updated:
            self.message_user(
                request,
                _(f"{updated} shipment(s) marked as {label}."),
            )
        if skipped:
            self.message_user(
                request,
                _(f"{skipped} shipment(s) skipped."),
                level="warning",
            )

    @admin.action(description=_("Mark selected as Picked Up"))
    def action_mark_picked_up(self, request, queryset):
        self._bulk_status_action(
            request, queryset, Shipment.Status.PICKED_UP, "Picked Up"
        )

    @admin.action(description=_("Mark selected as In Transit"))
    def action_mark_in_transit(self, request, queryset):
        self._bulk_status_action(
            request, queryset, Shipment.Status.IN_TRANSIT, "In Transit"
        )

    @admin.action(description=_("Mark selected as Out for Delivery"))
    def action_mark_out_for_delivery(self, request, queryset):
        self._bulk_status_action(
            request, queryset, Shipment.Status.OUT_FOR_DELIVERY, "Out for Delivery"
        )

    @admin.action(description=_("Mark selected as Delivered"))
    def action_mark_delivered(self, request, queryset):
        self._bulk_status_action(
            request, queryset, Shipment.Status.DELIVERED, "Delivered"
        )

    @admin.action(description=_("Mark selected as RTO Delivered (stock restored)"))
    def action_mark_rto_delivered(self, request, queryset):
        self._bulk_status_action(
            request, queryset, Shipment.Status.RTO_DELIVERED, "RTO Delivered"
        )


# ─────────────────────────────────────────────────────────────────────────────
# SHIPMENT STATUS LOG ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(ShipmentStatusLog)
class ShipmentStatusLogAdmin(admin.ModelAdmin):
    """
    Admin interface for ShipmentStatusLog — fully immutable audit trail.
    No add, change, or delete permitted.
    """

    list_display = [
        "shipment",
        "from_status",
        "to_status",
        "source",
        "created_at",
    ]
    readonly_fields = [
        "shipment",
        "from_status",
        "to_status",
        "source",
        "raw_webhook_data",
        "created_at",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False