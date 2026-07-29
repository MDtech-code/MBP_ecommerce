// src/shared/api/services/wishlistService.js

import { api } from "../client";
import { extractResponse } from "../transformers";

export const wishlistService = {
  /**
   * GET /api/wishlist/?page=
   * Auth required — IsAuthenticated.
   * Returns paginated wishlist items with product summary.
   *
   * @param {{ page?: number }} params
   */
  getWishlist: async ({ page = 1 } = {}) => {
    const response = await api.get("/api/wishlist/", {
      params: { page },
    });
    return extractResponse(response);
  },

  /**
   * POST /api/wishlist/add/
   * Auth required — IsAuthenticated.
   * Adds a product to the wishlist.
   * Returns 409 if already in wishlist.
   *
   * @param {number} productId
   */
  addToWishlist: async (productId) => {
    const response = await api.post("/api/wishlist/add/", {
      product_id: productId,
    });
    return extractResponse(response);
  },

  /**
   * DELETE /api/wishlist/<product_id>/
   * Auth required — IsAuthenticated.
   * Removes a product from the wishlist.
   *
   * @param {number} productId
   */
  removeFromWishlist: async (productId) => {
    const response = await api.delete(`/api/wishlist/${productId}/`);
    return extractResponse(response);
  },
};
