// components/product-detail/RelatedProducts.jsx
import { Star, ChevronRight } from "lucide-react";

export default function RelatedProducts({ products }) {
  return (
    <div className="mt-10">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-black text-gray-900">RELATED PRODUCTS</h2>
        <button className="text-primary text-sm font-semibold flex items-center gap-1 hover:underline">
          View All <ChevronRight size={16} />
        </button>
      </div>

      {/* Products Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {products.map((product) => (
          <div
            key={product.id}
            className="bg-white rounded-xl p-4 hover:shadow-md transition cursor-pointer"
          >
            {/* Image */}
            <div className="h-32 flex items-center justify-center mb-3">
              <img
                src={product.image}
                alt={product.name}
                className="max-h-full object-contain"
              />
            </div>

            {/* Name */}
            <h4 className="text-sm font-bold text-gray-900">{product.name}</h4>

            {/* Price */}
            <p className="text-primary font-black mt-1 text-sm">
              Rs. {product.price.toLocaleString()}
            </p>

            {/* Rating */}
            <div className="flex items-center gap-1 mt-1">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star
                  key={i}
                  size={12}
                  className={
                    i <= Math.floor(product.rating)
                      ? "fill-yellow-400 text-yellow-400"
                      : "fill-gray-200 text-gray-200"
                  }
                />
              ))}
              <span className="text-xs text-gray-400">({product.reviews})</span>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
}