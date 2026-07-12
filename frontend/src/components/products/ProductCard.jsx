// src/components/products/ProductCard.jsx
import { Star, ShoppingCart, Heart } from "lucide-react";
import { Link } from "react-router-dom";

/**
 * ProductCard — driven by real backend product list item shape.
 *
 * Backend fields used:
 *   slug               → Link to /product/:slug
 *   primary_image      → product image URL (can be null)
 *   has_discount       → controls discount badge + old price display
 *   discount_percentage → badge number e.g. "-18%"
 *   name               → product title
 *   primary_bike       → "Honda CD70" or "Universal"
 *   current_price      → price to display (already discounted)
 *   price              → original price (shown crossed when has_discount)
 *   is_in_stock        → controls Add to Cart button
 *   is_featured        → (available, not used in card UI currently)
 *
 * NOT in backend (reviews app not built yet):
 *   rating  → hardcoded 4 stars as placeholder
 *   reviews → hardcoded placeholder count
 *
 * Why dummy rating not removed:
 *   Design shows star rating on every card.
 *   Removing it breaks the card layout.
 *   When reviews app ships, replace DUMMY_RATING with product.rating.
 */

const DUMMY_RATING  = 4;
const DUMMY_REVIEWS = 0;
const FALLBACK_IMG  = "/placeholder-part.png"; // put a real placeholder in /public

export default function ProductCard({ product }) {
  const {
    slug,
    name,
    primary_image,
    primary_bike,
    has_discount,
    discount_percentage,
    current_price,
    price,
    is_in_stock,
  } = product;

  const imageUrl = primary_image || FALLBACK_IMG;

  return (
    <Link
      to={`/product/${slug}`}
      className="bg-white rounded-xl p-4 hover:shadow-lg transition
                 group block"
    >
      {/* Image Area */}
      <div className="relative h-52 flex items-center justify-center mb-4">

        {/* Discount badge */}
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

      {/* Product name */}
      <h3 className="font-bold text-sm text-gray-900 line-clamp-2">
        {name}
      </h3>

      {/* Compatible bike */}
      <p className="text-xs text-gray-500 mt-1">
        {primary_bike}
      </p>

      {/* Rating — placeholder until reviews app ships */}
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
        <span className="text-xs text-gray-500 ml-1">
          ({DUMMY_REVIEWS})
        </span>
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

      {/* Add to Cart + Heart */}
      <div className="flex items-center gap-2 mt-4">
        <button
          onClick={(e) => {
            // Prevent Link navigation when clicking Add to Cart
            e.preventDefault();
          }}
          disabled={!is_in_stock}
          className="flex-1 bg-primary text-white py-2.5 rounded-lg
                     font-bold text-sm flex items-center justify-center
                     gap-2 hover:bg-red-700 transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {is_in_stock ? (
            <>ADD TO CART <ShoppingCart size={15} /></>
          ) : (
            "OUT OF STOCK"
          )}
        </button>
        <button
          onClick={(e) => e.preventDefault()}
          className="border border-gray-300 rounded-lg p-2.5
                     hover:border-gray-400 transition"
        >
          <Heart size={16} className="text-gray-400" />
        </button>
      </div>
    </Link>
  );
}
// // ProductCard.jsx
// import { Star, ShoppingCart, Heart } from "lucide-react";

// export default function ProductCard({ product }) {
//   return (
//     <div className="bg-white rounded-xl p-4 hover:shadow-lg transition group">
      
//       {/* Image Area */}
//       <div className="relative h-52 flex items-center justify-center mb-4">
        
//         {product.discount && (
//           <span className="absolute top-0 left-0 bg-primary text-white text-xs font-bold px-2 py-1 rounded-md z-10">
//             -{product.discount}%
//           </span>
//         )}

//         <img
//           src={product.image}
//           alt={product.name}
//           className="max-h-full object-contain group-hover:scale-105 transition duration-300"
//         />
//       </div>

