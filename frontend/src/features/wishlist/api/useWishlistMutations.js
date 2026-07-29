// src/features/wishlist/api/useWishlistMutations.js

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { wishlistService } from "@shared/api";
import { wishlistKeys } from "./useWishlistQueries";

// ─────────────────────────────────────────────────────────────────────────────
// ADD TO WISHLIST
// POST /api/wishlist/add/
// On success: invalidate all wishlist list queries
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mutation for adding a product to the wishlist.
 * On success invalidates all paginated wishlist list queries.
 */
export function useAddToWishlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (productId) => wishlistService.addToWishlist(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: wishlistKeys.all,
      });
    },
  });
}

// ─────────────────────────────────────────────────────────────────────────────
// REMOVE FROM WISHLIST
// DELETE /api/wishlist/<product_id>/
// On success: invalidate all wishlist list queries
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Mutation for removing a product from the wishlist.
 * On success invalidates all paginated wishlist list queries.
 */
export function useRemoveFromWishlist() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (productId) => wishlistService.removeFromWishlist(productId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: wishlistKeys.all,
      });
    },
  });
}
