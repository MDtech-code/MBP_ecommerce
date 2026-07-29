// src/pages/WishlistPage/WishlistPage.jsx

import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Heart,
  ShoppingCart,
  Trash2,
  PackageOpen,
  ArrowRight,
} from "lucide-react";
import { useWishlist } from "@features/wishlist/model/useWishlist";
import { useCart } from "@features/cart/model/useCart";
import {Pagination} from "@shared/ui/Pagination";

/**
 * WishlistPage — /wishlist
 *
 * Renders inside DashboardLayout outlet.
 *
 * Features:
 *   - Paginated wishlist items grid
 *   - Add to cart directly from wishlist card
 *   - Remove from wishlist per item
 *   - Empty state with CTA to browse products
 *   - Skeleton loading
 */
export default function WishlistPage() {
  const [page, setPage] = useState(1);

  const {
    items,
    meta,
    isLoading,
    isError,
    isMutating,
    handleRemove,
  } = useWishlist({ page });

  const { handleAddToCart, isMutating: isCartMutating } = useCart();

  const handlePageChange = (newPage) => {
    setPage(newPage);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  return (
    <div className="max-w-5xl">

      {/* ── Page Header ─────────────────────────────────────────────────── */}
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-1">
          <Heart size={20} className="text-primary" />
          <h1 className="text-xl font-bold text-dark">My Wishlist</h1>
        </div>
        <p className="text-sm text-muted">
          Products you have saved for later.
        </p>
      </div>

      {/* ── Loading skeleton ─────────────────────────────────────────────── */}
      {isLoading && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((n) => (
            <div
              key={n}
              className="h-64 bg-gray-100 rounded-2xl animate-pulse"
            />
          ))}
        </div>
      )}

      {/* ── Error ────────────────────────────────────────────────────────── */}
      {isError && !isLoading && (
        <div className="flex flex-col items-center py-16 text-center">
          <p className="text-sm font-semibold text-gray-700 mb-1">
            Failed to load wishlist
          </p>
          <p className="text-xs text-muted">
            Please refresh the page and try again.
          </p>
        </div>
      )}

      {/* ── Empty state ──────────────────────────────────────────────────── */}
      {!isLoading && !isError && items.length === 0 && (
        <div className="flex flex-col items-center py-20 text-center">
          <div className="w-20 h-20 rounded-full bg-gray-50 border
                          border-gray-200 flex items-center justify-center
                          mb-5">
            <PackageOpen size={32} className="text-gray-300" strokeWidth={1.5} />
          </div>
          <h2 className="text-base font-bold text-gray-800 mb-1">
            Your wishlist is empty
          </h2>
          <p className="text-sm text-muted mb-6 max-w-xs">
            Save products you love by clicking the heart icon on any
            product card.
          </p>
          <Link
            to="/product"
            className="inline-flex items-center gap-2 bg-primary text-white
                       text-sm font-semibold px-5 py-2.5 rounded-xl
                       hover:bg-red-700 transition"
          >
            Browse Products
            <ArrowRight size={15} />
          </Link>
        </div>
      )}

      {/* ── Wishlist grid ────────────────────────────────────────────────── */}
      {!isLoading && !isError && items.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map((item) => (
              <WishlistCard
                key={item.id}
                item={item}
                isRemoving={isMutating(item.product_id)}
                isAddingToCart={isCartMutating}
                onRemove={() => handleRemove(item.product_id)}
                onAddToCart={() => handleAddToCart(item.product_id, 1)}
              />
            ))}
          </div>

          {/* ── Pagination ─────────────────────────────────────────────── */}
          {meta && meta.total_pages > 1 && (
            <div className="mt-8">
              <Pagination
                currentPage={meta.page}
                totalPages={meta.total_pages}
                hasNext={meta.has_next}
                hasPrevious={meta.has_previous}
                onPageChange={handlePageChange}
              />
            </div>
          )}
        </>
      )}

    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// WishlistCard — single wishlist item card
