// src/components/product-detail/ProductInfo.jsx
import { Star, CheckCircle2, XCircle } from "lucide-react";

/**
 * ProductInfo
 *
 * Props:
 *   product: full backend product detail object
 *
 * Backend fields used:
 *   name                → product title
 *   brand.name          → brand label in red
 *   has_discount        → controls crossed price display
 *   discount_percentage → badge "-11%"
 *   current_price       → main displayed price
 *   price               → original price (crossed out)
 *   is_in_stock         → availability badge
 *   stock               → "Only X left" when low stock
 *   compatible_bikes[]  → chip tags using display_name
 *   sku                 → shown under title
 *
 * NOT in backend (reviews not built):
 *   rating  → DUMMY_RATING hardcoded
 *   reviews → DUMMY_REVIEWS hardcoded
 */

const DUMMY_RATING  = 4;
const DUMMY_REVIEWS = 0;
const LOW_STOCK_THRESHOLD = 5;

export default function ProductInfo({ product }) {
  if (!product) return null;

  const {
    name,
    sku,
    brand,
    has_discount,
    discount_percentage,
    current_price,
    price,
    is_in_stock,
    stock,
    compatible_bikes = [],
  } = product;

  return (
    <div>

      {/* Name */}
      <h1 className="text-2xl font-black text-gray-900 leading-tight">
        {name}
      </h1>

      {/* Brand + SKU row */}
      <div className="flex items-center gap-3 mt-1">
        {brand && (
          <p className="text-primary font-semibold text-sm">
            {brand.name}
          </p>
        )}
        <span className="text-gray-300">|</span>
        <p className="text-xs text-gray-400">
          SKU: {sku}
        </p>
      </div>

      {/* Rating — placeholder until reviews ship */}
      <div className="flex items-center gap-2 mt-3">
        <div className="flex items-center">
          {[1, 2, 3, 4, 5].map((i) => (
            <Star
              key={i}
              size={16}
              className={
                i <= DUMMY_RATING
                  ? "fill-yellow-400 text-yellow-400"
                  : "fill-gray-200 text-gray-200"
              }
            />
          ))}
        </div>
        <span className="text-sm text-gray-500">
          {DUMMY_RATING}.0
          {DUMMY_REVIEWS > 0
            ? ` (${DUMMY_REVIEWS} Reviews)`
            : " (No reviews yet)"
          }
        </span>
      </div>

      {/* Price block */}
      <div className="flex items-center gap-3 mt-5">
        <span className="text-primary text-3xl font-black">
          Rs. {parseFloat(current_price).toLocaleString()}
        </span>

        {has_discount && (
          <>
            <span className="line-through text-gray-400 text-lg">
              Rs. {parseFloat(price).toLocaleString()}
            </span>
            <span className="bg-primary text-white px-3 py-1
                             rounded-md text-sm font-bold">
              -{discount_percentage}%
            </span>
          </>
        )}
      </div>

      {/* Tax note */}
      <p className="text-xs text-gray-500 mt-1">
        Inclusive of all taxes
      </p>

      {/* Availability */}
      <div className="flex items-center gap-2 mt-4">
        <span className="text-sm font-semibold text-gray-700">
          Availability:
        </span>
        {is_in_stock ? (
          <div className="flex items-center gap-1 text-green-600">
            <CheckCircle2 size={15} />
            <span className="text-sm font-semibold">In Stock</span>
            {stock <= LOW_STOCK_THRESHOLD && stock > 0 && (
              <span className="text-xs text-orange-500 font-semibold ml-1">
                (Only {stock} left)
              </span>
            )}
          </div>
        ) : (
          <div className="flex items-center gap-1 text-red-500">
            <XCircle size={15} />
            <span className="text-sm font-semibold">Out of Stock</span>
          </div>
        )}
      </div>

      {/* Compatible Bikes */}
      {compatible_bikes.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-bold text-gray-800 mb-2">
            Compatible Bikes:
          </p>
          <div className="flex gap-2 flex-wrap">
            {compatible_bikes.map((bike) => (
              <span
                key={bike.id}
                className="border border-gray-300 px-4 py-1.5
                           rounded-md text-sm text-gray-700"
              >
                {bike.display_name}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Universal badge — when no compatible bikes */}
      {compatible_bikes.length === 0 && (
        <div className="mt-4">
          <p className="text-sm font-bold text-gray-800 mb-2">
            Compatibility:
          </p>
          <span className="border border-green-300 bg-green-50 text-green-700
                           px-4 py-1.5 rounded-md text-sm font-semibold">
            Universal — Fits All Bikes
          </span>
        </div>
      )}

    </div>
  );
}
// // components/product-detail/ProductInfo.jsx
// import { Star, CheckCircle2 } from "lucide-react";

// export default function ProductInfo({ product }) {
//   return (
//     <div>

//       {/* Name */}
//       <h1 className="text-2xl font-black text-gray-900">
//         {product.name}
//       </h1>

//       {/* Brand */}
//       <p className="text-primary font-semibold mt-1">
//         {product.brand}
//       </p>

//       {/* Rating */}
//       <div className="flex items-center gap-2 mt-3">
//         <div className="flex items-center">
//           {[1, 2, 3, 4, 5].map((i) => (
//             <Star
//               key={i}
//               size={16}
//               className={
//                 i <= Math.floor(product.rating)
//                   ? "fill-yellow-400 text-yellow-400"
//                   : "fill-gray-200 text-gray-200"
//               }
//             />
//           ))}
//         </div>
//         <span className="text-sm text-gray-600">
//           {product.rating} ({product.reviews} Reviews)
//         </span>
//       </div>

//       {/* Price */}
//       <div className="flex items-center gap-3 mt-5">
//         <span className="text-primary text-3xl font-black">
//           Rs. {product.price.toLocaleString()}
//         </span>
//         <span className="line-through text-gray-400 text-lg">
//           Rs. {product.oldPrice.toLocaleString()}
//         </span>
//         <span className="bg-primary text-white px-3 py-1 rounded-md text-sm font-bold">
//           -{product.discount}
//         </span>
//       </div>

//       {/* Tax */}
//       <p className="text-xs text-gray-500 mt-1">Inclusive of all taxes</p>

//       {/* Availability */}
//       <div className="flex items-center gap-2 mt-4">
//         <span className="text-sm font-semibold text-gray-700">Availability:</span>
//         {product.stock ? (
//           <div className="flex items-center gap-1 text-green-600">
//             <CheckCircle2 size={15} />
//             <span className="text-sm font-semibold">In Stock</span>
//           </div>
//         ) : (
//           <span className="text-sm font-semibold text-red-500">Out of Stock</span>
//         )}
//       </div>

//       {/* Compatible Bikes */}
//       <div className="mt-4">
//         <p className="text-sm font-bold text-gray-800 mb-2">Compatible Bikes:</p>
//         <div className="flex gap-2 flex-wrap">
//           {product.compatibility.map((item) => (
//             <span
//               key={item}
//               className="border border-gray-300 px-4 py-1.5 rounded-md text-sm text-gray-700"
//             >
//               {item}
//             </span>
//           ))}
//         </div>
//       </div>

//     </div>
//   );
// }