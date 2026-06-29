// components/cart/YouMayAlsoLike.jsx
import { Star, ShoppingCart, Heart } from "lucide-react";

export default function YouMayAlsoLike({ products }) {
  return (
    <div className="mt-10">

      <h2 className="text-xl font-black text-gray-900 mb-6">
        You May Also Like
      </h2>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {products.map((product) => (
          <div
            key={product.id}
            className="bg-white rounded-xl p-4 hover:shadow-md transition"
          >
            {/* Image */}
            <div className="relative h-36 flex items-center justify-center mb-3">
              {product.discount && (
                <span className="absolute top-0 left-0 bg-primary text-white text-xs font-bold px-2 py-1 rounded-md">
                  -{product.discount}
                </span>
              )}
              <img
                src={product.image}
                alt={product.name}
                className="max-h-full object-contain"
              />
            </div>

            {/* Info */}
            <h4 className="font-bold text-sm text-gray-900">{product.name}</h4>
            <p className="text-xs text-gray-500 mt-0.5">{product.bike}</p>

            {/* Rating */}
            <div className="flex items-center gap-1 mt-1.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star
                  key={i}
                  size={12}
                  className={
                    i <= product.rating
                      ? "fill-yellow-400 text-yellow-400"
                      : "fill-gray-200 text-gray-200"
                  }
                />
              ))}
              <span className="text-xs text-gray-400 ml-1">({product.reviews})</span>
            </div>

            {/* Price */}
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-primary font-black text-sm">
                Rs. {product.price.toLocaleString()}
              </span>
              {product.oldPrice && (
                <span className="text-gray-400 line-through text-xs">
                  Rs. {product.oldPrice.toLocaleString()}
                </span>
              )}
            </div>

            {/* Buttons */}
            <div className="flex items-center gap-2 mt-3">
              <button className="flex-1 bg-primary text-white py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-1.5 hover:bg-red-700 transition">
                <ShoppingCart size={13} />
                ADD TO CART
              </button>
              <button className="border border-gray-300 rounded-lg p-2 hover:border-gray-400 transition">
                <Heart size={13} className="text-gray-400" />
              </button>
            </div>

          </div>
        ))}
      </div>

    </div>
  );
}