// src/features/reviews/api/useReviewQueries.js

import { useQuery } from "@tanstack/react-query";
import { reviewService } from "@shared/api";
import { useAuthStore } from "@entities/user";

// ─── Query Key Factory ────────────────────────────────────────────────────────
// Centralised here — mutations import these to invalidate correctly.
// Never hardcode query key strings at call sites.

export const reviewKeys = {
  // All reviews queries
  all: ["reviews"],

  // Public product reviews — scoped by slug + page + rating filter
  productReviews: (slug, page, rating) => [
    "reviews",
    "product",
    slug,
    { page, rating },
  ],

  // Eligible items for a specific product (per-product, auth)
  eligibleItems: (productId) => ["reviews", "eligible", productId],

  // All pending reviews across all orders (dashboard, auth)
  pendingReviews: () => ["reviews", "pending"],

  // User's submitted review history (dashboard, auth)
  myReviews: () => ["reviews", "my-reviews"],
};

// ─────────────────────────────────────────────────────────────────────────────
// PUBLIC PRODUCT REVIEWS
// GET /api/products/:slug/reviews/?page=&rating=
// No auth required — enabled always when slug is present.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetches paginated approved reviews for a product.
 *
 * @param {string} slug        - product slug
 * @param {number} page        - current page (from URL state)
 * @param {number|null} rating - rating filter 1-5 or null for all
 */
export function useProductReviewsQuery(slug, page = 1, rating = null) {
  return useQuery({
    queryKey: reviewKeys.productReviews(slug, page, rating),
    queryFn: () => reviewService.getProductReviews(slug, { page, rating }),
    enabled: !!slug,
    staleTime: 1000 * 60 * 5, // 5 min — reviews don't change often
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// ELIGIBLE ITEMS — per product
// GET /api/reviews/eligible/?product_id=:id
// Auth required — only enabled when user is authenticated AND productId present.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetches OrderItems the authenticated user can review for a specific product.
 * Returns empty array if no eligible items — never 404.
 *
 * @param {number|null} productId - product pk from product detail data
 */
export function useEligibleItemsQuery(productId) {
  const user = useAuthStore((state) => state.user);

  return useQuery({
    queryKey: reviewKeys.eligibleItems(productId),
    queryFn: () => reviewService.getEligibleItems(productId),
    // Both conditions required:
    // !!user       — no point calling auth endpoint without a user
    // !!productId  — endpoint requires product_id param
    enabled: !!user && !!productId,
    staleTime: 1000 * 60 * 5,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// PENDING REVIEWS — dashboard, all products
// GET /api/reviews/pending/
// Auth required — only enabled when user is authenticated.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetches ALL OrderItems the user can review across all delivered orders.
 * No product filter — used for dashboard Pending Reviews section.
 */
export function usePendingReviewsQuery() {
  const user = useAuthStore((state) => state.user);

  return useQuery({
    queryKey: reviewKeys.pendingReviews(),
    queryFn: reviewService.getPendingReviews,
    enabled: !!user,
    staleTime: 1000 * 60 * 5,
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// MY REVIEWS — dashboard, user's submitted history
// GET /api/reviews/my-reviews/
// Auth required — only enabled when user is authenticated.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetches all reviews submitted by the authenticated user.
 * Includes both approved and pending moderation reviews.
 * Used for dashboard Review History section.
 */
export function useMyReviewsQuery() {
  const user = useAuthStore((state) => state.user);

  return useQuery({
    queryKey: reviewKeys.myReviews(),
    queryFn: reviewService.getMyReviews,
    enabled: !!user,
    staleTime: 1000 * 60 * 5,
  });
}
