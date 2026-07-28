// src/features/cart/model/useCart.js

import { useCartQuery } from "../api/useCartQueries";
import {
  useAddToCart,
  useUpdateCartItem,
  useRemoveCartItem,
  useClearCart,
  useApplyCoupon,
  useRemoveCoupon,
} from "../api/useCartMutations";
import { normalizeError } from "@shared/api";

/**
 * useCart — business logic hook for CartPage.
 *
 * Responsibilities:
 *   - Provides cart data (items, totals, coupon state) from backend
 *   - Provides all cart action handlers
 *   - Normalizes errors for UI display
 *
 * Backend cart fields now consumed:
 *   cart.items           → item list
 *   cart.total_items     → item count
 *   cart.subtotal        → sum of items before coupon discount
 *   cart.discount_amount → coupon discount in PKR (0.00 if no coupon)
 *   cart.total_price     → subtotal - discount (no shipping — unknown until checkout)
 *   cart.is_empty        → boolean
 *   cart.coupon          → coupon FK id (null if none applied)
 *   cart.coupon_code_input → last typed code preserved across sessions
 *
 * Financial truth:
 *   total_price from backend = subtotal - coupon discount
 *   Shipping NOT included — unknown until delivery address confirmed at checkout
 *   CartSummary shows "Calculated at checkout" for shipping
 */
export function useCart() {
  // ── Query ──────────────────────────────────────────────────────────────────
  const { data: cart, isLoading, isError, error } = useCartQuery();

  // ── Mutations ──────────────────────────────────────────────────────────────
  const addToCartMutation = useAddToCart();
  const updateItemMutation = useUpdateCartItem();
  const removeItemMutation = useRemoveCartItem();
  const clearCartMutation = useClearCart();
  const applyCouponMutation = useApplyCoupon();
  const removeCouponMutation = useRemoveCoupon();

  // ── Derived cart data ──────────────────────────────────────────────────────
  const items = cart?.items ?? [];
  const totalItems = cart?.total_items ?? 0;
  const subtotal = cart?.subtotal ?? "0.00"; // before coupon
  const discountAmount = cart?.discount_amount ?? "0.00"; // coupon discount
  const totalPrice = cart?.total_price ?? "0.00"; // subtotal - discount
  const isEmpty = cart?.is_empty ?? true;
  const couponId = cart?.coupon ?? null; // FK id or null
  const couponCodeInput = cart?.coupon_code_input ?? ""; // preserved code

  // ── Query error normalization ──────────────────────────────────────────────
  const normalized = isError ? normalizeError(error) : null;

  // ── Mutation error normalization ───────────────────────────────────────────
  // Cart item mutations (add, update, remove, clear)
  const mutationError =
    addToCartMutation.error ||
    updateItemMutation.error ||
    removeItemMutation.error ||
    clearCartMutation.error;

  const normalizedMutationError = mutationError
    ? normalizeError(mutationError)
    : null;

  // Coupon mutations — separate error channel so UI can show
  // coupon-specific error near the coupon input, not the main banner
  const couponMutationError =
    applyCouponMutation.error || removeCouponMutation.error;

  const normalizedCouponError = couponMutationError
    ? normalizeError(couponMutationError)
    : null;

  // ── Any mutation pending ───────────────────────────────────────────────────
  // Includes coupon mutations — disables all cart buttons during any operation
  const isMutating =
    addToCartMutation.isPending ||
    updateItemMutation.isPending ||
    removeItemMutation.isPending ||
    clearCartMutation.isPending ||
    applyCouponMutation.isPending ||
    removeCouponMutation.isPending;

  // Coupon-specific pending — used to show spinner on apply/remove button only
  const isCouponPending =
    applyCouponMutation.isPending || removeCouponMutation.isPending;

  // ── Handlers ───────────────────────────────────────────────────────────────

  const handleIncrease = (itemId, quantity) => {
    updateItemMutation.mutate({ itemId, quantity: quantity + 1 });
  };

  const handleDecrease = (itemId, quantity) => {
    updateItemMutation.mutate({ itemId, quantity: quantity - 1 });
  };

  const handleRemove = (itemId) => {
    removeItemMutation.mutate({ itemId });
  };

  const handleClearCart = () => {
    clearCartMutation.mutate();
  };

  const handleAddToCart = (productId, quantity = 1) => {
    addToCartMutation.mutate({ productId, quantity });
  };

  /**
   * Apply coupon code to cart.
   * Backend uppercases and strips whitespace — we do the same
   * before sending so input field reflects normalized value.
   * @param {string} code
   */
  const handleApplyCoupon = (code) => {
    applyCouponMutation.mutate({ code: code.trim().toUpperCase() });
  };

  /**
   * Remove currently applied coupon from cart.
   * Guard against calling when no coupon applied lives in CartSummary UI.
   */
  const handleRemoveCoupon = () => {
    removeCouponMutation.mutate();
  };

  return {
    // ── Cart data ────────────────────────────────────────────────────────────
    items,
    totalItems,
    subtotal, // before coupon — used for selected item subtotal calc
    discountAmount, // coupon discount PKR
    totalPrice, // subtotal - discount (no shipping)
    isEmpty,
    couponId, // null or FK id — used to show/hide discount row
    couponCodeInput, // preserved code — pre-populates coupon input on load

    // ── Loading / error states ───────────────────────────────────────────────
    isLoading,
    isError,
    isMutating,
    isCouponPending,
    errorMessage: normalized?.message ?? null,
    mutationErrorMessage: normalizedMutationError?.message ?? null,
    couponError: normalizedCouponError?.message ?? null,
    couponErrorCode: normalizedCouponError?.errors?.non_fields?.code ?? null,

    // ── Handlers ─────────────────────────────────────────────────────────────
    handleIncrease,
    handleDecrease,
    handleRemove,
    handleClearCart,
    handleAddToCart,
    handleApplyCoupon,
    handleRemoveCoupon,
  };
}
// // src/hooks/cart/useCart.js
// import { useCartQuery } from "../api/useCartQueries";
// import {
//   useAddToCart,
//   useUpdateCartItem,
//   useRemoveCartItem,
//   useClearCart,
// } from "../api/useCartMutations";
// import { normalizeError } from "@shared/api";

