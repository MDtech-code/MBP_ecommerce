// src/features/orders/model/useOrderList.js

import { useSearchParams } from "react-router-dom";
import { normalizeError } from "@shared/api";
import { useOrderListQuery } from "../api/useOrderQueries";

/**
 * useOrderList — logic hook for OrderListPage.
 *
 * Responsibilities:
 *   - Reads page from URL search params (?page=N)
 *   - Fetches paginated order list
 *   - Exposes setPage handler that updates URL + scrolls to top
 *   - Normalizes errors for display
 *
 * Why URL drives page:
 *   Back navigation restores correct page.
 *   User can share/bookmark page 3 of their orders.
 *   Consistent with ProductListingPage pattern.
 */
export function useOrderList() {
  const [searchParams, setSearchParams] = useSearchParams();
  const page = parseInt(searchParams.get("page") ?? "1", 10);

  const { data, isLoading, isFetching, isError, error } =
    useOrderListQuery(page);

  const setPage = (newPage) => {
    setSearchParams({ page: String(newPage) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const normalized = isError ? normalizeError(error) : null;

  return {
    orders: data?.orders ?? [],
    meta: data?.meta ?? {},
    isLoading,
    isFetching,
    isError,
    errorMessage: normalized?.message ?? null,
    page,
    setPage,
  };
}
