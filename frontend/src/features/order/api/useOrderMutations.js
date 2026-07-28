// src/features/orders/api/useOrderMutations.js

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { orderService } from "@shared/api";
import { ORDER_DETAIL_KEY } from "./useOrderQueries";

/**
 * useCancelOrder — cancels a PENDING order.
 *
 * POST /api/orders/<order_number>/cancel/
 *
 * On success:
 *   1. Update detail cache directly with fresh server response
 *      (status now CANCELLED, is_cancellable now false)
 *   2. Invalidate all order list pages — status badge must update
 *      on list page too
 *
 * On error:
 *   DomainError 409 (order_not_cancellable) bubbles to useOrderDetail
 *   for normalized error display.
 *
 * @param {string} orderNumber
 */
export function useCancelOrder(orderNumber) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => orderService.cancelOrder(orderNumber),

    onSuccess: (result) => {
      // Update detail cache — avoids extra GET request
      // result.data is OrderDetailSerializer output
      queryClient.setQueryData(ORDER_DETAIL_KEY(orderNumber), result);

      // Invalidate list — all pages, status badge must update
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    },
  });
}
