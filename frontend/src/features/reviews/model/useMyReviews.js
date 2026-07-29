// src/features/reviews/model/useReviewDashboard.js

import { useState } from "react";
import { normalizeError } from "@shared/api";
import {
  usePendingReviewsQuery,
  useMyReviewsQuery,
} from "../api/useReviewQueries";
import { useSubmitReview } from "../api/useReviewMutations";

/**
 * Logic hook for the /reviews dashboard page.
 *
 * Manages:
 *   - Pending reviews list (products user can review)
 *   - My reviews history list (reviews user has submitted)
 *   - Inline review form per pending item
 *
 * Form is identified by order_item_id — only one form
 * open at a time across all pending items.
 *
 * @param {{ slug?: string, productId?: number }} params
 * Slug and productId are not known upfront on the dashboard —
 * they are derived from the selected pending item when form opens.
 */
export function useReviewDashboard() {
  // ── Active form state ─────────────────────────────────────────────────────
  // Tracks which pending item's form is open (by order_item_id)
  // null = no form open
  const [activeItemId, setActiveItemId] = useState(null);
  const [formFields, setFormFields] = useState({
    rating: 0,
    title: "",
    body: "",
  });

  // ── Submit result state ───────────────────────────────────────────────────
  const [submitSuccessId, setSubmitSuccessId] = useState(null);

  // ── Queries ───────────────────────────────────────────────────────────────
  const pendingQuery = usePendingReviewsQuery();
  const myReviewsQuery = useMyReviewsQuery();

  // ── Derived data ──────────────────────────────────────────────────────────
  const pendingItems = pendingQuery.data?.data ?? [];
  const myReviews = myReviewsQuery.data?.data ?? [];

  // Active item full object — needed for submit payload
  const activeItem = pendingItems.find(
    (item) => item.order_item_id === activeItemId
  ) ?? null;

  // ── Mutation ──────────────────────────────────────────────────────────────
  // slug and productId not available upfront on dashboard —
  // invalidation of product-scoped queries uses activeItem data
  // pendingReviews + myReviews invalidation always happens regardless
  const submitMutation = useSubmitReview({
    slug: activeItem?.product_slug ?? null,
    productId: null, // not available from pending item data
  });

  // ── Error normalization ───────────────────────────────────────────────────
  const submitError = submitMutation.error
    ? normalizeError(submitMutation.error)
    : null;

  const submitNonFieldError = submitError?.errors?.non_fields ?? null;

  // ── Handlers ──────────────────────────────────────────────────────────────

  const openForm = (item) => {
    setActiveItemId(item.order_item_id);
    setSubmitSuccessId(null);
    setFormFields({ rating: 0, title: "", body: "" });
  };

  const closeForm = () => {
    setActiveItemId(null);
    setFormFields({ rating: 0, title: "", body: "" });
  };

  const handleRatingSelect = (star) => {
    setFormFields((prev) => ({ ...prev, rating: star }));
  };

  const handleFieldChange = (e) => {
    const { name, value } = e.target;
    setFormFields((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = () => {
    if (!activeItem || formFields.rating === 0) return;

    submitMutation.mutate(
      {
        order_item_id: activeItem.order_item_id,
        rating: formFields.rating,
        title: formFields.title,
        body: formFields.body,
      },
      {
        onSuccess: () => {
          setSubmitSuccessId(activeItem.order_item_id);
          setActiveItemId(null);
          setFormFields({ rating: 0, title: "", body: "" });
        },
      }
    );
  };

  // ── Return surface ────────────────────────────────────────────────────────
  return {
    // Pending items
    pendingItems,
    isLoadingPending: pendingQuery.isLoading,
    isErrorPending: pendingQuery.isError,

    // My reviews
    myReviews,
    isLoadingMyReviews: myReviewsQuery.isLoading,
    isErrorMyReviews: myReviewsQuery.isError,

    // Form state
    activeItemId,
    activeItem,
    formFields,
    openForm,
    closeForm,
    handleRatingSelect,
    handleFieldChange,
    handleSubmit,

    // Submit state
    submitSuccessId,
    isSubmitting: submitMutation.isPending,
    submitError,
    submitNonFieldError,
  };
}