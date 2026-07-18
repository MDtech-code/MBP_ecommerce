// src/widgets/product/ui/ProductGrid.jsx
import { ProductCard }       from "@entities/product"
import { ProductCardAction } from "@features/cart"

/**
 * ProductGrid — composes ProductCard (entity) with
 * ProductCardAction (feature) via the action prop slot.
 *
 * Widget layer is the correct place for this composition.
 * Neither entity nor feature knows the other exists.
 */
export default function ProductGrid({ products = [], isLoading = false }) {

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
        <ProductCard
          key={product.id}
          product={product}
          action={
            // Widget composes entity + feature here.
            // ProductCard does not know what this is.
            // ProductCardAction does not know which card it is in.
            <ProductCardAction
              productId={product.id}
              isInStock={product.is_in_stock}
            />
          }
        />
      ))}
    </div>
  );
}
