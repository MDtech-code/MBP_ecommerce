// src/features/wishlist/model/useWishlist.js

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { normalizeError } from "@shared/api";
import { useAuthStore } from "@entities/user";
import { useWishlistQuery } from "../api/useWishlistQueries";
import {
  useAddToWishlist,
  useRemoveFromWishlist,
} from "../api/useWishlistMutations";

/**
 * Logic hook for all wishlist interactions.
 *
 * Used by:
 *   - WishlistPage — full paginated list + remove
 *   - ProductCardAction — heart button add/remove toggle
 *
 * Manages:
 *   - Paginated wishlist data
 *   - Add to wishlist (redirects to login if not authenticated)
 *   - Remove from wishlist
 *   - Per-product loading state (which product is mutating)
 *   - 409 conflict handling (already in wishlist)
 *
 * @param {{ page?: number }} params
 */
export function useWishlist({ page = 1 } = {}) {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

  // ── Query ─────────────────────────────────────────────────────────────────
  const wishlistQuery = useWishlistQuery(page);

  // ── Mutations ─────────────────────────────────────────────────────────────
  const addMutation = useAddToWishlist();
  const removeMutation = useRemoveFromWishlist();

  // ── Derived data ──────────────────────────────────────────────────────────
  const items = wishlistQuery.data?.data ?? [];
  const meta = wishlistQuery.data?.meta ?? null;

  // Set of product IDs currently in wishlist — O(1) lookup for heart toggle
  const wishlistedIds = new Set(items.map((item) => item.product_id));

  // ── Per-product mutating state ────────────────────────────────────────────
  // Tracks which productId is currently being added or removed
  // so individual heart buttons can show their own loading state
  const [mutatingId, setMutatingId] = useState(null);

  // ── Error state ───────────────────────────────────────────────────────────
  const [actionError, setActionError] = useState(null);

  // ── Handlers ──────────────────────────────────────────────────────────────

  /**
   * Toggle wishlist state for a product.
   * If not authenticated — redirect to login.
   * If already wishlisted — remove it.
   * If not wishlisted — add it.
   *
   * @param {number} productId
   */
  const handleToggleWishlist = (productId) => {
    if (!isAuthenticated) {
      navigate("/login");
      return;
    }

    setActionError(null);
    setMutatingId(productId);

    if (wishlistedIds.has(productId)) {
      // Already wishlisted — remove
      removeMutation.mutate(productId, {
        onSuccess: () => setMutatingId(null),
        onError: (error) => {
          setMutatingId(null);
          const normalized = normalizeError(error);
          setActionError(normalized.message);
        },
      });
    } else {
      // Not wishlisted — add
      addMutation.mutate(productId, {
        onSuccess: () => setMutatingId(null),
        onError: (error) => {
          setMutatingId(null);
          const normalized = normalizeError(error);
          // 409 = already in wishlist — treat as success silently
          // This handles race conditions (double click)
          if (normalized.isConflict) return;
          setActionError(normalized.message);
        },
      });
    }
  };

  /**
   * Remove item directly — used by WishlistPage remove button.
   * Separate from toggle so WishlistPage does not need wishlistedIds check.
   *
   * @param {number} productId
   */
  const handleRemove = (productId) => {
    setMutatingId(productId);
    removeMutation.mutate(productId, {
      onSuccess: () => setMutatingId(null),
      onError: (error) => {
        setMutatingId(null);
        const normalized = normalizeError(error);
        setActionError(normalized.message);
      },
    });
  };

  // ── Return surface ────────────────────────────────────────────────────────
  return {
    // List data
    items,
    meta,
    isLoading: wishlistQuery.isLoading,
    isError: wishlistQuery.isError,

    // Wishlist state helpers
    wishlistedIds,
    isWishlisted: (productId) => wishlistedIds.has(productId),
    isMutating: (productId) => mutatingId === productId,

    // Handlers
    handleToggleWishlist,
    handleRemove,

    // Error
    actionError,
  };
}
