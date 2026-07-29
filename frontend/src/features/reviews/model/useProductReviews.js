// src/features/reviews/model/useProductReviews.js

import { useState } from "react";
import { normalizeError } from "@shared/api";
import {
  useProductReviewsQuery,
  useEligibleItemsQuery,
} from "../api/useReviewQueries";
import { useSubmitReview, useVoteOnReview } from "../api/useReviewMutations";

/**
 * Logic hook for the Reviews tab on the Product Detail page.
 *
 * Manages:
 *   - Paginated public review list with rating filter
 *   - Eligible items check (can this user write a review?)
 *   - Inline review form state (open/close, selected item, fields)
 *   - Submit review mutation with success/error state
 *   - Vote mutation
 *
 * @param {{ slug: string, productId: number }} params
 */
export function useProductReviews({ slug, productId }) {
  // ── Pagination + filter state ─────────────────────────────────────────────
  const [page, setPage] = useState(1);
  const [ratingFilter, setRatingFilter] = useState(null); // null = all

  // ── Review form state ─────────────────────────────────────────────────────
  const [formOpen, setFormOpen] = useState(false);
  // selectedItem is the full eligible item object user chose to review
  // { order_item_id, order_number, product_name, ... }
  const [selectedItem, setSelectedItem] = useState(null);
  const [formFields, setFormFields] = useState({
    rating: 0, // 0 = not selected yet
    title: "",
    body: "",
  });

  // ── Submit result state ───────────────────────────────────────────────────
  // Tracks whether submit succeeded so we can show the success banner
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // ── Queries ───────────────────────────────────────────────────────────────
  const reviewsQuery = useProductReviewsQuery(slug, page, ratingFilter);
  const eligibleQuery = useEligibleItemsQuery(productId);

  // ── Mutations ─────────────────────────────────────────────────────────────
  const submitMutation = useSubmitReview({ slug, productId });
  const voteMutation = useVoteOnReview({ slug });

  // ── Derived data ──────────────────────────────────────────────────────────
  const reviews = reviewsQuery.data?.data ?? [];
  const meta = reviewsQuery.data?.meta ?? null;
  const totalReviews = meta?.total ?? 0;

  // eligibleItems — array of OrderItems user can review for this product
  // Empty array when not authenticated or no eligible purchases
  const eligibleItems = eligibleQuery.data?.data ?? [];
  const hasEligibleItems = eligibleItems.length > 0;

  // Auto-select first eligible item when there's only one
  // When multiple items, user sees a dropdown to pick which purchase
  const defaultItem = eligibleItems[0] ?? null;

  // ── Error normalization ───────────────────────────────────────────────────
  const submitError = submitMutation.error
    ? normalizeError(submitMutation.error)
    : null;

  const submitFieldErrors = submitError?.errors?.fields ?? null;
  const submitNonFieldError = submitError?.errors?.non_fields ?? null;

  // ── Handlers ──────────────────────────────────────────────────────────────

  const openForm = () => {
    setFormOpen(true);
    setSubmitSuccess(false);
    // Pre-select first eligible item — user can change if multiple
    setSelectedItem(defaultItem);
    setFormFields({ rating: 0, title: "", body: "" });
  };

  const closeForm = () => {
    setFormOpen(false);
    setSelectedItem(null);
    setFormFields({ rating: 0, title: "", body: "" });
  };

  const handleRatingSelect = (star) => {
    setFormFields((prev) => ({ ...prev, rating: star }));
  };

  const handleFieldChange = (e) => {
    const { name, value } = e.target;
    setFormFields((prev) => ({ ...prev, [name]: value }));
  };

  const handleItemSelect = (item) => {
    setSelectedItem(item);
  };

  const handleRatingFilter = (rating) => {
    // Clicking active filter clears it — toggles back to "All"
    setRatingFilter((prev) => (prev === rating ? null : rating));
    setPage(1); // reset to page 1 on filter change
  };

  const handlePageChange = (newPage) => {
    setPage(newPage);
  };

  const handleSubmit = () => {
    if (!selectedItem || formFields.rating === 0) return;

    submitMutation.mutate(
      {
        order_item_id: selectedItem.order_item_id,
        rating: formFields.rating,
        title: formFields.title,
        body: formFields.body,
      },
      {
        onSuccess: () => {
          setSubmitSuccess(true);
          setFormOpen(false);
          setFormFields({ rating: 0, title: "", body: "" });
          setSelectedItem(null);
        },
      },
    );
  };

  const handleVote = (reviewId, vote) => {
    voteMutation.mutate({ reviewId, vote });
  };

  // ── Return surface ────────────────────────────────────────────────────────
  return {
    // Review list
    reviews,
    meta,
    totalReviews,
    isLoadingReviews: reviewsQuery.isLoading,
    isErrorReviews: reviewsQuery.isError,

    // Pagination
    page,
    handlePageChange,

    // Rating filter
    ratingFilter,
    handleRatingFilter,

    // Eligible items
    eligibleItems,
    hasEligibleItems,

    // Form state
    formOpen,
    selectedItem,
    formFields,
    openForm,
    closeForm,
    handleRatingSelect,
    handleFieldChange,
    handleItemSelect,
    handleSubmit,

    // Submit state
    submitSuccess,
    isSubmitting: submitMutation.isPending,
    submitError,
    submitFieldErrors,
    submitNonFieldError,

    // Vote
    handleVote,
    isVoting: voteMutation.isPending,
  };
}
