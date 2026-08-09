// src/hooks/cart/useCartQueries.js
import { useQuery } from "@tanstack/react-query";
import { cartService } from "@shared/api";
import {useAuthStore} from "@entities/user"



export const CART_QUERY_KEY = ["cart"];

export function useCartQuery() {
  const isAuthenticated=useAuthStore((s)=>s.isAuthenticated);
  return useQuery({
    queryKey: CART_QUERY_KEY,
    queryFn: () => cartService.getCart(),
    staleTime: 1000 * 30,
    select: (result) => result.data ?? null,
    enabled: isAuthenticated,
  });
}
