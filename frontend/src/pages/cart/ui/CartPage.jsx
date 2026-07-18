  // src/pages/cart/CartPage.jsx
import { Link } from "react-router-dom";
import {CartList} from "@widgets/cart";
import {CartSummary} from "@widgets/cart";
import {CartTrust} from "@entities/cart";
import {YouMayAlsoLike} from "@widgets/cart";
import { useCart } from "@features/cart";
import { useProducts } from "@entities/product"

/**
 * CartPage — Layer 4 (dumb).
 *
 * Zero API calls here.
 * Zero business logic here.
 * Destructures everything from useCart() and passes down.
 *
 * YouMayAlsoLike:
 *   Uses useProducts with featured=true to suggest products.
 *   Shown only when cart is not empty.
 *   page_size=4 — just enough for the 4-column grid.
 */
export default function CartPage() {
  const {
    items,
    totalItems,
    totalPrice,
    isEmpty,
    isLoading,
    isError,
    isMutating,
    errorMessage,
    mutationErrorMessage,
    handleIncrease,
    handleDecrease,
    handleRemove,
    handleClearCart,
  } = useCart();

  // Suggested products — featured items for "You May Also Like"
  const { data: suggestedData } = useProducts({
    featured: true,
    page_size: 4,
  });
  const suggestedProducts = suggestedData?.products ?? [];

  // ── Loading skeleton ──────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <>
        
        <div className="bg-gray-50 min-h-screen">
          <div className="max-w-7xl mx-auto px-6 py-6">
            <div className="grid lg:grid-cols-4 gap-6">
              <div className="lg:col-span-3 bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex gap-4 py-5 border-b border-gray-100">
                    <div className="w-20 h-20 bg-gray-100 rounded-lg shrink-0" />
                    <div className="flex-1 space-y-2">
                      <div className="h-4 bg-gray-100 rounded w-3/4" />
                      <div className="h-3 bg-gray-100 rounded w-1/2" />
                    </div>
                  </div>
                ))}
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse h-64" />
            </div>
          </div>
        </div>
      </>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (isError) {
    return (
      <>
        
        <div className="bg-gray-50 min-h-screen flex items-center justify-center">
          <div className="text-center py-24">
            <p className="text-4xl mb-4">⚠️</p>
            <p className="font-bold text-gray-700 mb-2">
              Failed to load cart
            </p>
            <p className="text-sm text-gray-500 mb-6">
              {errorMessage ?? "Something went wrong. Please try again."}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="bg-primary text-white px-6 py-3 rounded-lg
                         font-bold text-sm hover:bg-red-700 transition"
            >
              Try Again
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      

      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Breadcrumb */}
          <nav className="text-sm text-gray-500 mb-5 flex items-center gap-2">
            <Link to="/" className="hover:text-primary transition-colors">
              Home
            </Link>
            <span>›</span>
            <span className="text-gray-800">Your Cart</span>
          </nav>

          {/* Title */}
          <h1 className="text-2xl font-black text-gray-900 mb-6">
            Your Cart{" "}
            <span className="text-gray-400 font-bold">
              ({totalItems} Items)
            </span>
          </h1>

          {/* Mutation error banner */}
          {mutationErrorMessage && (
            <div className="bg-red-50 border border-red-200 rounded-xl
                            px-4 py-3 mb-6 text-sm text-red-600">
              {mutationErrorMessage}
            </div>
          )}

          {/* Empty cart state */}
          {isEmpty ? (
            <div className="flex flex-col items-center justify-center
                            py-24 text-center bg-white rounded-xl
                            border border-gray-200">
              <p className="text-5xl mb-4">🛒</p>
              <p className="font-bold text-gray-700 text-lg mb-2">
                Your cart is empty
              </p>
              <p className="text-sm text-gray-500 mb-6">
                Add products to your cart to see them here
              </p>
              <Link
                to="/product"
                className="bg-primary text-white px-6 py-3 rounded-lg
                           font-bold text-sm hover:bg-red-700 transition"
              >
                Browse Products
              </Link>
            </div>
          ) : (
            <>
              {/* Main Grid */}
              <div className="grid lg:grid-cols-4 gap-6">

                {/* Cart List */}
                <div className="lg:col-span-3">
                  <CartList
                    items={items}
                    isMutating={isMutating}
                    onIncrease={handleIncrease}
                    onDecrease={handleDecrease}
                    onRemove={handleRemove}
                    onClearCart={handleClearCart}
                  />
                </div>

                {/* Summary */}
                <div>
                  <CartSummary
                    totalPrice={totalPrice}
                    totalItems={totalItems}
                    isMutating={isMutating}
                  />
                </div>

              </div>

              {/* Trust Badges */}
              <CartTrust />

              {/* You May Also Like */}
              {suggestedProducts.length > 0 && (
                <YouMayAlsoLike products={suggestedProducts} />
              )}
            </>
          )}

        </div>
      </div>
    </>
  );
}
 