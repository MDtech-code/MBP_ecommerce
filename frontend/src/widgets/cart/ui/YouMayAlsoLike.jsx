// src/components/cart/YouMayAlsoLike.jsx
// The products shape from useProducts is ProductListSerializer
// which has: slug, name, primary_image, current_price, has_discount, price
// NOT: image, bike, rating, reviews, oldPrice, discount
import { Link } from "react-router-dom";
// Update the component to use real backend fields:
import { getMediaUrl } from "@shared/lib/media"; 
import { IMAGES} from "@shared/assets";
const FALLBACK_IMG  = IMAGES.PLACEHOLDER;
export default function YouMayAlsoLike({ products }) {
  return (
    <div className="mt-10">
      <h2 className="text-xl font-black text-gray-900 mb-6">
        You May Also Like
      </h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {products.map((product) => (
          <Link
            key={product.id}
            to={`/product/${product.slug}`}
            className="bg-white rounded-xl p-4 hover:shadow-md transition block"
          >
            {/* Image */}
            <div className="relative h-36 flex items-center justify-center mb-3">
              {product.has_discount && product.discount_percentage > 0 && (
                <span className="absolute top-0 left-0 bg-primary text-white
                                 text-xs font-bold px-2 py-1 rounded-md">
                  -{product.discount_percentage}%
                </span>
              )}
              <img
                src={getMediaUrl(product.primary_image) || FALLBACK_IMG}
                alt={product.name}
                className="max-h-full object-contain"
                onError={(e) => { e.currentTarget.src = "/placeholder-part.png"; }}
              />
            </div>

            {/* Info */}
            <h4 className="font-bold text-sm text-gray-900 line-clamp-2">
              {product.name}
            </h4>
            <p className="text-xs text-gray-500 mt-0.5">{product.primary_bike}</p>

            {/* Price */}
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-primary font-black text-sm">
                Rs. {parseFloat(product.current_price).toLocaleString()}
              </span>
              {product.has_discount && (
                <span className="text-gray-400 line-through text-xs">
                  Rs. {parseFloat(product.price).toLocaleString()}
                </span>
              )}
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
