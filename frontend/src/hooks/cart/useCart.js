// src/hooks/cart/useCart.js
import { useCartQuery } from "./useCartQueries";
import {
  useAddToCart,
  useUpdateCartItem,
  useRemoveCartItem,
  useClearCart,
} from "./useCartMutations";
import { normalizeError } from "../../api/transformers";

/**
 * useCart — Layer 3b
 *
 * Business logic hook for CartPage.
 *
 * Responsibilities:
 *   - Provides cart data (items, totals) from backend
 *   - Provides all cart action handlers
 *   - Normalizes errors for UI display
 *   - Derives display values from backend fields
 *
 * Why subtotal comes from backend not computed in frontend:
 *   Backend uses Decimal precision for monetary values.
 *   Frontend float arithmetic can produce rounding errors.
 *   Backend is the source of truth for all financial calculations.
 *
 * Backend cart item shape:
 *   {
 *     id, product_name, product_slug, product_price,
 *     product_image, is_in_stock, quantity, subtotal,
 *     created_at, updated_at
 *   }
 *
 * URL param → backend param mapping:
 *   item.id          → itemId for PATCH/DELETE
 *   item.quantity    → current quantity for display
 *   item.subtotal    → backend-computed subtotal string
 *   cart.subtotal → backend-computed total string
 */
export function useCart() {
  // ── Query ──────────────────────────────────────────────────────────────────
  const { data: cart, isLoading, isError, error } = useCartQuery();

  // ── Mutations ──────────────────────────────────────────────────────────────
  const addToCartMutation = useAddToCart();
  const updateItemMutation = useUpdateCartItem();
  const removeItemMutation = useRemoveCartItem();
  const clearCartMutation = useClearCart();

  // ── Derived cart data ──────────────────────────────────────────────────────
  const items = cart?.items ?? [];
  const totalItems = cart?.total_items ?? 0;
  const totalPrice = cart?.subtotal ?? "0.00";
  const isEmpty = cart?.is_empty ?? true;

  // ── Error normalization ────────────────────────────────────────────────────
  const normalized = isError ? normalizeError(error) : null;

  // Mutation errors — shown as toast/banner
  const mutationError =
    addToCartMutation.error ||
    updateItemMutation.error ||
    removeItemMutation.error ||
    clearCartMutation.error;

  const normalizedMutationError = mutationError
    ? normalizeError(mutationError)
    : null;

  // ── Any mutation pending — disable all buttons ─────────────────────────────
  const isMutating =
    addToCartMutation.isPending ||
    updateItemMutation.isPending ||
    removeItemMutation.isPending ||
    clearCartMutation.isPending;

  // ── Handlers ───────────────────────────────────────────────────────────────

  /**
   * Increase item quantity by 1.
   * Backend validates against stock — will error if exceeds stock.
   *
   * @param {number} itemId   - CartItem.id
   * @param {number} quantity - current quantity
   */
  const handleIncrease = (itemId, quantity) => {
    updateItemMutation.mutate({ itemId, quantity: quantity + 1 });
  };

  /**
   * Decrease item quantity by 1.
   * Sending quantity=0 triggers server-side auto-delete.
   * This gives consistent UX: user decrements to 0 → item disappears.
   *
   * @param {number} itemId   - CartItem.id
   * @param {number} quantity - current quantity
   */
  const handleDecrease = (itemId, quantity) => {
    updateItemMutation.mutate({ itemId, quantity: quantity - 1 });
  };

  /**
   * Remove a single item from cart via DELETE endpoint.
   *
   * @param {number} itemId - CartItem.id
   */
  const handleRemove = (itemId) => {
    removeItemMutation.mutate({ itemId });
  };

  /**
   * Clear all items from the cart.
   */
  const handleClearCart = () => {
    clearCartMutation.mutate();
  };

  /**
   * Add a product to cart.
   * Used by ProductCard and ProductDetail — not by CartPage directly.
   *
   * @param {number} productId
   * @param {number} quantity
   */
  const handleAddToCart = (productId, quantity = 1) => {
    addToCartMutation.mutate({ productId, quantity });
  };

  return {
    // Cart data
    items,
    totalItems,
    totalPrice,
    isEmpty,

    // Loading states
    isLoading,
    isError,
    isMutating,
    errorMessage: normalized?.message ?? null,
    mutationErrorMessage: normalizedMutationError?.message ?? null,

    // Handlers
    handleIncrease,
    handleDecrease,
    handleRemove,
    handleClearCart,
    handleAddToCart,
  };
}
