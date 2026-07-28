// src/features/checkout/model/useCheckoutPayment.js

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { orderService } from "@shared/api";
import { normalizeError } from "@shared/api";
import { useCheckoutStore } from "@entities/checkout/model/checkoutStore";

/**
 * useCheckoutPayment — logic hook for /checkout/payment step.
 *
 * Responsibilities:
 *   - Reads checkout state from checkoutStore (items, address, payment)
 *   - Builds the POST /api/orders/checkout/ payload
 *   - Executes the checkout mutation
 *   - On success: clears checkout store, invalidates cart, navigates to order
 *   - On error: normalizes and exposes error message + code for UI
 *   - Exposes payment method selection and notes handlers
 *
 * Payload shape sent to backend:
 *   {
 *     payment_method: "cod",
 *     notes: "",
 *     selected_item_ids: [1, 2, 3],
 *     shipping_address: {
 *       full_name: "...",
 *       phone: "...",
 *       address_line1: "...",
 *       address_line2: "...",
 *       city: "...",
 *       province: "...",    ← auto-derived, sent to backend
 *       postal_code: "...", ← auto-derived, sent to backend
 *     }
 *   }
 *
 * Note: coupon is NOT in payload — already applied on cart.
 * Backend reads cart.coupon directly during checkout.
 *
 * Error codes handled:
 *   cart_empty           → redirect to /cart
 *   product_unavailable  → show banner with product names
 *   insufficient_stock   → show stock error
 *   coupon_invalid       → suggest removing coupon
 *   coupon_already_used  → specific message
 *   coupon_limit_reached → specific message
 *   coupon_expired       → specific message
 *   invalid_cart_items   → return to cart
 *   validation errors    → field-level (unlikely at this stage)
 *   network/server error → generic message
 */
export function useCheckoutPayment() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // ── Checkout store ───────────────────────────────────────────────────────
  const paymentMethod = useCheckoutStore((s) => s.paymentMethod);
  const notes = useCheckoutStore((s) => s.notes);
  const addressForm = useCheckoutStore((s) => s.addressForm);
  const shippingFee = useCheckoutStore((s) => s.shippingFee);
  const selectedItems = useCheckoutStore((s) => s.selectedItems);
  const selectedItemIds = useCheckoutStore((s) => s.selectedItemIds);

  const setPaymentMethod = useCheckoutStore((s) => s.setPaymentMethod);
  const setNotes = useCheckoutStore((s) => s.setNotes);
  const clearCheckoutStore = useCheckoutStore((s) => s.clearCheckoutStore);

  // ── Checkout mutation ────────────────────────────────────────────────────
  const mutation = useMutation({
    mutationFn: (payload) => orderService.checkout(payload),

    onSuccess: (result) => {
      // 1. Clear checkout store — selection, address, payment all reset
      clearCheckoutStore();

      // 2. Invalidate cart — partial items were removed from cart
      //    Cart badge and cart page will refetch and show remaining items
      queryClient.invalidateQueries({ queryKey: ["cart"] });

      // 3. Navigate to order detail page
      const orderNumber = result.data?.order_number;
      navigate(`/orders/${orderNumber}`);
    },
  });

  // ── Error normalization ──────────────────────────────────────────────────
  const normalized = mutation.error ? normalizeError(mutation.error) : null;
  const errorMessage = normalized?.message ?? null;
  const errorCode = normalized?.errors?.non_fields?.code ?? null;

  // ── Place order handler ──────────────────────────────────────────────────
  const handlePlaceOrder = () => {
    const payload = {
      payment_method: paymentMethod,
      notes: notes,
      selected_item_ids: selectedItemIds,
      shipping_address: {
        full_name: addressForm.full_name,
        phone: addressForm.phone,
        address_line1: addressForm.address_line1,
        address_line2: addressForm.address_line2 ?? "",
        city: addressForm.city,
        province: addressForm.province,
        postal_code: addressForm.postal_code,
      },
    };
    mutation.mutate(payload);
  };

  // ── Return ───────────────────────────────────────────────────────────────
  return {
    // State for UI rendering
    paymentMethod,
    notes,
    addressForm,
    shippingFee,
    selectedItems,
    selectedItemIds,

    // Handlers
    setPaymentMethod,
    setNotes,
    handlePlaceOrder,

    // Mutation state
    isPlacing: mutation.isPending,
    isSuccess: mutation.isSuccess,
    errorMessage,
    errorCode,
  };
}
