// src/shared/api/services/reviewService.js

import { api } from "../client";
import { extractResponse } from "../transformers";

export const reviewService = {
  /**
   * GET /api/products/:slug/reviews/?page=&rating=
   * Public — no auth required.
   * Returns paginated approved reviews for a product.
   *
   * @param {string} slug - product slug from URL
   * @param {{ page?: number, rating?: number | null }} params
   */
  getProductReviews: async (slug, { page = 1, rating = null } = {}) => {
    const params = { page };
    if (rating) params.rating = rating;
    const response = await api.get(`/api/products/${slug}/reviews/`, {
      params,
    });
    return extractResponse(response);
  },

  /**
   * GET /api/reviews/eligible/?product_id=:id
   * Auth required — IsAuthenticated.
   * Returns OrderItems the user can review for a specific product.
   * Returns empty list if no eligible items — not a 404.
   *
   * @param {number} productId
   */
  getEligibleItems: async (productId) => {
    const response = await api.get("/api/reviews/eligible/", {
      params: { product_id: productId },
    });
    return extractResponse(response);
  },

  /**
   * GET /api/reviews/pending/
   * Auth required — IsAuthenticated.
   * Returns ALL OrderItems user can review across all delivered orders.
   * No product filter — used for dashboard Pending Reviews section.
   */
  getPendingReviews: async () => {
    const response = await api.get("/api/reviews/pending/");
    return extractResponse(response);
  },

  /**
   * GET /api/reviews/my-reviews/
   * Auth required — IsAuthenticated.
   * Returns all reviews submitted by the user.
   * Includes both approved and pending moderation reviews.
   * Used for dashboard Review History section.
   */
  getMyReviews: async () => {
    const response = await api.get("/api/reviews/my-reviews/");
    return extractResponse(response);
  },

  /**
   * POST /api/reviews/
   * Auth required — IsAuthenticated + IsVerified.
   * Submits a verified purchase review.
   * New reviews start with is_approved=False — pending moderation.
   *
   * @param {{ order_item_id: number, rating: number, title?: string, body?: string }} payload
   */
  submitReview: async (payload) => {
    const response = await api.post("/api/reviews/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/reviews/:reviewId/vote/
   * Auth required — IsAuthenticated.
   * Casts or updates a helpful/not_helpful vote on a review.
   * Changing vote updates existing row — no duplicates.
   *
   * @param {number} reviewId
   * @param {{ vote: "helpful" | "not_helpful" }} payload
   */
  voteOnReview: async (reviewId, payload) => {
    const response = await api.post(`/api/reviews/${reviewId}/vote/`, payload);
    return extractResponse(response);
  },
};
