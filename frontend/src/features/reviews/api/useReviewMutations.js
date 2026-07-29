// src/features/reviews/api/useReviewMutations.js

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { reviewService } from "@shared/api";
import { reviewKeys } from "./useReviewQueries";

// ─────────────────────────────────────────────────────────────────────────────
// SUBMIT REVIEW
// POST /api/reviews/
// On success:
//   - Invalidate eligibleItems for this product → prompt disappears
//   - Invalidate productReviews for this slug   → list refreshes
//   - Invalidate pendingReviews                 → dashboard count updates
//   - Invalidate myReviews                      → dashboard history updates
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mutation for submitting a verified purchase review.
 *
 * Caller must pass slug and productId so we can invalidate
 * the correct product-scoped query keys on success.
 *
 * Usage:
 *   const { mutate, isPending } = useSubmitReview({ slug, productId })
 *   mutate({ order_item_id, rating, title, body })
 *
 * @param {{ slug: string, productId: number }} context
 */
export function useSubmitReview({ slug, productId } = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (payload) => reviewService.submitReview(payload),

    onSuccess: () => {
      // Remove eligible item prompt for this product —
      // user just reviewed it so they're no longer eligible
      queryClient.invalidateQueries({
        queryKey: reviewKeys.eligibleItems(productId),
      });

      // Refresh public review list — though new review won't appear
      // until approved, invalidating keeps data fresh for future visits
      queryClient.invalidateQueries({
        queryKey: reviewKeys.productReviews(slug, 1, null),
      });

      // Dashboard — pending count drops by one
      queryClient.invalidateQueries({
        queryKey: reviewKeys.pendingReviews(),
      });

      // Dashboard — new review appears in history (pending approval)
      queryClient.invalidateQueries({
        queryKey: reviewKeys.myReviews(),
      });
    },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// VOTE ON REVIEW
// POST /api/reviews/:reviewId/vote/
// On success:
//   - Invalidate productReviews for this slug →
//     helpful_count / not_helpful_count update
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mutation for casting or updating a helpful/not_helpful vote.
 *
 * Caller must pass slug so we can invalidate the correct
 * product review list on success.
 *
 * Vote values are exactly "helpful" or "not_helpful" —
 * from ReviewVote.Vote TextChoices on the backend.
 *
 * Usage:
 *   const { mutate } = useVoteOnReview({ slug })
 *   mutate({ reviewId, vote: "helpful" })
 *
 * @param {{ slug: string }} context
 */
export function useVoteOnReview({ slug } = {}) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ reviewId, vote }) =>
      reviewService.voteOnReview(reviewId, { vote }),

    onSuccess: () => {
      // Invalidate all pages + all rating filters for this product's
      // reviews — helpful counts changed, any cached page is stale
      queryClient.invalidateQueries({
        queryKey: ["reviews", "product", slug],
      });
    },
  });
}
