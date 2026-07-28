// src/features/orders/model/useOrderDetail.js

import { useState } from "react";
import { normalizeError } from "@shared/api";
import { useOrderDetailQuery } from "../api/useOrderQueries";
import { useCancelOrder } from "../api/useOrderMutations";

/**
 * useOrderDetail — logic hook for OrderDetailPage.
 *
 * Responsibilities:
 *   - Fetches full order detail by order number
 *   - Manages cancel confirmation dialog state
 *   - Executes cancel mutation + exposes loading/error states
 *   - Normalizes errors for display
 *
 * Cancel flow:
 *   1. User clicks "Cancel Order" → showCancelConfirm = true
 *   2. Dialog shown with confirm/dismiss
 *   3. Confirm → mutation fires → onSuccess updates cache
 *   4. Dismiss → showCancelConfirm = false, nothing happens
 *
 * @param {string} orderNumber — from useParams() in page component
 */
export function useOrderDetail(orderNumber) {
  const [showCancelConfirm, setShowCancelConfirm] = useState(false);

  const {
    data: order,
    isLoading,
    isError,
    error,
  } = useOrderDetailQuery(orderNumber);

  const cancelMutation = useCancelOrder(orderNumber);

  const normalizedQuery = isError ? normalizeError(error) : null;
  const normalizedCancel = cancelMutation.error
    ? normalizeError(cancelMutation.error)
    : null;

  const handleCancelClick = () => setShowCancelConfirm(true);
  const handleCancelDismiss = () => setShowCancelConfirm(false);
  const handleCancelConfirm = () => {
    cancelMutation.mutate(undefined, {
      onSuccess: () => setShowCancelConfirm(false),
    });
  };

  return {
    order,
    isLoading,
    isError,
    errorMessage: normalizedQuery?.message ?? null,
    isCancelling: cancelMutation.isPending,
    cancelError: normalizedCancel?.message ?? null,
    cancelErrorCode: normalizedCancel?.errors?.non_fields?.code ?? null,
    showCancelConfirm,
    handleCancelClick,
    handleCancelDismiss,
    handleCancelConfirm,
  };
}
