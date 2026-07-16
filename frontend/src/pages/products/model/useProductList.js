// src/hooks/products/useProductList.js
import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";
import { useProducts } from "../../../entities/product/api/useProductQueries";
import { normalizeError } from "../../../shared/api/transformers";

/**
 * useProductList — Layer 3b
 *
 * Business logic hook for the ProductListing page.
 *
 * Responsibilities:
 *   - Reads filters from URL search params (shareable/bookmarkable URLs)
 *   - Provides filter update handlers
 *   - Provides pagination handlers
 *   - Provides sort handler
 *   - Exposes normalized error when query fails
 *   - Returns clean destructured values to page (dumb UI)
 *
 * Why URL search params not useState:
 *   User can share the URL and get the same filtered view.
 *   Browser back button restores previous filter state.
 *   Page refresh keeps filters intact.
 *
 * URL param → backend param mapping:
 *   ?category=brake-system → ?category=brake-system (slug)
 *   ?brand=honda           → ?brand=honda (slug)
 *   ?bike=1                → ?bike_model=1 (id)
 *   ?min=500               → ?min_price=500
 *   ?max=5000              → ?max_price=5000
 *   ?q=brake               → ?q=brake
 *   ?featured=true         → ?featured=true
 *   ?sort=newest           → ?sort=newest
 *   ?page=2                → ?page=2
 */
export function useProductList() {
  const [searchParams, setSearchParams] = useSearchParams();

  // ── Read filters from URL ──────────────────────────────────────────────────
  const filters = {
    category: searchParams.get("category") || undefined,
    brand: searchParams.get("brand") || undefined,
    bike_model: searchParams.get("bike") || undefined,
    min_price: searchParams.get("min") || undefined,
    max_price: searchParams.get("max") || undefined,
    q: searchParams.get("q") || undefined,
    featured: searchParams.get("featured") || undefined,
    sort: searchParams.get("sort") || "newest",
    page: Number(searchParams.get("page")) || 1,
    page_size: 12,
  };

  // ── Query ──────────────────────────────────────────────────────────────────
  const { data, isLoading, isError, error, isFetching } = useProducts(filters);

  const products = data?.products ?? [];
  const meta = data?.meta ?? {};

  // ── Error normalization ────────────────────────────────────────────────────
  const normalized = isError ? normalizeError(error) : null;

  // ── Filter updaters ────────────────────────────────────────────────────────

  /**
   * Update a single filter param and reset to page 1.
   * Preserves all other params.
   */
  const updateFilter = useCallback(
    (key, value) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        if (value) {
          next.set(key, value);
        } else {
          next.delete(key);
        }
        // Reset to page 1 whenever filter changes
        next.delete("page");
        return next;
      });
    },
    [setSearchParams],
  );

  const setCategory = useCallback(
    (slug) => updateFilter("category", slug),
    [updateFilter],
  );
  const setBrand = useCallback(
    (slug) => updateFilter("brand", slug),
    [updateFilter],
  );
  const setBikeModel = useCallback(
    (id) => updateFilter("bike", id),
    [updateFilter],
  );
  const setMinPrice = useCallback(
    (val) => updateFilter("min", val),
    [updateFilter],
  );
  const setMaxPrice = useCallback(
    (val) => updateFilter("max", val),
    [updateFilter],
  );
  const setSearch = useCallback(
    (val) => updateFilter("q", val),
    [updateFilter],
  );
  const setFeatured = useCallback(
    (val) => updateFilter("featured", val),
    [updateFilter],
  );

  const setSort = useCallback(
    (sort) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("sort", sort);
        next.delete("page");
        return next;
      });
    },
    [setSearchParams],
  );

  const setPage = useCallback(
    (page) => {
      setSearchParams((prev) => {
        const next = new URLSearchParams(prev);
        next.set("page", page);
        return next;
      });
    },
    [setSearchParams],
  );

  /**
   * Clear ALL filters — reset to default state.
   */
  const clearFilters = useCallback(() => {
    setSearchParams({});
  }, [setSearchParams]);

  // ── Active filter values (for sidebar checked state) ──────────────────────
  const activeFilters = {
    category: searchParams.get("category") || null,
    brand: searchParams.get("brand") || null,
    bikeModel: searchParams.get("bike") || null,
    minPrice: searchParams.get("min") || null,
    maxPrice: searchParams.get("max") || null,
    search: searchParams.get("q") || null,
    featured: searchParams.get("featured") || null,
    sort: searchParams.get("sort") || "newest",
    page: Number(searchParams.get("page")) || 1,
  };

  return {
    // Data
    products,
    meta,

    // Loading states
    isLoading,
    isFetching, // true during background refetch (page change etc.)
    isError,
    errorMessage: normalized?.message ?? null,

    // Active filter state (for UI checked/selected state)
    activeFilters,

    // Filter setters
    setCategory,
    setBrand,
    setBikeModel,
    setMinPrice,
    setMaxPrice,
    setSearch,
    setFeatured,
    setSort,
    setPage,
    clearFilters,
  };
}
