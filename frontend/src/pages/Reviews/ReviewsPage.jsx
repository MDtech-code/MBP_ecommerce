// src/pages/ReviewsPage/ReviewsPage.jsx

import { Link } from "react-router-dom";
import { Star, Clock, CheckCircle, ChevronRight } from "lucide-react";
import { useMyReviews } from "@features/reviews";
import { useState } from "react";

/**
 * ReviewsPage — /reviews
 *
 * Renders inside DashboardLayout outlet.
 *
 * Two sections:
 *   1. Pending Reviews  — products user can review (from GET /api/reviews/pending/)
 *   2. Your Reviews     — reviews user has submitted (from GET /api/reviews/my-reviews/)
 *
 * Inline review form opens per pending item.
 * Only one form open at a time — controlled by activeItemId.
 */
export default function ReviewsPage() {
  const {
    // Pending
    pendingItems,
    isLoadingPending,
    isErrorPending,

    // My reviews
    myReviews,
    isLoadingMyReviews,
    isErrorMyReviews,

    // Form
    activeItemId,
    formFields,
    openForm,
    closeForm,
    handleRatingSelect,
    handleFieldChange,
    handleSubmit,

    // Submit state
    submitSuccessId,
    isSubmitting,
    submitNonFieldError,
  } = useMyReviews();

  return (
    <div className="max-w-3xl">

      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="mb-8">
        <h1 className="text-xl font-bold text-dark">My Reviews</h1>
        <p className="text-sm text-muted mt-1">
          Manage your product reviews and pending items.
        </p>
      </div>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 1 — PENDING REVIEWS
      ══════════════════════════════════════════════════════════════════ */}
      <section className="mb-10">

        <div className="flex items-center gap-2 mb-4">
          <Clock size={16} className="text-muted" />
          <h2 className="text-sm font-bold text-dark uppercase tracking-wide">
            Pending Reviews
          </h2>
          {pendingItems.length > 0 && (
            <span className="ml-auto text-xs text-muted">
              {pendingItems.length} item{pendingItems.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Loading */}
        {isLoadingPending && (
          <div className="space-y-3">
            {[1, 2].map((n) => (
              <div
                key={n}
                className="h-20 bg-gray-100 rounded-xl animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Error */}
        {isErrorPending && !isLoadingPending && (
          <p className="text-sm text-red-500">
            Failed to load pending reviews. Please refresh.
          </p>
        )}

        {/* Empty state */}
        {!isLoadingPending && !isErrorPending && pendingItems.length === 0 && (
          <div className="border border-dashed border-gray-200 rounded-xl
                          px-5 py-8 text-center">
            <p className="text-sm font-semibold text-gray-700">
              All caught up!
            </p>
            <p className="text-xs text-muted mt-1">
              You have no pending reviews.
            </p>
          </div>
        )}

        {/* Pending item cards */}
        {!isLoadingPending && !isErrorPending && pendingItems.length > 0 && (
          <div className="space-y-3">
            {pendingItems.map((item) => (
              <div key={item.order_item_id}>

                {/* ── Success banner per item ────────────────────────── */}
                {submitSuccessId === item.order_item_id && (
                  <div className="flex items-start gap-3 bg-green-50
                                  border border-green-200 rounded-xl
                                  px-4 py-3 mb-2">
                    <CheckCircle
                      size={16}
                      className="text-green-600 shrink-0 mt-0.5"
                    />
                    <div>
                      <p className="text-sm font-semibold text-green-800">
                        Review submitted
                      </p>
                      <p className="text-xs text-green-700 mt-0.5">
                        Pending moderation — will appear once approved.
                      </p>
                    </div>
                  </div>
                )}

                {/* ── Pending item card ──────────────────────────────── */}
                {submitSuccessId !== item.order_item_id && (
                  <div className="border border-gray-200 rounded-xl
                                  bg-white overflow-hidden">

                    {/* Card header row */}
                    <div className="flex items-center gap-4 p-4">

                      {/* Product image */}
                      <div className="w-14 h-14 rounded-lg overflow-hidden
                                      bg-gray-100 shrink-0">
                        {item.product_image ? (
                          <img
                            src={item.product_image}
                            alt={item.product_name}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center
                                          justify-center">
                            <Star
                              size={20}
                              className="text-gray-300"
                              strokeWidth={1.5}
                            />
                          </div>
                        )}
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-dark
                                      truncate">
                          {item.product_name}
                        </p>
                        <p className="text-xs text-muted mt-0.5">
                          Order #{item.order_number} · Delivered
                        </p>
                      </div>

                      {/* Write review CTA */}
                      {activeItemId !== item.order_item_id && (
                        <button
                          onClick={() => openForm(item)}
                          className="flex items-center gap-1 text-xs
                                     font-semibold text-primary
                                     hover:underline shrink-0"
                        >
                          Write a Review
                          <ChevronRight size={13} />
                        </button>
                      )}
                    </div>

                    {/* ── Inline form — expands below card row ──────── */}
                    {activeItemId === item.order_item_id && (
                      <div className="border-t border-gray-100 p-4 bg-surface">

                        {/* Star rating */}
                        <div className="mb-4">
                          <label className="block text-xs font-semibold
                                            text-gray-600 mb-1.5">
                            Your Rating{" "}
                            <span className="text-primary">*</span>
                          </label>
                          <DashboardStarPicker
                            value={formFields.rating}
                            onChange={handleRatingSelect}
                          />
                        </div>

                        {/* Title */}
                        <div className="mb-4">
                          <label className="block text-xs font-semibold
                                            text-gray-600 mb-1.5">
                            Title{" "}
                            <span className="text-gray-400 font-normal">
                              (optional)
                            </span>
                          </label>
                          <input
                            type="text"
                            name="title"
                            value={formFields.title}
                            onChange={handleFieldChange}
                            maxLength={100}
                            placeholder="Summarise your experience"
                            className="w-full border border-gray-200
                                       rounded-lg px-3 py-2 text-sm
                                       text-gray-700 placeholder:text-gray-300
                                       focus:outline-none focus:ring-2
                                       focus:ring-primary/30"
                          />
                        </div>

                        {/* Body */}
                        <div className="mb-4">
                          <label className="block text-xs font-semibold
                                            text-gray-600 mb-1.5">
                            Your Review{" "}
                            <span className="text-gray-400 font-normal">
                              (optional)
                            </span>
                          </label>
                          <textarea
                            name="body"
                            value={formFields.body}
                            onChange={handleFieldChange}
                            rows={3}
                            placeholder="Tell others about your experience"
                            className="w-full border border-gray-200
                                       rounded-lg px-3 py-2 text-sm
                                       text-gray-700 placeholder:text-gray-300
                                       resize-none focus:outline-none
                                       focus:ring-2 focus:ring-primary/30"
                          />
                        </div>

                        {/* Non-field error */}
                        {submitNonFieldError && (
                          <p className="text-xs text-red-600 mb-3">
                            {submitNonFieldError.message}
                          </p>
                        )}

                        {/* Actions */}
                        <div className="flex items-center
                                        justify-between">
                          <button
                            onClick={closeForm}
                            disabled={isSubmitting}
                            className="text-sm text-gray-500
                                       hover:text-gray-700 font-medium
                                       disabled:opacity-50"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSubmit}
                            disabled={
                              isSubmitting || formFields.rating === 0
                            }
                            className="bg-primary text-white text-sm
                                       font-semibold px-5 py-2 rounded-lg
                                       hover:bg-red-700 transition
                                       disabled:opacity-50
                                       disabled:cursor-not-allowed"
                          >
                            {isSubmitting
                              ? "Submitting…"
                              : "Submit Review →"}
                          </button>
                        </div>

                      </div>
                    )}

                  </div>
                )}

              </div>
            ))}
          </div>
        )}

      </section>

      {/* ══════════════════════════════════════════════════════════════════
          SECTION 2 — YOUR REVIEWS
      ══════════════════════════════════════════════════════════════════ */}
      <section>

        <div className="flex items-center gap-2 mb-4">
          <Star size={16} className="text-muted" />
          <h2 className="text-sm font-bold text-dark uppercase tracking-wide">
            Your Reviews
          </h2>
          {myReviews.length > 0 && (
            <span className="ml-auto text-xs text-muted">
              {myReviews.length} review{myReviews.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Loading */}
        {isLoadingMyReviews && (
          <div className="space-y-3">
            {[1, 2].map((n) => (
              <div
                key={n}
                className="h-24 bg-gray-100 rounded-xl animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Error */}
        {isErrorMyReviews && !isLoadingMyReviews && (
          <p className="text-sm text-red-500">
            Failed to load your reviews. Please refresh.
          </p>
        )}

        {/* Empty state */}
        {!isLoadingMyReviews &&
          !isErrorMyReviews &&
          myReviews.length === 0 && (
            <div className="border border-dashed border-gray-200
                            rounded-xl px-5 py-8 text-center">
              <p className="text-sm font-semibold text-gray-700">
                No reviews yet
              </p>
              <p className="text-xs text-muted mt-1">
                You haven't submitted any reviews yet.
              </p>
            </div>
          )}

        {/* Review history cards */}
        {!isLoadingMyReviews &&
          !isErrorMyReviews &&
          myReviews.length > 0 && (
            <div className="space-y-3">
              {myReviews.map((review) => (
                <MyReviewCard key={review.id} review={review} />
              ))}
            </div>
          )}

      </section>

    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// DashboardStarPicker — same logic as ProductTabs StarPicker
// Kept inline here — ReviewsPage is a separate page,
// no shared component needed between two different contexts.
// ─────────────────────────────────────────────────────────────────────────────
function DashboardStarPicker({ value, onChange }) {
  const [hovered, setHovered] = useState(0);

  return (
    <div className="flex gap-1">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHovered(star)}
          onMouseLeave={() => setHovered(0)}
          className="text-2xl leading-none transition-transform
                     hover:scale-110 focus:outline-none"
          aria-label={`Rate ${star} star${star > 1 ? "s" : ""}`}
        >
          <span
            className={
              star <= (hovered || value)
                ? "text-yellow-400"
                : "text-gray-300"
            }
          >
            ★
          </span>
        </button>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// MyReviewCard — single submitted review in history section
// Shape: UserReviewHistorySerializer
//   id, product_name, product_slug, product_image, order_number,
//   rating, title, body, is_approved, created_at, updated_at
// ─────────────────────────────────────────────────────────────────────────────
function MyReviewCard({ review }) {
  const formattedDate = review.created_at
    ? new Date(review.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <div className="border border-gray-200 rounded-xl bg-white p-4">
      <div className="flex items-start gap-4">

        {/* Product image */}
        <div className="w-14 h-14 rounded-lg overflow-hidden
                        bg-gray-100 shrink-0">
          {review.product_image ? (
            <img
              src={review.product_image}
              alt={review.product_name}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center
                            justify-center">
              <Star
                size={20}
                className="text-gray-300"
                strokeWidth={1.5}
              />
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">

          {/* Product name — links to product page */}
          {review.product_slug ? (
            <Link
              to={`/product/${review.product_slug}`}
              className="text-sm font-semibold text-dark hover:text-primary
                         transition truncate block"
            >
              {review.product_name || "Product"}
            </Link>
          ) : (
            <p className="text-sm font-semibold text-dark truncate">
              {review.product_name || "Product"}
            </p>
          )}

          {/* Star rating row */}
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span className="text-sm leading-none">
              {[1, 2, 3, 4, 5].map((star) => (
                <span
                  key={star}
                  className={
                    star <= review.rating
                      ? "text-yellow-400"
                      : "text-gray-300"
                  }
                >
                  ★
                </span>
              ))}
            </span>

            {/* Moderation status badge */}
            {review.is_approved ? (
              <span className="inline-flex items-center gap-1 text-xs
                               font-semibold text-green-700 bg-green-50
                               border border-green-200 px-2 py-0.5
                               rounded-full">
                <CheckCircle size={11} />
                Published
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs
                               font-semibold text-yellow-700 bg-yellow-50
                               border border-yellow-200 px-2 py-0.5
                               rounded-full">
                <Clock size={11} />
                Pending Approval
              </span>
            )}
          </div>

          {/* Review title */}
          {review.title && (
            <p className="text-sm font-semibold text-gray-800 mt-2">
              "{review.title}"
            </p>
          )}

          {/* Review body */}
          {review.body && (
            <p className="text-xs text-gray-500 mt-1 leading-relaxed
                          line-clamp-2">
              {review.body}
            </p>
          )}

          {/* Footer */}
          <div className="flex items-center gap-3 mt-2 flex-wrap">
            {review.order_number && (
              <span className="text-xs text-muted">
                Order #{review.order_number}
              </span>
            )}
            {formattedDate && (
              <span className="text-xs text-muted">
                Submitted {formattedDate}
              </span>
            )}
          </div>

        </div>
      </div>
    </div>
  );
}