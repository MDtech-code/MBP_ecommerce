// src/features/orders/api/useOrderQueries.js

import { useQuery } from "@tanstack/react-query";
import { orderService } from "@shared/api";

/**
 * Order queries — TanStack Query wrappers for order endpoints.
 *
 * Query key conventions:
 *   ["orders", page]          → paginated order list
 *   ["order", orderNumber]    → single order detail
 *
 * Why page in list key:
 *   Each page is a separate cache entry.
 *   Page 1 and page 2 cached independently — back navigation
 *   restores previous page instantly without refetch.
 *
 * staleTime choices:
 *   List: 60s — order status changes matter but not sub-second
 *   Detail: 30s — user watching their order status needs fresher data
 */

export const ORDER_LIST_KEY = (page) => ["orders", page];
export const ORDER_DETAIL_KEY = (orderNumber) => ["order", orderNumber];

export function useOrderListQuery(page = 1) {
  return useQuery({
    queryKey: ORDER_LIST_KEY(page),
    queryFn: () => orderService.getOrders({ page }),
    staleTime: 1000 * 60, // 1 min
    placeholderData: (prev) => prev, // keep previous page visible during load
    select: (result) => ({
      orders: result.data ?? [],
      meta: result.meta ?? {},
    }),
  });
}

export function useOrderDetailQuery(orderNumber) {
  return useQuery({
    queryKey: ORDER_DETAIL_KEY(orderNumber),
    queryFn: () => orderService.getOrderDetail(orderNumber),
    staleTime: 1000 * 30, // 30s — status changes matter
    enabled: !!orderNumber,
    select: (result) => result.data ?? null,
  });
}
