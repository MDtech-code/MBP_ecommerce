// src/entities/checkout/model/checkoutStore.js

import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { immer } from "zustand/middleware/immer";
import {
  getProvinceForCity,
  getPostalForCity,
  getShippingFee,
} from "@shared/lib/locationData";

/**
 * checkoutStore — multi-step checkout state.
 *
 * Persists state across the two checkout steps:
 *   Step 1 — /checkout/address  (address selection)
 *   Step 2 — /checkout/payment  (payment method + place order)
 *
 * Set on cart page before entering checkout:
 *   selectedItemIds — which cart item IDs to checkout
 *   selectedItems   — full item objects for summary display
 *
 * Cleared after successful order placement via clearCheckoutStore().
 *
 * Why Zustand not React Router state:
 *   Router state is lost on page refresh.
 *   Checkout steps must survive accidental refresh without
 *   forcing user to restart selection from cart.
 *
 * Why not React Query:
 *   This is pure client UI state — no server sync needed.
 *   Zustand is correct for this.
 *
 * FSD layer: entities/checkout/model
 *   Same pattern as entities/user/model/authStore.js
 */

const INITIAL_ADDRESS_FORM = {
  full_name: "",
  phone: "",
  address_line1: "",
  address_line2: "",
  city: "",
  province: "", // auto-derived from city
  postal_code: "", // auto-derived from city
};

const INITIAL_STATE = {
  // ── Step 0 — Item selection (set on cart page) ──────────────────────────
  selectedItemIds: [], // number[] — CartItem IDs
  selectedItems: [], // CartItem objects — for summary display

  // ── Step 1 — Address ────────────────────────────────────────────────────
  addressMode: "saved", // "saved" | "new"
  selectedAddressId: null, // number | null — ID of chosen saved address
  addressForm: { ...INITIAL_ADDRESS_FORM },

  // ── Step 2 — Payment ────────────────────────────────────────────────────
  paymentMethod: "cod", // only "cod" active currently
  notes: "",

  // ── Derived ─────────────────────────────────────────────────────────────
  shippingFee: null, // number | null — null = "Calculated at checkout"
};

export const useCheckoutStore = create(
  devtools(
    immer((set, get) => ({
      ...INITIAL_STATE,

      // ── Selection actions ────────────────────────────────────────────────

      /**
       * Set selected items in one call — used when navigating from cart to checkout.
       * @param {number[]} ids     — CartItem IDs
       * @param {object[]} items   — full CartItem objects
       */
      setSelectedItems: (ids, items) =>
        set((state) => {
          state.selectedItemIds = ids;
          state.selectedItems = items;
        }),

      /**
       * Toggle a single item in/out of selection.
       * @param {number} id    — CartItem.id
       * @param {object} item  — full CartItem object
       */
      toggleItem: (id, item) =>
        set((state) => {
          const exists = state.selectedItemIds.includes(id);
          if (exists) {
            state.selectedItemIds = state.selectedItemIds.filter(
              (i) => i !== id,
            );
            state.selectedItems = state.selectedItems.filter(
              (i) => i.id !== id,
            );
          } else {
            state.selectedItemIds.push(id);
            state.selectedItems.push(item);
          }
        }),

      /**
       * Select all cart items at once.
       * @param {object[]} items — all CartItem objects from useCart
       */
      selectAll: (items) =>
        set((state) => {
          state.selectedItemIds = items.map((i) => i.id);
          state.selectedItems = [...items];
        }),

      /**
       * Deselect all items.
       */
      clearSelection: () =>
        set((state) => {
          state.selectedItemIds = [];
          state.selectedItems = [];
        }),

      /**
       * Check if a specific item is selected.
       * @param {number} id
       * @returns {boolean}
       */
      isItemSelected: (id) => get().selectedItemIds.includes(id),

      // ── Address actions ──────────────────────────────────────────────────

      /**
       * Switch between saved address mode and new address form mode.
       * @param {"saved"|"new"} mode
       */
      setAddressMode: (mode) =>
        set((state) => {
          state.addressMode = mode;
          // When switching to new, clear form so it starts fresh
          if (mode === "new") {
            state.selectedAddressId = null;
            state.addressForm = { ...INITIAL_ADDRESS_FORM };
            state.shippingFee = null;
          }
        }),

      /**
       * Record which saved address the user selected.
       * @param {number} id
       */
      setSelectedAddressId: (id) =>
        set((state) => {
          state.selectedAddressId = id;
        }),

      /**
       * Populate address form from a saved UserAddress object.
       * Called when user selects a saved address card.
       * Maps UserAddressSerializer fields → addressForm fields.
       *
       * Note: full_name is not on UserAddress — user must provide it.
       * Pre-populate from profile full_name if available (passed by caller).
       *
       * @param {object} address — UserAddressSerializer output
       * @param {string} fullName — from user profile (optional)
       */
      populateAddressForm: (address, fullName = "") =>
        set((state) => {
          state.addressForm = {
            full_name: fullName || state.addressForm.full_name,
            phone: address.phone || "",
            address_line1: address.address_line1,
            address_line2: address.address_line2 || "",
            city: address.city,
            province: address.province,
            postal_code: address.postal_code,
          };
          state.shippingFee = getShippingFee(address.city);
        }),

      /**
       * Update a single address form field.
       * When field is "city", auto-derives province, postal_code, shippingFee.
       * Mirrors UserAddress.save() and checkoutStore city logic.
       *
       * @param {string} field
       * @param {string} value
       */
      updateAddressField: (field, value) =>
        set((state) => {
          state.addressForm[field] = value;

          if (field === "city") {
            state.addressForm.province = getProvinceForCity(value);
            state.addressForm.postal_code = getPostalForCity(value);
            state.shippingFee = getShippingFee(value);
          }
        }),

      // ── Payment actions ──────────────────────────────────────────────────

      /**
       * @param {"cod"|"online"|"bank_transfer"} method
       */
      setPaymentMethod: (method) =>
        set((state) => {
          state.paymentMethod = method;
        }),

      /**
       * @param {string} notes — max 500 chars, enforced by backend
       */
      setNotes: (notes) =>
        set((state) => {
          state.notes = notes;
        }),

      // ── Reset ────────────────────────────────────────────────────────────

      /**
       * Full reset to initial state.
       * Called after successful order placement.
       * Do NOT call on navigation away — user might come back.
       */
      clearCheckoutStore: () => set(() => ({ ...INITIAL_STATE })),
    })),
    { name: "CheckoutStore" },
  ),
);
