// src/components/product-detail/RelatedProducts.jsx
import { Star, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

/**
 * RelatedProducts
 *
 * Props:
 *   products: Array — product.related_products from backend
 *             shape: ProductListSerializer (same as list endpoint)
 *
 * Backend fields used:
 *   slug          → Link to /product/:slug
 *   primary_image → product image (can be null)
 *   name          → product title
 *   current_price → display price
 *   has_discount  → crossed price control
 *   price         → original price when discounted
 *
 * NOT in backend:
 *   rating  → dummy stars
 *   reviews → dummy count
 */

const DUMMY_RATING  = 4;
const FALLBACK_IMG  = "/placeholder-part.png";

export default function RelatedProducts({ products = [] }) {

  if (products.length === 0) return null;

  return (
    <div className="mt-4">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-lg font-black text-gray-900">
          RELATED PRODUCTS
        </h2>
        <Link
          to="/product"
          className="text-primary text-sm font-semibold
                     flex items-center gap-1 hover:underline"
        >
          View All <ChevronRight size={16} />
        </Link>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-2 gap-3">
        {products.map((product) => (
          <Link
            key={product.id}
            to={`/product/${product.slug}`}
            className="bg-gray-50 rounded-xl p-3 hover:shadow-md
                       transition cursor-pointer group block border
                       border-gray-100 hover:border-gray-200"
          >
            {/* Image */}
            <div className="h-28 flex items-center justify-center mb-3
                            bg-white rounded-lg">
              <img
                src={product.primary_image || FALLBACK_IMG}
                alt={product.name}
                className="max-h-full object-contain
                           group-hover:scale-105 transition duration-200"
                onError={(e) => { e.currentTarget.src = FALLBACK_IMG; }}
              />
            </div>

            {/* Name */}
            <h4 className="text-xs font-bold text-gray-900 line-clamp-2
                           leading-tight">
              {product.name}
            </h4>

            {/* Price */}
            <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
              <p className="text-primary font-black text-sm">
                Rs. {parseFloat(product.current_price).toLocaleString()}
              </p>
              {product.has_discount && (
                <p className="text-gray-400 line-through text-xs">
                  Rs. {parseFloat(product.price).toLocaleString()}
                </p>
              )}
            </div>

            {/* Rating — placeholder */}
            <div className="flex items-center gap-0.5 mt-1.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star
                  key={i}
                  size={11}
                  className={
                    i <= DUMMY_RATING
                      ? "fill-yellow-400 text-yellow-400"
                      : "fill-gray-200 text-gray-200"
                  }
                />
              ))}
            </div>
          </Link>
        ))}
      </div>

    </div>
  );
}
