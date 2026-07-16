// src/components/products/ProductGrid.jsx
import ProductCard from "../../../entities/product/ui/ProductCard";

/**
 * ProductGrid — pure pass-through, unchanged structure.
 * products[] now uses real backend shape via ProductCard.
 */
export default function ProductGrid({ products = [], isLoading = false }) {

  // Loading skeleton
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {[...Array(12)].map((_, i) => (
          <div key={i} className="bg-white rounded-xl p-4 animate-pulse">
            <div className="h-52 bg-gray-100 rounded-lg mb-4" />
            <div className="h-4 bg-gray-100 rounded mb-2" />
            <div className="h-3 bg-gray-100 rounded w-2/3 mb-2" />
            <div className="h-3 bg-gray-100 rounded w-1/2 mb-4" />
            <div className="h-10 bg-gray-100 rounded" />
          </div>
        ))}
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center
                      py-24 text-center">
        <p className="text-4xl mb-4">🔧</p>
        <p className="font-bold text-gray-700 text-lg">No products found</p>
        <p className="text-sm text-gray-500 mt-1">
          Try adjusting your filters or search term
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {products.map((product) => (
        <ProductCard key={product.id} product={product} />
      ))}
    </div>
  );
}
