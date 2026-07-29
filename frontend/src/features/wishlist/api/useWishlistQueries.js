// src/features/wishlist/api/useWishlistQueries.js

import { useQuery } from "@tanstack/react-query";
import { wishlistService } from "@shared/api";
import { useAuthStore } from "@entities/user";

// ─── Query Key Factory ────────────────────────────────────────────────────────
export const wishlistKeys = {
  all: ["wishlist"],
  list: (page) => ["wishlist", "list", { page }],
};

// ─────────────────────────────────────────────────────────────────────────────
// WISHLIST LIST
// GET /api/wishlist/?page=
// Auth required — only enabled when user is authenticated.
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Fetches paginated wishlist items for the authenticated user.
 *
 * @param {number} page - current page
 */
export function useWishlistQuery(page = 1) {
  const user = useAuthStore((state) => state.user);

  return useQuery({
    queryKey: wishlistKeys.list(page),
    queryFn: () => wishlistService.getWishlist({ page }),
    enabled: !!user,
    staleTime: 1000 * 60 * 3,
  });
}
