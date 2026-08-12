// src/hooks/products/useProductQueries.js
import { useQuery } from "@tanstack/react-query";
import { productService,extractData,extractPagination } from "@shared/api";


/**
 * Product queries — Layer 3a
 *
 * Pure TanStack Query wrappers.
 * No business logic here — just query keys, fetchers, options.
 * Business logic lives in useProductList.js / useProductDetail.js
 *
 * Query key conventions:
 *   ["categories", "tree"]
 *   ["categories", "flat"]
 *   ["brands"]
 *   ["bike-models", brandId]
 *   ["products", filters]        ← filters object is part of key
 *   ["product", slug]
 *
 * Why filters object in key:
 *   TanStack Query deep-compares keys.
 *   { page: 1, category: "brakes" } and { page: 2, category: "brakes" }
 *   are different keys → different cache entries automatically.
 */

// ─── Categories ───────────────────────────────────────────────────────────────

export function useCategoriesTree() {
  return useQuery({
    queryKey: ["categories", "tree"],
    queryFn: () => productService.getCategoriesTree(),
    // Why long staleTime:
    //   Categories change rarely — admin adds/removes maybe monthly.
    //   Backend signals invalidate Redis cache on change.
    //   Frontend can safely cache for 10 minutes.
    staleTime: 1000 * 60 * 10, // 10 minutes
    select: (result) => extractData(result,[]),
  });
}

export function useCategoriesFlat() {
  return useQuery({
    queryKey: ["categories", "flat"],
    queryFn: () => productService.getCategoriesFlat(),
    staleTime: 1000 * 60 * 10,
    select: (result) => extractData(result,[]),
  });
}

// ─── Brands ───────────────────────────────────────────────────────────────────

export function useBrands() {
  return useQuery({
    queryKey: ["brands"],
    queryFn: () => productService.getBrands(),
    staleTime: 1000 * 60 * 10,
    select: (result) => extractData(result,[]),
  });
}

// ─── Bike Models ──────────────────────────────────────────────────────────────

/**
 * @param {number|null} brandId - pass null to fetch all models
 */
export function useBikeModels(brandId = null) {
  return useQuery({
    queryKey: ["bike-models", brandId],
    queryFn: () => productService.getBikeModels(brandId),
    staleTime: 1000 * 60 * 5,
    select: (result) => extractData(result,[]),
  });
}

// ─── Product List ─────────────────────────────────────────────────────────────

/**
 * @param {Object} filters - same shape as productService.getProducts params
 */
export function useProducts(filters = {}) {
  return useQuery({
    queryKey: ["products", filters],
    queryFn: () => productService.getProducts(filters),
    // Why shorter staleTime:
    //   Products change more often — price, stock, new arrivals.
    //   2 minutes is a safe balance between freshness and performance.
    staleTime: 1000 * 60 * 2,
    // Why keepPreviousData:
    //   When user changes page/filter, show previous page data
    //   while new page loads — prevents layout flash.
    placeholderData: (prev) => prev,
    select: (result) => ({
      products: extractData(result,[]),
      meta: extractPagination(result),
    }),
  });
}

// ─── Product Detail ───────────────────────────────────────────────────────────

/**
 * @param {string} slug
 */
export function useProductDetail(slug) {
  return useQuery({
    queryKey: ["product", slug],
    queryFn: () => productService.getProductBySlug(slug),
    staleTime: 1000 * 60 * 5,
    // Why enabled: !!slug:
    //   Don't fire query if slug is undefined (page still mounting).
    enabled: !!slug,
    select: (result) => extractData(result,null),
  });
}
