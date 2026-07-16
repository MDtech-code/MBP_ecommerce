// src/pages/products/ProductListing.jsx
import Header from "../../../widgets/header/ui/Header";
import ProductSidebar from "../../../widgets/sidebar/ui/ProductSidebar";
import ProductGrid    from "../../../widgets/product/ui/ProductGrid";
import ProductToolbar from "../../../features/filtering/ui/ProductToolbar";
import Pagination     from "../../../shared/ui/Pagination/Pagination";
import { useProductList } from "../model/useProductList";
import { Link } from "react-router-dom";

/**
 * ProductListing page — Layer 4 (dumb).
 *
 * Zero API calls here.
 * Zero business logic here.
 * Destructures everything from useProductList and passes down.
 *
 * URL drives all state:
 *   /product                          → all products, page 1
 *   /product?category=brake-system    → filtered by category
 *   /product?brand=honda              → filtered by brand
 *   /product?bike=1                   → compatibility filter
 *   /product?sort=price_asc&page=2    → sorted + paginated
 */
export default function ProductListing() {
  const {
    products,
    meta,
    isLoading,
    isFetching,
    isError,
    errorMessage,
    activeFilters,
    setCategory,
    setBrand,
    setBikeModel,
    setMinPrice,
    setMaxPrice,
    setSort,
    setPage,
    clearFilters,
  } = useProductList();

  // ── Breadcrumb label ────────────────────────────────────────────────────────
  const breadcrumbLabel = activeFilters.category
    ? activeFilters.category
        .split("-")
        .map((w) => w[0].toUpperCase() + w.slice(1))
        .join(" ")
    : "All Products";

  return (
    <>
      <Header />

      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-7xl mx-auto px-6 py-6">

          {/* Breadcrumb */}
          <nav className="text-sm text-gray-500 mb-6 flex items-center gap-2">
            <Link to="/" className="hover:text-primary transition-colors">
              Home
            </Link>
            <span>›</span>
            <span className="text-gray-800 font-medium">
              {breadcrumbLabel}
            </span>
          </nav>

          {/* Error state */}
          {isError && (
            <div className="bg-red-50 border border-red-200 rounded-xl
                            px-4 py-3 mb-6 text-sm text-red-600">
              {errorMessage ?? "Failed to load products. Please try again."}
            </div>
          )}

          {/* Main Layout */}
          <div className="flex gap-8">

            {/* Sidebar */}
            <aside className="w-64 shrink-0">
              <ProductSidebar
                activeFilters={activeFilters}
                setCategory={setCategory}
                setBrand={setBrand}
                setBikeModel={setBikeModel}
                setMinPrice={setMinPrice}
                setMaxPrice={setMaxPrice}
                clearFilters={clearFilters}
              />
            </aside>

            {/* Content */}
            <div className="flex-1 min-w-0">

              {/* Toolbar — shows count + sort */}
              <ProductToolbar
                meta={meta}
                activeSort={activeFilters.sort}
                onSort={setSort}
              />

              {/* Product Grid */}
              {/* isFetching (not isLoading) for background refetch during
                  filter/page changes — placeholderData keeps old data visible
                  while new data loads, so we show a subtle opacity fade
                  instead of full skeleton reload */}
              <div className={isFetching && !isLoading
                ? "opacity-60 transition-opacity duration-200"
                : ""
              }>
                <ProductGrid
                  products={products}
                  isLoading={isLoading}
                />
              </div>

              {/* Pagination */}
              <Pagination
                currentPage={meta.page ?? 1}
                totalPages={meta.total_pages ?? 1}
                hasNext={meta.has_next ?? false}
                hasPrevious={meta.has_previous ?? false}
                onPageChange={setPage}
              />

            </div>
          </div>
        </div>
      </div>
    </>
  );
}
