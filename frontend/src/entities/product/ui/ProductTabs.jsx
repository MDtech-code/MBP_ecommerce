// src/components/product-detail/ProductTabs.jsx

import { useState } from "react";
import { MessageSquare, Wrench, ThumbsUp, ThumbsDown, CheckCircle } from "lucide-react";
import { useAuthStore } from "@entities/user";
import { useProductReviews } from "@features/reviews/model/useProductReviews";
import {Pagination} from "@shared/ui/Pagination";

/**
 * ProductTabs
 *
 * Tabs:
 *   DESCRIPTION    → product.description
 *   SPECIFICATIONS → product.specifications[] + static rows
 *   REVIEWS        → live reviews with form, rating filter, pagination
 *   COMPATIBILITY  → compatible_bikes[]
 */
export default function ProductTabs({ product }) {
  const [active, setActive] = useState("description");

  const compatible_bikes = product?.compatible_bikes ?? [];
  const specifications   = product?.specifications   ?? [];

  // ── Reviews hook ──────────────────────────────────────────────────────────
  const {
    reviews,
    meta,
    totalReviews,
    isLoadingReviews,

    
    handlePageChange,

    ratingFilter,
    handleRatingFilter,

    eligibleItems,
    hasEligibleItems,

    formOpen,
    selectedItem,
    formFields,
    openForm,
    closeForm,
    handleRatingSelect,
    handleFieldChange,
    handleItemSelect,
    handleSubmit,

    submitSuccess,
    isSubmitting,
    submitNonFieldError,
  } = useProductReviews({
    slug: product?.slug,
    productId: product?.id,
  });

  const user = useAuthStore((state) => state.user);

  // ── Tab label shows live review count ─────────────────────────────────────
  const tabs = [
    { id: "description",    label: "DESCRIPTION"    },
    { id: "specifications", label: "SPECIFICATIONS" },
    {
      id: "reviews",
      label: totalReviews > 0 ? `REVIEWS (${totalReviews})` : "REVIEWS",
    },
    { id: "compatibility",  label: "COMPATIBILITY"  },
  ];

  // ── Static spec rows ──────────────────────────────────────────────────────
  const staticTopRows = [
    { label: "Part Number", value: product?.sku ?? "—" },
    { label: "Category",    value: product?.category?.name ?? "—" },
    { label: "Brand",       value: product?.brand?.name ?? "Universal" },
  ];

  const staticBottomRows = [
    {
      label: "Weight",
      value: product?.weight_grams
        ? product.weight_grams >= 1000
          ? `${(product.weight_grams / 1000).toFixed(2)} kg`
          : `${product.weight_grams} g`
        : null,
    },
    {
      label: "Status",
      value: product?.is_in_stock ? "In Stock" : "Out of Stock",
      highlight: product?.is_in_stock,
    },
  ];

  return (
    <div className="mt-4">

      {/* ── Tab Headers ─────────────────────────────────────────────────── */}
      <div className="flex border-b border-gray-200 overflow-x-auto">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActive(tab.id)}
            className={`px-5 py-3 text-sm font-bold transition
                        relative whitespace-nowrap shrink-0
                        ${active === tab.id
                          ? "text-primary"
                          : "text-gray-500 hover:text-gray-700"
                        }`}
          >
            {tab.label}
            {active === tab.id && (
              <span className="absolute bottom-0 left-0 right-0 h-0.5
                               bg-primary rounded-full" />
            )}
          </button>
        ))}
      </div>

      {/* ── Tab Content ──────────────────────────────────────────────────── */}
      <div className="py-5">

        {/* ── Description ─────────────────────────────────────────────── */}
        {active === "description" && (
          <div>
            {product?.description ? (
              <p className="text-sm text-gray-600 leading-relaxed
                            whitespace-pre-line">
                {product.description}
              </p>
            ) : (
              <p className="text-sm text-gray-400 italic">
                No description available.
              </p>
            )}
          </div>
        )}

        {/* ── Specifications ───────────────────────────────────────────── */}
        {active === "specifications" && (
          <div className="max-w-lg">
            <table className="w-full text-sm border border-gray-100
                              rounded-lg overflow-hidden">
              <tbody>
                {staticTopRows.map((row, i) => (
                  <SpecRow
                    key={row.label}
                    label={row.label}
                    value={row.value}
                    index={i}
                  />
                ))}
                {specifications.length > 0 ? (
                  specifications
                    .slice()
                    .sort((a, b) => a.display_order - b.display_order)
                    .map((spec, i) => (
                      <SpecRow
                        key={spec.id}
                        label={spec.name}
                        value={
                          spec.unit
                            ? `${spec.value} ${spec.unit}`
                            : spec.value
                        }
                        index={staticTopRows.length + i}
                      />
                    ))
                ) : (
                  <tr className="bg-gray-50">
                    <td
                      colSpan={2}
                      className="py-3 px-4 text-xs text-gray-400
                                 italic border-b border-gray-100 text-center"
                    >
                      No additional specifications provided.
                    </td>
                  </tr>
                )}
                {staticBottomRows.map((row, i) => (
                  <SpecRow
                    key={row.label}
                    label={row.label}
                    value={row.value}
                    highlight={row.highlight}
                    index={staticTopRows.length + specifications.length + i}
                  />
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* ── Reviews ─────────────────────────────────────────────────── */}
        {active === "reviews" && (
          <div>

            {/* ── Submit success banner ──────────────────────────────── */}
            {submitSuccess && (
              <div className="flex items-start gap-3 bg-green-50
                              border border-green-200 rounded-xl
                              px-4 py-4 mb-6">
                <CheckCircle
                  size={18}
                  className="text-green-600 shrink-0 mt-0.5"
                />
                <div>
                  <p className="text-sm font-semibold text-green-800">
                    Review submitted
                  </p>
                  <p className="text-xs text-green-700 mt-0.5">
                    Your review is pending moderation and will appear
                    once approved by our team.
                  </p>
                </div>
              </div>
            )}

            {/* ── Eligible prompt + inline form ─────────────────────── */}
            {user && hasEligibleItems && !submitSuccess && (
              <div className="mb-6">

                {/* Prompt bar */}
                {!formOpen && (
                  <div className="flex items-center justify-between
                                  bg-surface border border-gray-200
                                  rounded-xl px-4 py-3">
                    <p className="text-sm text-gray-700 font-medium">
                      ✏️ You purchased this product
                    </p>
                    <button
                      onClick={openForm}
                      className="text-sm font-semibold text-primary
                                 hover:underline"
                    >
                      Write a Review ▾
                    </button>
                  </div>
                )}

                {/* Inline review form */}
                {formOpen && (
                  <div className="border border-gray-200 rounded-xl
                                  p-5 bg-white">

                    {/* Header */}
                    <p className="text-sm font-semibold text-gray-800 mb-4">
                      Reviewing:{" "}
                      <span className="text-gray-600 font-normal">
                        {selectedItem?.product_name}
                      </span>
                      {selectedItem?.order_number && (
                        <span className="text-gray-400 ml-2 font-normal">
                          — Order #{selectedItem.order_number}
                        </span>
                      )}
                    </p>

                    {/* Multiple eligible items — dropdown to pick which */}
                    {eligibleItems.length > 1 && (
                      <div className="mb-4">
                        <label className="block text-xs font-semibold
                                          text-gray-600 mb-1.5">
                          Select Purchase
                        </label>
                        <select
                          value={selectedItem?.order_item_id ?? ""}
                          onChange={(e) => {
                            const found = eligibleItems.find(
                              (it) =>
                                it.order_item_id === Number(e.target.value)
                            );
                            if (found) handleItemSelect(found);
                          }}
                          className="w-full border border-gray-200 rounded-lg
                                     px-3 py-2 text-sm text-gray-700
                                     focus:outline-none focus:ring-2
                                     focus:ring-primary/30"
                        >
                          {eligibleItems.map((item) => (
                            <option
                              key={item.order_item_id}
                              value={item.order_item_id}
                            >
                              Order #{item.order_number}
                            </option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* Star rating */}
                    <div className="mb-4">
                      <label className="block text-xs font-semibold
                                        text-gray-600 mb-1.5">
                        Your Rating{" "}
                        <span className="text-primary">*</span>
                      </label>
                      <StarPicker
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
                        className="w-full border border-gray-200 rounded-lg
                                   px-3 py-2 text-sm text-gray-700
                                   placeholder:text-gray-300
                                   focus:outline-none focus:ring-2
                                   focus:ring-primary/30"
                      />
                    </div>

                    {/* Body */}
                    <div className="mb-5">
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
                        rows={4}
                        placeholder="Tell others about your experience with this product"
                        className="w-full border border-gray-200 rounded-lg
                                   px-3 py-2 text-sm text-gray-700
                                   placeholder:text-gray-300 resize-none
                                   focus:outline-none focus:ring-2
                                   focus:ring-primary/30"
                      />
                    </div>

                    {/* Non-field error */}
                    {submitNonFieldError && (
                      <p className="text-xs text-red-600 mb-4">
                        {submitNonFieldError.message}
                      </p>
                    )}

                    {/* Actions */}
                    <div className="flex items-center justify-between">
                      <button
                        onClick={closeForm}
                        disabled={isSubmitting}
                        className="text-sm text-gray-500 hover:text-gray-700
                                   font-medium disabled:opacity-50"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSubmit}
                        disabled={
                          isSubmitting || formFields.rating === 0
                        }
                        className="bg-primary text-white text-sm font-semibold
                                   px-5 py-2 rounded-lg hover:bg-red-700
                                   transition disabled:opacity-50
                                   disabled:cursor-not-allowed"
                      >
                        {isSubmitting ? "Submitting…" : "Submit Review →"}
                      </button>
                    </div>

                  </div>
                )}
              </div>
            )}

            {/* ── Rating filter buttons ──────────────────────────────── */}
            {!isLoadingReviews && reviews.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap mb-5">
                <button
                  onClick={() => handleRatingFilter(null)}
                  className={`px-3 py-1.5 rounded-full text-xs font-semibold
                              border transition
                              ${ratingFilter === null
                                ? "bg-primary text-white border-primary"
                                : "border-gray-200 text-gray-600 hover:border-gray-400"
                              }`}
                >
                  All
                </button>
                {[5, 4, 3, 2, 1].map((star) => (
                  <button
                    key={star}
                    onClick={() => handleRatingFilter(star)}
                    className={`px-3 py-1.5 rounded-full text-xs font-semibold
                                border transition
                                ${ratingFilter === star
                                  ? "bg-primary text-white border-primary"
                                  : "border-gray-200 text-gray-600 hover:border-gray-400"
                                }`}
                  >
                    ★{star}
                  </button>
                ))}
              </div>
            )}

            {/* ── Loading state ──────────────────────────────────────── */}
            {isLoadingReviews && (
              <div className="space-y-4">
                {[1, 2, 3].map((n) => (
                  <div
                    key={n}
                    className="h-24 bg-gray-100 rounded-xl animate-pulse"
                  />
                ))}
              </div>
            )}

            {/* ── Review list ────────────────────────────────────────── */}
            {!isLoadingReviews && reviews.length > 0 && (
              <div className="space-y-4">
                {reviews.map((review) => (
                  <ReviewCard
                    key={review.id}
                    review={review}
                    onVote={(vote) =>
                      handleVote(review.id, vote)
                    }
                  />
                ))}
              </div>
            )}

            {/* ── Empty state ────────────────────────────────────────── */}
            {!isLoadingReviews && reviews.length === 0 && (
              <div className="flex flex-col items-center py-10 text-center">
                <MessageSquare
                  size={36}
                  className="text-gray-300 mb-3"
                  strokeWidth={1.5}
                />
                <p className="text-sm font-bold text-gray-700">
                  No reviews yet
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  Be the first to review this product
                </p>
              </div>
            )}

           {/* ── Pagination ─────────────────────────────────────────────────── */}
            {!isLoadingReviews && meta && meta.total_pages > 1 && (
              <Pagination
                currentPage={meta.page}
                totalPages={meta.total_pages}
                hasNext={meta.has_next}
                hasPrevious={meta.has_previous}
                onPageChange={handlePageChange}
              />
            )}

          </div>
        )}

        {/* ── Compatibility ────────────────────────────────────────────── */}
        {active === "compatibility" && (
          <div>
            {compatible_bikes.length > 0 ? (
              <>
                <p className="text-sm text-gray-500 mb-3">
                  This part is compatible with the following bike models:
                </p>
                <div className="flex gap-2 flex-wrap">
                  {compatible_bikes.map((bike) => (
                    <span
                      key={bike.id}
                      className="border border-gray-300 px-4 py-1.5
                                 rounded-md text-sm text-gray-700 bg-gray-50"
                    >
                      {bike.display_name}
                      {bike.year_end
                        ? ` (${bike.year_start}–${bike.year_end})`
                        : ` (${bike.year_start}–present)`
                      }
                    </span>
                  ))}
                </div>
              </>
            ) : (
              <div className="flex items-center gap-2 text-green-700
                              bg-green-50 border border-green-200
                              rounded-lg px-4 py-3">
                <Wrench size={16} className="shrink-0" />
                <span className="text-sm font-semibold">
                  Universal — Compatible with all bikes
                </span>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// StarPicker — inline clickable star rating, no library
// Props:
//   value    number  — currently selected rating (0 = none)
//   onChange fn      — called with star number (1-5)
// ─────────────────────────────────────────────────────────────────────────────
function StarPicker({ value, onChange }) {
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
// StarDisplay — read-only star row for review cards
// Props:
//   rating  number  — 1-5
//   size    string  — "sm" | "md"
// ─────────────────────────────────────────────────────────────────────────────
function StarDisplay({ rating, size = "sm" }) {
  const sizeClass = size === "md" ? "text-base" : "text-sm";

  return (
    <span className={`${sizeClass} leading-none`}>
      {[1, 2, 3, 4, 5].map((star) => (
        <span
          key={star}
          className={star <= rating ? "text-yellow-400" : "text-gray-300"}
        >
          ★
        </span>
      ))}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// ReviewCard — single approved review display
// Props:
//   review  object  — ReviewListSerializer shape from backend
//   onVote  fn      — called with "helpful" | "not_helpful"
// ─────────────────────────────────────────────────────────────────────────────
function ReviewCard({ review, onVote }) {
  const formattedDate = review.created_at
    ? new Date(review.created_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <div className="border border-gray-100 rounded-xl p-4 bg-white">

      {/* ── Header row ─────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <StarDisplay rating={review.rating} />
          <span className="text-sm font-semibold text-gray-800">
            {review.reviewer?.display_name ?? "Customer"}
          </span>
          {review.is_verified_purchase && (
            <span className="text-xs text-green-700 font-medium">
              ✓ Verified Purchase
            </span>
          )}
        </div>
        {formattedDate && (
          <span className="text-xs text-gray-400 shrink-0">
            {formattedDate}
          </span>
        )}
      </div>

      {/* ── Title ──────────────────────────────────────────────────── */}
      {review.title && (
        <p className="text-sm font-semibold text-gray-800 mb-1">
          "{review.title}"
        </p>
      )}

      {/* ── Body ───────────────────────────────────────────────────── */}
      {review.body && (
        <p className="text-sm text-gray-600 leading-relaxed mb-3">
          {review.body}
        </p>
      )}

      {/* ── Vote row ───────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 mt-2">
        <button
          onClick={() => onVote("helpful")}
          className="flex items-center gap-1.5 text-xs text-gray-500
                     hover:text-gray-800 transition"
        >
          <ThumbsUp size={13} />
          Helpful ({review.helpful_count})
        </button>
        <button
          onClick={() => onVote("not_helpful")}
          className="flex items-center gap-1.5 text-xs text-gray-500
                     hover:text-gray-800 transition"
        >
          <ThumbsDown size={13} />
          Not Helpful ({review.not_helpful_count})
        </button>
      </div>

    </div>
  );
}


// ─────────────────────────────────────────────────────────────────────────────
// SpecRow — unchanged from original
// ─────────────────────────────────────────────────────────────────────────────
function SpecRow({ label, value, index = 0, highlight = false }) {
  return (
    <tr className={index % 2 === 0 ? "bg-gray-50" : "bg-white"}>
      <td className="py-3 px-4 font-semibold text-gray-700 w-36
                     border-b border-gray-100 align-top">
        {label}
      </td>
      <td className="py-3 px-4 border-b border-gray-100">
        {highlight ? (
          <span className="text-green-600 font-semibold">
            {value ?? "—"}
          </span>
        ) : (
          <span className="text-gray-600">
            {value ?? "—"}
          </span>
        )}
      </td>
    </tr>
  );
}
// // src/components/product-detail/ProductTabs.jsx
// import { useState } from "react";
// import { MessageSquare, Wrench } from "lucide-react";

// /**
//  * ProductTabs
//  *
//  * Tabs:
//  *   DESCRIPTION    → product.description
//  *   SPECIFICATIONS → product.specifications[] from backend
//  *                    + static rows: Part Number, Category, Brand, Status, Weight
//  *   REVIEWS        → placeholder until reviews app ships
//  *   COMPATIBILITY  → compatible_bikes[] with year range
//  */
// export default function ProductTabs({ product }) {
//   const [active, setActive] = useState("description");

//   const compatible_bikes = product?.compatible_bikes ?? [];
//   const specifications   = product?.specifications   ?? [];

//   const tabs = [
//     { id: "description",    label: "DESCRIPTION"    },
//     { id: "specifications", label: "SPECIFICATIONS" },
//     { id: "reviews",        label: "REVIEWS (0)"    },
//     { id: "compatibility",  label: "COMPATIBILITY"  },
//   ];

//   // ── Static rows (always shown, from top-level product fields) ─────────────
//   // These sit above the dynamic spec rows so they're always visible.
//   const staticTopRows = [
//     {
//       label: "Part Number",
//       value: product?.sku ?? "—",
//     },
//     {
//       label: "Category",
//       value: product?.category?.name ?? "—",
//     },
//     {
//       label: "Brand",
//       value: product?.brand?.name ?? "Universal",
//     },
//   ];

//   const staticBottomRows = [
//     {
//       label: "Weight",
//       // weight_grams comes from backend; convert to readable format
//       value: product?.weight_grams
//         ? product.weight_grams >= 1000
//           ? `${(product.weight_grams / 1000).toFixed(2)} kg`
//           : `${product.weight_grams} g`
//         : null,
//     },
//     {
//       label: "Status",
//       value: product?.is_in_stock ? "In Stock" : "Out of Stock",
//       highlight: product?.is_in_stock,
//     },
//   ];

//   return (
//     <div className="mt-4">

//       {/* Tab Headers */}
//       <div className="flex border-b border-gray-200 overflow-x-auto">
//         {tabs.map((tab) => (
//           <button
//             key={tab.id}
//             onClick={() => setActive(tab.id)}
//             className={`px-5 py-3 text-sm font-bold transition
//                         relative whitespace-nowrap shrink-0
//                         ${active === tab.id
//                           ? "text-primary"
//                           : "text-gray-500 hover:text-gray-700"
//                         }`}
//           >
//             {tab.label}
//             {active === tab.id && (
//               <span className="absolute bottom-0 left-0 right-0 h-0.5
//                                bg-primary rounded-full" />
//             )}
//           </button>
//         ))}
//       </div>

//       {/* Tab Content */}
//       <div className="py-5">

//         {/* ── Description ─────────────────────────────────────────────────── */}
//         {active === "description" && (
//           <div>
//             {product?.description ? (
//               <p className="text-sm text-gray-600 leading-relaxed
//                             whitespace-pre-line">
//                 {product.description}
//               </p>
//             ) : (
//               <p className="text-sm text-gray-400 italic">
//                 No description available.
//               </p>
//             )}
//           </div>
//         )}

//         {/* ── Specifications ───────────────────────────────────────────────── */}
//         {active === "specifications" && (
//           <div className="max-w-lg">
//             <table className="w-full text-sm border border-gray-100 rounded-lg
//                               overflow-hidden">
//               <tbody>

//                 {/* Static Top Rows — Part Number, Category, Brand */}
//                 {staticTopRows.map((row, i) => (
//                   <SpecRow
//                     key={row.label}
//                     label={row.label}
//                     value={row.value}
//                     index={i}
//                   />
//                 ))}

//                 {/* Dynamic Rows — from product.specifications[] */}
//                 {specifications.length > 0 ? (
//                   specifications
//                     // already ordered by display_order from backend
//                     // but sort defensively in case order changes
//                     .slice()
//                     .sort((a, b) => a.display_order - b.display_order)
//                     .map((spec, i) => (
//                       <SpecRow
//                         key={spec.id}
//                         label={spec.name}
//                         value={
//                           spec.unit
//                             ? `${spec.value} ${spec.unit}`
//                             : spec.value
//                         }
//                         // continue alternating stripe from where static rows ended
//                         index={staticTopRows.length + i}
//                       />
//                     ))
//                 ) : (
//                   // Only show this when backend returns empty specs array
//                   <tr className="bg-gray-50">
//                     <td
//                       colSpan={2}
//                       className="py-3 px-4 text-xs text-gray-400 italic
//                                  border-b border-gray-100 text-center"
//                     >
//                       No additional specifications provided.
//                     </td>
//                   </tr>
//                 )}

//                 {/* Static Bottom Rows — Weight, Status */}
//                 {staticBottomRows.map((row, i) => (
//                   <SpecRow
//                     key={row.label}
//                     label={row.label}
//                     value={row.value}
//                     highlight={row.highlight}
//                     index={staticTopRows.length + specifications.length + i}
//                   />
//                 ))}

//               </tbody>
//             </table>
//           </div>
//         )}

//         {/* ── Reviews ─────────────────────────────────────────────────────── */}
//         {active === "reviews" && (
//           <div className="flex flex-col items-center py-8 text-center">
//             <MessageSquare
//               size={36}
//               className="text-gray-300 mb-3"
//               strokeWidth={1.5}
//             />
//             <p className="text-sm font-bold text-gray-700">
//               No reviews yet
//             </p>
//             <p className="text-xs text-gray-400 mt-1">
//               Be the first to review this product
//             </p>
//           </div>
//         )}

//         {/* ── Compatibility ────────────────────────────────────────────────── */}
//         {active === "compatibility" && (
//           <div>
//             {compatible_bikes.length > 0 ? (
//               <>
//                 <p className="text-sm text-gray-500 mb-3">
//                   This part is compatible with the following bike models:
//                 </p>
//                 <div className="flex gap-2 flex-wrap">
//                   {compatible_bikes.map((bike) => (
//                     <span
//                       key={bike.id}
//                       className="border border-gray-300 px-4 py-1.5
//                                  rounded-md text-sm text-gray-700 bg-gray-50"
//                     >
//                       {bike.display_name}
//                       {bike.year_end
//                         ? ` (${bike.year_start}–${bike.year_end})`
//                         : ` (${bike.year_start}–present)`
//                       }
//                     </span>
//                   ))}
//                 </div>
//               </>
//             ) : (
//               <div className="flex items-center gap-2 text-green-700
//                               bg-green-50 border border-green-200
//                               rounded-lg px-4 py-3">
//                 <Wrench size={16} className="shrink-0" />
//                 <span className="text-sm font-semibold">
//                   Universal — Compatible with all bikes
//                 </span>
//               </div>
//             )}
//           </div>
//         )}

//       </div>
//     </div>
//   );
// }

// // ─────────────────────────────────────────────────────────────────────────────
// // SpecRow — reusable table row
// // Props:
// //   label     string   — left cell label
// //   value     string   — right cell value  (null → "—")
// //   index     number   — used for alternating stripe color
// //   highlight boolean  — green text (used for "In Stock")
// // ─────────────────────────────────────────────────────────────────────────────
// function SpecRow({ label, value, index = 0, highlight = false }) {
//   return (
//     <tr className={index % 2 === 0 ? "bg-gray-50" : "bg-white"}>

//       {/* Label */}
//       <td className="py-3 px-4 font-semibold text-gray-700 w-36
//                      border-b border-gray-100 align-top">
//         {label}
//       </td>

//       {/* Value */}
//       <td className="py-3 px-4 border-b border-gray-100">
//         {highlight ? (
//           <span className="text-green-600 font-semibold">
//             {value ?? "—"}
//           </span>
//         ) : (
//           <span className="text-gray-600">
//             {value ?? "—"}
//           </span>
//         )}
//       </td>

//     </tr>
//   );
// }