//       {/* Product Info */}
//       <h3 className="font-bold text-sm text-gray-900">
//         {product.name}
//       </h3>

//       <p className="text-xs text-gray-500 mt-1">
//         {product.bike}
//       </p>

//       {/* Rating */}
//       <div className="flex items-center gap-1 mt-2">
//         {[1, 2, 3, 4, 5].map((star) => (
//           <Star
//             key={star}
//             size={13}
//             className={
//               star <= Math.floor(product.rating)
//                 ? "fill-yellow-400 text-yellow-400"
//                 : star - 0.5 <= product.rating
//                 ? "fill-yellow-200 text-yellow-400"
//                 : "fill-gray-200 text-gray-200"
//             }
//           />
//         ))}
//         <span className="text-xs text-gray-500 ml-1">({product.reviews})</span>
//       </div>

//       {/* Price */}
//       <div className="flex items-center gap-2 mt-2">
//         <span className="text-primary font-black text-base">
//           Rs. {product.price.toLocaleString()}
//         </span>
//         <span className="text-gray-400 line-through text-sm">
//           Rs. {product.oldPrice.toLocaleString()}
//         </span>
//       </div>

//       {/* Add to Cart + Heart */}
//       <div className="flex items-center gap-2 mt-4">
//         <button className="flex-1 bg-primary text-white py-2.5 rounded-lg font-bold text-sm flex items-center justify-center gap-2 hover:bg-red-700 transition">
//           ADD TO CART
//           <ShoppingCart size={15} />
//         </button>
//         <button className="border border-gray-300 rounded-lg p-2.5 hover:border-gray-400 transition">
//           <Heart size={16} className="text-gray-400" />
//         </button>
//       </div>

//     </div>
//   );
// }
// import {
// Star,
// ShoppingCart,
// Heart
// } from "lucide-react";


// export default function ProductCard({
// product
// }){


// return (

// <div
// className="
// bg-white
// border
// border-gray-200
// rounded-xl
// p-4
// hover:shadow-xl
// transition
// group
// "
// >


// <div
// className="
// relative
// h-56
// flex
// items-center
// justify-center
// "
// >


// <span
// className="
// absolute
// top-2
// left-2
// bg-primary
// text-white
// text-xs
// font-bold
// px-3
// py-1
// rounded-full
// "
// >

// -{product.discount}

// </span>


// <button
// className="
// absolute
// right-2
// top-2
// "
// >

// <Heart
// size={20}
// className="
// text-gray-400
// "
// />

// </button>



// <img

// src={product.image}

// alt={product.name}

// className="
// max-h-full
// object-contain
// group-hover:scale-105
// transition
// "

// />


// </div>




// <h3
// className="
// font-bold
// mt-4
// text-sm
// "
// >

// {product.name}

// </h3>



// <p
// className="
// text-xs
// text-gray-500
// mt-1
// "
// >

// {product.bike}

// </p>



// <div
// className="
// flex
// items-center
// gap-1
// mt-3
// "
// >


// <Star

// size={15}

// className="
// fill-yellow-400
// text-yellow-400
// "

// />


// <span
// className="
// text-sm
// font-semibold
// "
// >

// {product.rating}

// </span>


// <span
// className="
// text-xs
// text-gray-400
// "
// >

// ({product.reviews})

// </span>


// </div>




// <div
// className="
// flex
// items-center
// gap-2
// mt-3
// "
// >

// <span
// className="
// text-primary
// font-black
// "
// >

// Rs. {product.price}

// </span>


// <span
// className="
// text-gray-400
// line-through
// text-sm
// "
// >

// Rs. {product.oldPrice}

// </span>


// </div>




// <button
// className="
// mt-5
// w-full
// bg-primary
// text-white
// py-3
// rounded-lg
// font-bold
// flex
// items-center
// justify-center
// gap-2
// "
// >

// <ShoppingCart size={17}/>

// ADD TO CART


// </button>



// </div>


// )

// }