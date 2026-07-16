// src/services/cartService.js
import { api } from "../client";
import { extractResponse } from "../transformers";

/**
 * Cart service — Layer 2
 *
 * Rules:
 *   - Only makes API calls
 *   - Always passes response through extractResponse()
 *   - Never catches errors — let them bubble to hooks
 *   - Never imports from hooks or stores
 *
 * Backend endpoints:
 *   GET    /api/cart/              → full cart with items + totals
 *   POST   /api/cart/items/        → add product (upsert)
 *   PATCH  /api/cart/items/<id>/   → update quantity (0 = delete)
 *   DELETE /api/cart/items/<id>/   → remove item
 *   DELETE /api/cart/clear/        → clear all items
 */

export const cartService = {
  /**
   * GET /api/cart/
   * Returns full cart with items, total_items, total_price, is_empty
   */
  getCart: async () => {
    const response = await api.get("/api/cart/");
    return extractResponse(response);
  },

  /**
   * POST /api/cart/items/
   * Add product to cart or increase quantity if already present.
   *
   * @param {number} productId
   * @param {number} quantity
   */
  addToCart: async (productId, quantity = 1) => {
    const response = await api.post("/api/cart/items/", {
      product_id: productId,
      quantity,
    });
    return extractResponse(response);
  },

  /**
   * PATCH /api/cart/items/<itemId>/
   * Update item quantity. Sending quantity=0 auto-deletes the item.
   *
   * @param {number} itemId   - CartItem id (not product id)
   * @param {number} quantity - new quantity (0 triggers server-side delete)
   */
  updateCartItem: async (itemId, quantity) => {
    const response = await api.patch(`/api/cart/items/${itemId}/`, {
      quantity,
    });
    return extractResponse(response);
  },

  /**
   * DELETE /api/cart/items/<itemId>/
   * Remove a single item from cart.
   *
   * @param {number} itemId
   */
  removeCartItem: async (itemId) => {
    const response = await api.delete(`/api/cart/items/${itemId}/`);
    return extractResponse(response);
  },

  /**
   * DELETE /api/cart/clear/
   * Remove all items from cart.
   */
  clearCart: async () => {
    const response = await api.delete("/api/cart/clear/");
    return extractResponse(response);
  },
};
