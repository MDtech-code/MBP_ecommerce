// components/product-detail/ProductInfo.jsx
import { Star, CheckCircle2 } from "lucide-react";

export default function ProductInfo({ product }) {
  return (
    <div>

      {/* Name */}
      <h1 className="text-2xl font-black text-gray-900">
        {product.name}
      </h1>

      {/* Brand */}
      <p className="text-primary font-semibold mt-1">
        {product.brand}
      </p>

      {/* Rating */}
      <div className="flex items-center gap-2 mt-3">
        <div className="flex items-center">
          {[1, 2, 3, 4, 5].map((i) => (
            <Star
              key={i}
              size={16}
              className={
                i <= Math.floor(product.rating)
                  ? "fill-yellow-400 text-yellow-400"
                  : "fill-gray-200 text-gray-200"
              }
            />
          ))}
        </div>
        <span className="text-sm text-gray-600">
          {product.rating} ({product.reviews} Reviews)
        </span>
      </div>

      {/* Price */}
      <div className="flex items-center gap-3 mt-5">
        <span className="text-primary text-3xl font-black">
          Rs. {product.price.toLocaleString()}
        </span>
        <span className="line-through text-gray-400 text-lg">
          Rs. {product.oldPrice.toLocaleString()}
        </span>
        <span className="bg-primary text-white px-3 py-1 rounded-md text-sm font-bold">
          -{product.discount}
        </span>
      </div>

      {/* Tax */}
      <p className="text-xs text-gray-500 mt-1">Inclusive of all taxes</p>

      {/* Availability */}
      <div className="flex items-center gap-2 mt-4">
        <span className="text-sm font-semibold text-gray-700">Availability:</span>
        {product.stock ? (
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle2 size={15} />
            <span className="text-sm font-semibold">In Stock</span>
          </div>
        ) : (
          <span className="text-sm font-semibold text-red-500">Out of Stock</span>
        )}
      </div>

      {/* Compatible Bikes */}
      <div className="mt-4">
        <p className="text-sm font-bold text-gray-800 mb-2">Compatible Bikes:</p>
        <div className="flex gap-2 flex-wrap">
          {product.compatibility.map((item) => (
            <span
              key={item}
              className="border border-gray-300 px-4 py-1.5 rounded-md text-sm text-gray-700"
            >
              {item}
            </span>
          ))}
        </div>
      </div>

    </div>
  );
}