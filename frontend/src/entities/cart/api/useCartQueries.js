// src/hooks/cart/useCartQueries.js
import { useQuery } from "@tanstack/react-query";
import { cartService, extractData } from "@shared/api";

export const CART_QUERY_KEY = ["cart"];

export function useCartQuery() {
  return useQuery({
    queryKey: CART_QUERY_KEY,
    queryFn: () => cartService.getCart(),
    staleTime: 1000 * 30,
    select: (result) => extractData(result,null),
    // select: (result) => result.data ?? null,
  });
}
