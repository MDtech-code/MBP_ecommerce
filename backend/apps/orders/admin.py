# apps/orders/admin.py
from __future__ import annotations

"""
Order app — Django admin registration.

Design decisions:
    Order is created exclusively via OrderService.checkout().
    has_add_permission=False on OrderAdmin — no manual creation allowed.
    All financial snapshot fields are readonly — immutable after creation.
    Status changes go through custom admin action calling transition_to()
    so audit log is always created — never via direct field edit.
    OrderStatusLog: fully immutable — no add, change, or delete permitted.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Order, OrderItem, OrderShippingAddress, OrderStatusLog


# ─────────────────────────────────────────────────────────────────────────────
# INLINES
# ─────────────────────────────────────────────────────────────────────────────


class OrderShippingAddressInline(admin.StackedInline):
    model = OrderShippingAddress
    can_delete = False
    max_num = 1
    extra = 0
    readonly_fields = [
        "full_name", "phone", "address_line1", "address_line2",
        "city", "province", "postal_code", "country", "full_address",
    ]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    can_delete = False
    extra = 0
    readonly_fields = [
        "product", "product_name", "product_sku", "original_price",
        "unit_price", "quantity", "subtotal", "discount_amount",
        "tax_rate_percentage", "tax_amount",
    ]


class OrderStatusLogInline(admin.TabularInline):
    model = OrderStatusLog
    can_delete = False
    extra = 0
    readonly_fields = [
        "from_status", "to_status", "changed_by", "note", "created_at",
    ]


# ─────────────────────────────────────────────────────────────────────────────
# ORDER ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Admin interface for Order management.

    Orders are created via checkout only — has_add_permission=False.
    Status transitions are performed via custom actions which call
    order.transition_to() — never via direct field edit.
    All financial fields are readonly — frozen snapshot at placement time.

    Testing bypass actions (DEV/TESTING only):
        action_bypass_to_processing — CONFIRMED → PROCESSING
        action_bypass_to_shipped    — PROCESSING → SHIPPED
        action_bypass_to_delivered  — SHIPPED → DELIVERED

        These bypass actions skip courier API and Shipment record creation.
        They call order.transition_to() directly — audit log is still written.
        Use these when courier credentials are not yet configured.

        When real courier credentials are available:
            Remove these three actions.
            Use ShipmentAdmin to create shipments (triggers PROCESSING).
            Use ShipmentAdmin status actions for SHIPPED and DELIVERED.
    """

    list_display = [
        "order_number", "user", "status",
        "payment_method", "total_price", "placed_at",
    ]
    list_filter  = ["status", "payment_method", "placed_at"]
    search_fields = ["order_number", "user__email"]
    readonly_fields = [
        "order_number", "user", "placed_at", "confirmed_at",
        "processed_at", "shipped_at", "delivered_at", "cancelled_at",
        "refunded_at", "subtotal", "shipping_fee", "discount_amount",
        "tax_amount", "total_price", "coupon", "coupon_code_snapshot",
        "payment_status",
    ]
    inlines = [
        OrderShippingAddressInline,
        OrderItemInline,
        OrderStatusLogInline,
    ]
    actions = [
        "action_confirm_orders",
        "action_bypass_to_processing",
        "action_bypass_to_shipped",
        "action_bypass_to_delivered",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def payment_status(self, obj: Order) -> str:
        return obj.payment_status

    payment_status.short_description = _("Payment Status")

    # ─────────────────────────────────────────────────────────────────────
    # PRODUCTION ACTION
    # ─────────────────────────────────────────────────────────────────────

    @admin.action(description=_("✓ Confirm selected orders (PENDING → CONFIRMED)"))
    def action_confirm_orders(self, request, queryset):
        """
        Transition selected PENDING orders to CONFIRMED via the state machine.
        Calls order.transition_to() — creates OrderStatusLog + sets confirmed_at.
        Skips orders not in PENDING status.
        """
        confirmed = skipped = 0

        for order in queryset:
            if order.can_transition_to(Order.Status.CONFIRMED):
                order.transition_to(
                    Order.Status.CONFIRMED,
                    changed_by=request.user,
                    note="Confirmed via admin bulk action.",
                )
                confirmed += 1
            else:
                skipped += 1

        if confirmed:
            self.message_user(
                request,
                _(f"{confirmed} order(s) confirmed successfully."),
            )
        if skipped:
            self.message_user(
                request,
                _(f"{skipped} order(s) skipped — not in PENDING status."),
                level="warning",
            )

    # ─────────────────────────────────────────────────────────────────────
    # TESTING BYPASS ACTIONS
    # Remove these three actions when courier credentials are configured.
    # Replace with ShipmentAdmin workflow for production use.
    # ─────────────────────────────────────────────────────────────────────

    @admin.action(description=_(
        "[TEST] Bypass → PROCESSING (CONFIRMED → PROCESSING, no shipment created)"
    ))
    def action_bypass_to_processing(self, request, queryset):
        """
        DEV/TESTING ONLY — bypass courier API.

        Transitions CONFIRMED orders directly to PROCESSING without
        creating a Shipment record. Audit log is still written via
        transition_to(). processed_at timestamp is set automatically.

        In production: delete this action. Use ShipmentAdmin to create
        a shipment — that triggers PROCESSING via ShipmentService.
        """
        ok = skipped = 0

        for order in queryset:
            if order.can_transition_to(Order.Status.PROCESSING):
                order.transition_to(
                    Order.Status.PROCESSING,
                    changed_by=request.user,
                    note=(
                        "[BYPASS] Manually advanced to PROCESSING for testing. "
                        "No shipment record created. "
                        "Replace with ShipmentAdmin workflow in production."
                    ),
                )
                ok += 1
            else:
                skipped += 1
                self.message_user(
                    request,
                    _(
                        f"Order {order.order_number} skipped — "
                        f"current status '{order.status}' cannot "
                        f"transition to PROCESSING."
                    ),
                    level="warning",
                )

        if ok:
            self.message_user(
                request,
                _(f"{ok} order(s) → PROCESSING (bypass, no shipment)."),
            )

    @admin.action(description=_(
        "[TEST] Bypass → SHIPPED (PROCESSING → SHIPPED, no courier update)"
    ))
    def action_bypass_to_shipped(self, request, queryset):
        """
        DEV/TESTING ONLY — bypass courier API.

        Transitions PROCESSING orders directly to SHIPPED without
        a courier PICKED_UP webhook. Audit log is still written.
        shipped_at timestamp is set automatically.

        In production: delete this action. Use ShipmentAdmin action
        'mark_picked_up' — that syncs order to SHIPPED via
        ShipmentService.update_status().
        """
        ok = skipped = 0

        for order in queryset:
            if order.can_transition_to(Order.Status.SHIPPED):
                order.transition_to(
                    Order.Status.SHIPPED,
                    changed_by=request.user,
                    note=(
                        "[BYPASS] Manually advanced to SHIPPED for testing. "
                        "No courier PICKED_UP event processed. "
                        "Replace with ShipmentAdmin mark_picked_up in production."
                    ),
                )
                ok += 1
            else:
                skipped += 1
                self.message_user(
                    request,
                    _(
                        f"Order {order.order_number} skipped — "
                        f"current status '{order.status}' cannot "
                        f"transition to SHIPPED."
                    ),
                    level="warning",
                )

        if ok:
            self.message_user(
                request,
                _(f"{ok} order(s) → SHIPPED (bypass, no courier update)."),
            )

    @admin.action(description=_(
        "[TEST] Bypass → DELIVERED (SHIPPED → DELIVERED, no COD payment update)"
    ))
    def action_bypass_to_delivered(self, request, queryset):
        """
        DEV/TESTING ONLY — bypass courier API and payment update.

        Transitions SHIPPED orders directly to DELIVERED without
        a courier DELIVERED webhook or COD PaymentTransaction update.
        Audit log is still written. delivered_at timestamp is set.

        In production: delete this action. Use ShipmentAdmin action
        'mark_delivered' — that calls ShipmentService._handle_delivered()
        which also marks COD PaymentTransaction as SUCCESS.

        COD note: PaymentTransaction stays PENDING after this bypass.
        That is acceptable for testing — in production the service
        handles it atomically.
        """
        ok = skipped = 0

        for order in queryset:
            if order.can_transition_to(Order.Status.DELIVERED):
                order.transition_to(
                    Order.Status.DELIVERED,
                    changed_by=request.user,
                    note=(
                        "[BYPASS] Manually advanced to DELIVERED for testing. "
                        "No courier DELIVERED event processed. "
                        "COD PaymentTransaction NOT updated to SUCCESS. "
                        "Replace with ShipmentAdmin mark_delivered in production."
                    ),
                )
                ok += 1
            else:
                skipped += 1
                self.message_user(
                    request,
                    _(
                        f"Order {order.order_number} skipped — "
                        f"current status '{order.status}' cannot "
                        f"transition to DELIVERED."
                    ),
                    level="warning",
                )

        if ok:
            self.message_user(
                request,
                _(
                    f"{ok} order(s) → DELIVERED (bypass, no courier event, "
                    f"COD payment NOT updated)."
                ),
            )


# ─────────────────────────────────────────────────────────────────────────────
# ORDER STATUS LOG ADMIN
# ─────────────────────────────────────────────────────────────────────────────


@admin.register(OrderStatusLog)
class OrderStatusLogAdmin(admin.ModelAdmin):
    """
    Admin interface for OrderStatusLog — fully immutable audit trail.
    FBR tax compliance requires 6-year retention of financial records.
    No add, change, or delete permitted via admin.
    """

    list_display = [
        "order", "from_status", "to_status", "changed_by", "created_at",
    ]
    readonly_fields = [
        "order", "from_status", "to_status", "changed_by", "note", "created_at",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
#! commented code is important
# # apps/orders/admin.py
# from __future__ import annotations

# """
# Order app — Django admin registration.

# Design decisions:
#     Order is created exclusively via OrderService.checkout().
#     has_add_permission=False on OrderAdmin — no manual creation allowed.
#     All financial snapshot fields are readonly — immutable after creation.
#     Status changes go through custom admin action calling transition_to()
#     so audit log is always created — never via direct field edit.
#     OrderStatusLog: fully immutable — no add, change, or delete permitted.
# """

# from django.contrib import admin
# from django.utils import timezone
# from django.utils.translation import gettext_lazy as _

# from .models import Order, OrderItem, OrderShippingAddress, OrderStatusLog


# # ─────────────────────────────────────────────────────────────────────────────
# # INLINES
# # ─────────────────────────────────────────────────────────────────────────────


# class OrderShippingAddressInline(admin.StackedInline):
#     """
#     Displays the immutable shipping address snapshot inline on the Order page.
#     All fields readonly — OrderShippingAddress.save() raises ValueError on update.
#     """

#     model = OrderShippingAddress
#     can_delete = False
#     max_num = 1
#     extra = 0
#     readonly_fields = [
#         "full_name",
#         "phone",
#         "address_line1",
#         "address_line2",
#         "city",
#         "province",
#         "postal_code",
#         "country",
#         "full_address",
#     ]


# class OrderItemInline(admin.TabularInline):
#     """
#     Displays all order line items inline on the Order page.
#     All fields readonly — price snapshots are immutable after creation.
#     """

#     model = OrderItem
#     can_delete = False
#     extra = 0
#     readonly_fields = [
#         "product",
#         "product_name",
#         "product_sku",
#         "original_price",
#         "unit_price",
#         "quantity",
#         "subtotal",
#         "discount_amount",
#         "tax_rate_percentage",
#         "tax_amount",
#     ]


# class OrderStatusLogInline(admin.TabularInline):
#     """
#     Displays the full audit trail of status transitions on the Order page.
#     Append-only — OrderStatusLog.save() raises ValueError on update.
#     """

#     model = OrderStatusLog
#     can_delete = False
#     extra = 0
#     readonly_fields = [
#         "from_status",
#         "to_status",
#         "changed_by",
#         "note",
#         "created_at",
#     ]


# # ─────────────────────────────────────────────────────────────────────────────
# # ORDER ADMIN
# # ─────────────────────────────────────────────────────────────────────────────


# @admin.register(Order)
# class OrderAdmin(admin.ModelAdmin):
#     """
#     Admin interface for Order management.

#     Orders are created via checkout only — has_add_permission=False.
#     Status transitions are performed via the confirm_orders custom
#     action which calls order.transition_to() — never via direct field edit.
#     All financial fields are readonly — frozen snapshot at placement time.
#     """

#     list_display = [
#         "order_number",
#         "user",
#         "status",
#         "payment_method",
#         "total_price",
#         "placed_at",
#     ]
#     list_filter = [
#         "status",
#         "payment_method",
#         "placed_at",
#     ]
#     search_fields = [
#         "order_number",
#         "user__email",
#     ]
#     readonly_fields = [
#         "order_number",
#         "user",
#         "placed_at",
#         "confirmed_at",
#         "processed_at",
#         "shipped_at",
#         "delivered_at",
#         "cancelled_at",
#         "refunded_at",
#         "subtotal",
#         "shipping_fee",
#         "discount_amount",
#         "tax_amount",
#         "total_price",
#         "coupon",
#         "coupon_code_snapshot",
#         "payment_status",
#     ]
#     inlines = [
#         OrderShippingAddressInline,
#         OrderItemInline,
#         OrderStatusLogInline,
#     ]
#     actions = ["action_confirm_orders"]

#     def has_add_permission(self, request) -> bool:
#         """
#         Orders are created exclusively via OrderService.checkout().
#         Manual creation via admin is not permitted.
#         """
#         return False

#     def payment_status(self, obj: Order) -> str:
#         """Display current payment status from PaymentTransaction."""
#         return obj.payment_status

#     payment_status.short_description = _("Payment Status")

#     @admin.action(description=_("Confirm selected orders (PENDING → CONFIRMED)"))
#     def action_confirm_orders(self, request, queryset):
#         """
#         Transition selected PENDING orders to CONFIRMED via the state machine.

#         Calls order.transition_to() for each order — this creates the
#         OrderStatusLog entry and sets confirmed_at automatically.
#         Skips orders that are not in PENDING status with a warning.
#         """
#         confirmed = 0
#         skipped   = 0
#         for order in queryset:
#             if order.can_transition_to(Order.Status.CONFIRMED):
#                 order.transition_to(
#                     Order.Status.CONFIRMED,
#                     changed_by=request.user,
#                     note="Confirmed via admin bulk action.",
#                 )
#                 confirmed += 1
#             else:
#                 skipped += 1

#         if confirmed:
#             self.message_user(
#                 request,
#                 _(f"{confirmed} order(s) confirmed successfully."),
#             )
#         if skipped:
#             self.message_user(
#                 request,
#                 _(
#                     f"{skipped} order(s) skipped — "
#                     f"not in PENDING status."
#                 ),
#                 level="warning",
#             )
    


# # ─────────────────────────────────────────────────────────────────────────────
# # ORDER STATUS LOG ADMIN
# # ─────────────────────────────────────────────────────────────────────────────


# @admin.register(OrderStatusLog)
# class OrderStatusLogAdmin(admin.ModelAdmin):
#     """
#     Admin interface for OrderStatusLog — fully immutable audit trail.

#     FBR tax compliance requires 6-year retention of financial records.
#     No add, change, or delete permitted via admin.
#     """

#     list_display = [
#         "order",
#         "from_status",
#         "to_status",
#         "changed_by",
#         "created_at",
#     ]
#     readonly_fields = [
#         "order",
#         "from_status",
#         "to_status",
#         "changed_by",
#         "note",
#         "created_at",
#     ]

#     def has_add_permission(self, request) -> bool:
#         return False

#     def has_change_permission(self, request, obj=None) -> bool:
#         return False

#     def has_delete_permission(self, request, obj=None) -> bool:
#         return False