//
// Shape from WishlistItemSerializer:
//   id, product_id, product_name, product_slug,
//   product_price, product_in_stock, created_at, updated_at
// ─────────────────────────────────────────────────────────────────────────────
function WishlistCard({ item, isRemoving, isAddingToCart, onRemove, onAddToCart }) {
  return (
    <div className="group bg-white border border-gray-200 rounded-2xl
                    overflow-hidden hover:shadow-md hover:border-gray-300
                    transition-all duration-200">

      {/* ── Product image area ─────────────────────────────────────────── */}
      <Link to={`/product/${item.product_slug}`}>
        <div className="relative h-44 bg-gray-50 flex items-center
                        justify-center overflow-hidden">

          {/* ── Product image area ─────────────────────────────────────────── */}
<Link to={`/product/${item.product_slug}`}>
  <div className="relative h-44 bg-gray-50 flex items-center
                  justify-center overflow-hidden">

    {item.product_image ? (
      <img
        src={item.product_image}
        alt={item.product_name}
        className="w-full h-full object-contain p-4
                   group-hover:scale-105 transition-transform
                   duration-300"
      />
    ) : (
      <div className="flex flex-col items-center gap-2 text-gray-200">
        <Heart size={40} strokeWidth={1} />
      </div>
    )}

    {/* Stock badge */}
    {!item.product_in_stock && (
      <div className="absolute top-3 left-3 bg-gray-800/80 text-white
                      text-xs font-semibold px-2.5 py-1 rounded-lg">
        Out of Stock
      </div>
    )}

    

  </div>
</Link>
          {/* Product image requires navigating to detail page         */}
          <div className="flex flex-col items-center gap-2 text-gray-200">
            <Heart size={40} strokeWidth={1} />
          </div>

          {/* Stock badge */}
          {!item.product_in_stock && (
            <div className="absolute top-3 left-3 bg-gray-800/80 text-white
                            text-xs font-semibold px-2.5 py-1 rounded-lg">
              Out of Stock
            </div>
          )}

          {/* Remove button — top right */}
          <button
            onClick={(e) => {
              e.preventDefault();
              onRemove();
            }}
            disabled={isRemoving}
            className="absolute top-3 right-3 w-8 h-8 rounded-full
                       bg-white border border-gray-200 flex items-center
                       justify-center opacity-0 group-hover:opacity-100
                       hover:border-red-300 hover:text-primary transition-all
                       disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Remove from wishlist"
          >
            {isRemoving ? (
              <span className="w-3 h-3 border-2 border-gray-300
                               border-t-primary rounded-full animate-spin" />
            ) : (
              <Trash2 size={13} className="text-gray-400
                                           group-hover:text-primary" />
            )}
          </button>

        </div>
      </Link>

      {/* ── Card body ──────────────────────────────────────────────────── */}
      <div className="p-4">

        {/* Product name */}
        <Link
          to={`/product/${item.product_slug}`}
          className="block text-sm font-semibold text-dark hover:text-primary
                     transition line-clamp-2 mb-3 min-h-10"
        >
          {item.product_name}
        </Link>

        {/* Price */}
        <p className="text-base font-black text-dark mb-4">
          Rs.{" "}
          {parseFloat(item.product_price).toLocaleString("en-PK", {
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
          })}
        </p>

        {/* Actions row */}
        <div className="flex items-center gap-2">

          {/* Add to cart */}
          <button
            onClick={onAddToCart}
            disabled={!item.product_in_stock || isAddingToCart}
            className="flex-1 flex items-center justify-center gap-1.5
                       bg-primary text-white text-xs font-bold py-2.5
                       rounded-xl hover:bg-red-700 transition
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ShoppingCart size={13} />
            {item.product_in_stock ? "Add to Cart" : "Out of Stock"}
          </button>

          {/* Remove — visible always on mobile, hover on desktop */}
          <button
            onClick={onRemove}
            disabled={isRemoving}
            className="w-9 h-9 flex items-center justify-center rounded-xl
                       border border-gray-200 hover:border-red-300
                       hover:text-primary transition
                       disabled:opacity-50 disabled:cursor-not-allowed
                       lg:hidden"
            aria-label="Remove from wishlist"
          >
            <Trash2 size={14} className="text-gray-400" />
          </button>

        </div>

      </div>
    </div>
  );
}