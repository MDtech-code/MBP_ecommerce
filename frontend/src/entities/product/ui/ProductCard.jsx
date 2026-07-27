// src/entities/product/ui/ProductCard.jsx
import { Star } from "lucide-react";
import { Link } from "react-router-dom";
import { getMediaUrl } from "@shared/lib/media"; 
const DUMMY_RATING  = 4;
const DUMMY_REVIEWS = 0;
const FALLBACK_IMG  = "/placeholder-part.png";

/**
 * ProductCard — pure display entity component.
 *
 * Knows nothing about cart or any feature.
 * Receives action prop slot — parent injects feature buttons.
 *
 * Props:
 *   product → backend product list item shape
 *   action  → JSX injected by parent (ProductCardAction, etc.)
 */
export default function ProductCard({ product, action }) {
  const {
    slug,
    name,
    primary_image,
    primary_bike,
    has_discount,
    discount_percentage,
    current_price,
    price,
  } = product;

   const imageUrl = getMediaUrl(primary_image) || FALLBACK_IMG;

  return (
    <Link
      to={`/product/${slug}`}
      className="bg-white rounded-xl p-4 hover:shadow-lg transition
                 group block"
    >
      {/* Image */}
      <div className="relative h-52 flex items-center justify-center mb-4">
        {has_discount && discount_percentage > 0 && (
          <span className="absolute top-0 left-0 bg-primary text-white
                           text-xs font-bold px-2 py-1 rounded-md z-10">
            -{discount_percentage}%
          </span>
        )}
        <img
          src={imageUrl}
          alt={name}
          className="max-h-full object-contain group-hover:scale-105
                     transition duration-300"
          onError={(e) => { e.currentTarget.src = FALLBACK_IMG; }}
        />
      </div>

      {/* Name */}
      <h3 className="font-bold text-sm text-gray-900 line-clamp-2">
        {name}
      </h3>

      {/* Bike compatibility */}
      <p className="text-xs text-gray-500 mt-1">{primary_bike}</p>

      {/* Rating placeholder */}
      <div className="flex items-center gap-1 mt-2">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={13}
            className={
              star <= DUMMY_RATING
                ? "fill-yellow-400 text-yellow-400"
                : "fill-gray-200 text-gray-200"
            }
          />
        ))}
        <span className="text-xs text-gray-500 ml-1">({DUMMY_REVIEWS})</span>
      </div>

      {/* Price */}
      <div className="flex items-center gap-2 mt-2">
        <span className="text-primary font-black text-base">
          Rs. {parseFloat(current_price).toLocaleString()}
        </span>
        {has_discount && (
          <span className="text-gray-400 line-through text-sm">
            Rs. {parseFloat(price).toLocaleString()}
          </span>
        )}
      </div>

      {/*
        Action slot — injected by parent.
        ProductCard does not know what renders here.
        Renders nothing if no action passed.
      */}
      {action && <div className="mt-4">{action}</div>}

    </Link>
  );
}
