// src/hooks/cart/useCartMutations.js
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cartService } from "../../../shared/api/services/cartService";
import { CART_QUERY_KEY } from "./useCartQueries";

/**
 * Cart mutations — Layer 3a
 *
 * All mutations:
 *   1. Call cartService method
 *   2. On success → update cart cache with server response
 *      (backend always returns full updated cart)
 *   3. Never catch errors — let them bubble to useCart hook
 *
 * Why setQueryData not invalidateQueries:
 *   Backend returns the full updated cart on every mutation.
 *   We use that response directly to update the cache instead of
 *   triggering a second GET request — saves one round trip.
 *
 * Why onSuccess sets cache from response.data:
 *   extractResponse() returns { data, message, meta }
 *   result.data is the CartSerializer output — exactly what
 *   useCartQuery.select() expects as input.
 *
 * Why onError does nothing here:
 *   Error handling lives in useCart (Layer 3b) via normalizeError.
 *   Mutation hooks stay pure — no UI logic here.
 */

export function useAddToCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ productId, quantity }) =>
      cartService.addToCart(productId, quantity),
    onSuccess: (result) => {
      // Server returns full updated cart — set directly, no refetch needed
      queryClient.setQueryData(CART_QUERY_KEY, result);
    },
  });
}

export function useUpdateCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId, quantity }) =>
      cartService.updateCartItem(itemId, quantity),
    onSuccess: (result) => {
      queryClient.setQueryData(CART_QUERY_KEY, result);
    },
  });
}

export function useRemoveCartItem() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ itemId }) => cartService.removeCartItem(itemId),
    onSuccess: (result) => {
      queryClient.setQueryData(CART_QUERY_KEY, result);
    },
  });
}

export function useClearCart() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => cartService.clearCart(),
    onSuccess: (result) => {
      queryClient.setQueryData(CART_QUERY_KEY, result);
    },
  });
}