// /**
//  * useCart — Layer 3b
//  *
//  * Business logic hook for CartPage.
//  *
//  * Responsibilities:
//  *   - Provides cart data (items, totals) from backend
//  *   - Provides all cart action handlers
//  *   - Normalizes errors for UI display
//  *   - Derives display values from backend fields
//  *
//  * Why subtotal comes from backend not computed in frontend:
//  *   Backend uses Decimal precision for monetary values.
//  *   Frontend float arithmetic can produce rounding errors.
//  *   Backend is the source of truth for all financial calculations.
//  *
//  * Backend cart item shape:
//  *   {
//  *     id, product_name, product_slug, product_price,
//  *     product_image, is_in_stock, quantity, subtotal,
//  *     created_at, updated_at
//  *   }
//  *
//  * URL param → backend param mapping:
//  *   item.id          → itemId for PATCH/DELETE
//  *   item.quantity    → current quantity for display
//  *   item.subtotal    → backend-computed subtotal string
//  *   cart.subtotal → backend-computed total string
//  */
// export function useCart() {
//   // ── Query ──────────────────────────────────────────────────────────────────
//   const { data: cart, isLoading, isError, error } = useCartQuery();

//   // ── Mutations ──────────────────────────────────────────────────────────────
//   const addToCartMutation = useAddToCart();
//   const updateItemMutation = useUpdateCartItem();
//   const removeItemMutation = useRemoveCartItem();
//   const clearCartMutation = useClearCart();

//   // ── Derived cart data ──────────────────────────────────────────────────────
//   const items = cart?.items ?? [];
//   const totalItems = cart?.total_items ?? 0;
//   const totalPrice = cart?.subtotal ?? "0.00";
//   const isEmpty = cart?.is_empty ?? true;

//   // ── Error normalization ────────────────────────────────────────────────────
//   const normalized = isError ? normalizeError(error) : null;

//   // Mutation errors — shown as toast/banner
//   const mutationError =
//     addToCartMutation.error ||
//     updateItemMutation.error ||
//     removeItemMutation.error ||
//     clearCartMutation.error;

//   const normalizedMutationError = mutationError
//     ? normalizeError(mutationError)
//     : null;

//   // ── Any mutation pending — disable all buttons ─────────────────────────────
//   const isMutating =
//     addToCartMutation.isPending ||
//     updateItemMutation.isPending ||
//     removeItemMutation.isPending ||
//     clearCartMutation.isPending;

//   // ── Handlers ───────────────────────────────────────────────────────────────

//   /**
//    * Increase item quantity by 1.
//    * Backend validates against stock — will error if exceeds stock.
//    *
//    * @param {number} itemId   - CartItem.id
//    * @param {number} quantity - current quantity
//    */
//   const handleIncrease = (itemId, quantity) => {
//     updateItemMutation.mutate({ itemId, quantity: quantity + 1 });
//   };

//   /**
//    * Decrease item quantity by 1.
//    * Sending quantity=0 triggers server-side auto-delete.
//    * This gives consistent UX: user decrements to 0 → item disappears.
//    *
//    * @param {number} itemId   - CartItem.id
//    * @param {number} quantity - current quantity
//    */
//   const handleDecrease = (itemId, quantity) => {
//     updateItemMutation.mutate({ itemId, quantity: quantity - 1 });
//   };

//   /**
//    * Remove a single item from cart via DELETE endpoint.
//    *
//    * @param {number} itemId - CartItem.id
//    */
//   const handleRemove = (itemId) => {
//     removeItemMutation.mutate({ itemId });
//   };

//   /**
//    * Clear all items from the cart.
//    */
//   const handleClearCart = () => {
//     clearCartMutation.mutate();
//   };

//   /**
//    * Add a product to cart.
//    * Used by ProductCard and ProductDetail — not by CartPage directly.
//    *
//    * @param {number} productId
//    * @param {number} quantity
//    */
//   const handleAddToCart = (productId, quantity = 1) => {
//     addToCartMutation.mutate({ productId, quantity });
//   };

//   return {
//     // Cart data
//     items,
//     totalItems,
//     totalPrice,
//     isEmpty,

//     // Loading states
//     isLoading,
//     isError,
//     isMutating,
//     errorMessage: normalized?.message ?? null,
//     mutationErrorMessage: normalizedMutationError?.message ?? null,

//     // Handlers
//     handleIncrease,
//     handleDecrease,
//     handleRemove,
//     handleClearCart,
//     handleAddToCart,
//   };
// }
