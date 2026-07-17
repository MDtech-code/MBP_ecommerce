// src/pages/products/ProductDetail.jsx
import { Link } from "react-router-dom";

import { useProductDetail } from "../model/useProductDetail";
import { Header }         from "@widgets/header"
import { ProductGallery } from "@entities/product"
import { ProductInfo }    from "@entities/product"
import { ProductActions } from "@entities/product"
import { ProductTrust }   from "@entities/product"
import { ProductTabs }    from "@entities/product"
import { RelatedProducts } from "@widgets/product"

/**
 * ProductDetail page — Layer 4 (dumb).
 *
 * Zero API calls here.
 * Zero business logic here.
 * Receives everything from useProductDetail() and passes down.
 *
 * URL: /product/:slug
 * slug is read inside useProductDetail via useParams()
 */
export default function ProductDetail() {
  const {
    product,
    isLoading,
    isError,
    isNotFound,
    errorMessage,
    images,
    breadcrumb,
    relatedProducts,
    isInStock,
    stock,
  } = useProductDetail();

  // ── Loading skeleton ────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <>
        <Header />
        <div className="bg-gray-50 min-h-screen">
          <div className="max-w-7xl mx-auto px-6 py-6">

            {/* Breadcrumb skeleton */}
            <div className="flex gap-2 mb-6">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-4 w-16 bg-gray-200
                                        rounded animate-pulse" />
              ))}
            </div>

            <div className="grid lg:grid-cols-2 gap-8">
              {/* Gallery skeleton */}
              <div className="bg-white border border-gray-200 rounded-xl p-6
                              animate-pulse">
                <div className="h-80 bg-gray-100 rounded-lg mb-6" />
                <div className="flex gap-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="w-20 h-20 bg-gray-100 rounded-lg" />
                  ))}
                </div>
              </div>

              {/* Info skeleton */}
              <div className="space-y-4 animate-pulse">
                <div className="h-8 bg-gray-200 rounded w-3/4" />
                <div className="h-4 bg-gray-200 rounded w-1/4" />
                <div className="h-4 bg-gray-200 rounded w-1/3" />
                <div className="h-10 bg-gray-200 rounded w-1/2 mt-6" />
                <div className="h-4 bg-gray-200 rounded w-1/4" />
                <div className="flex gap-3 mt-6">
                  <div className="h-14 bg-gray-200 rounded flex-1" />
                  <div className="h-14 bg-gray-200 rounded flex-1" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    );
  }

  // ── 404 ─────────────────────────────────────────────────────────────────────
  if (isNotFound) {
    return (
      <>
        <Header />
        <div className="bg-gray-50 min-h-screen flex items-center
                        justify-center">
          <div className="text-center py-24">
            <p className="text-6xl mb-4">🔧</p>
            <h1 className="text-2xl font-black text-gray-900 mb-2">
              Product Not Found
            </h1>
            <p className="text-gray-500 text-sm mb-6">
              The product you are looking for does not exist or
              has been removed.
            </p>
            <Link
              to="/product"
              className="bg-primary text-white px-6 py-3 rounded-lg
                         font-bold text-sm hover:bg-red-700 transition"
            >
              Browse All Products
            </Link>
          </div>
        </div>
      </>
    );
  }

  // ── Generic error ────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <>
        <Header />
        <div className="bg-gray-50 min-h-screen flex items-center
                        justify-center">
          <div className="text-center py-24">
            <p className="text-4xl mb-4">⚠️</p>
            <p className="font-bold text-gray-700 mb-2">
              Failed to load product
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
      <Header />

      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Breadcrumb — built from category.parent_name + category.name */}
          <nav className="text-sm text-gray-500 mb-6 flex items-center
                          gap-2 flex-wrap">
            {breadcrumb.map((crumb, index) => (
              <span key={index} className="flex items-center gap-2">
                {index > 0 && <span>›</span>}
                {crumb.to ? (
                  <Link
                    to={crumb.to}
                    className="hover:text-primary transition-colors"
                  >
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-gray-800 font-medium
                                   line-clamp-1 max-w-xs">
                    {crumb.label}
                  </span>
                )}
              </span>
            ))}
          </nav>

          {/* Top Section — Gallery + Info */}
          <div className="grid lg:grid-cols-2 gap-8">

            {/* Left — Gallery */}
            <ProductGallery images={images} />

            {/* Right — Info + Actions + Trust */}
            <div>
              <ProductInfo product={product} />
              <ProductActions
                isInStock={isInStock}
                stock={stock}
              />
              <ProductTrust />
            </div>

          </div>

          {/* Bottom Section — Tabs + Related */}
          <div className="grid lg:grid-cols-2 gap-8 mt-4">

            {/* Left — Tabs */}
            <div className="bg-white rounded-xl p-6">
              <ProductTabs product={product} />
            </div>

            {/* Right — Related Products */}
            <div className="bg-white rounded-xl p-6">
              <RelatedProducts products={relatedProducts} />
            </div>

          </div>

        </div>
      </div>
    </>
  );
}
