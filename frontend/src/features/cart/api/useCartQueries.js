// src/hooks/cart/useCartQueries.js
import { useQuery } from "@tanstack/react-query";
import { cartService } from "@shared/api";

/**
 * Cart queries — Layer 3a
 *
 * Query key: ["cart"]
 *
 * Why single key:
 *   There is only one cart per user — no need for parameterized keys.
 *   All mutations invalidate ["cart"] to trigger a refetch.
 *
 * Why staleTime is short (30 seconds):
 *   Cart is user-specific and changes frequently.
 *   We want near-real-time accuracy without hammering the server.
 *
 * Why enabled: !!user check is NOT here:
 *   Auth check lives in the page/hook — query layer stays pure.
 *   CartPage is only mounted when user is authenticated.
 */

export const CART_QUERY_KEY = ["cart"];

export function useCartQuery() {
  return useQuery({
    queryKey: CART_QUERY_KEY,
    queryFn: () => cartService.getCart(),
    staleTime: 1000 * 30, // 30 seconds
    select: (result) => result.data ?? null,
  });
}
