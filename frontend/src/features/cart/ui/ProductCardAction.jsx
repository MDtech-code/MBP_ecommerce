// src/features/cart/ui/ProductCardAction.jsx

import { ShoppingCart, Heart } from "lucide-react";
import { useCart } from "../model/useCart";
import { useAuthStore } from "@entities/user";
import { useNavigate } from "react-router-dom";
import { useWishlist } from "@features/wishlist/model/useWishlist";

/**
 * ProductCardAction — cart + wishlist actions for product listing cards.
 *
 * Props:
 *   productId  → product.id
 *   isInStock  → controls disabled state
 */
export default function ProductCardAction({ productId, isInStock }) {
  const { handleAddToCart, isMutating: isCartMutating } = useCart();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const navigate        = useNavigate();

  const {
    isWishlisted,
    isMutating: isWishlistMutating,
    handleToggleWishlist,
  } = useWishlist();

  const wishlisted    = isWishlisted(productId);
  const heartMutating = isWishlistMutating(productId);

  return (
    <div className="flex items-center gap-2">

      {/* ── Add to cart ─────────────────────────────────────────────── */}
      <button
        onClick={(e) => {
          e.preventDefault();
          if (!isAuthenticated) {
            navigate("/login");
            return;
          }
          handleAddToCart(productId, 1);
        }}
        disabled={!isInStock || isCartMutating}
        className="flex-1 bg-primary text-white py-2.5 rounded-lg
                   font-bold text-sm flex items-center justify-center
                   gap-2 hover:bg-red-700 transition
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {isInStock ? (
          <>ADD TO CART <ShoppingCart size={15} /></>
        ) : (
          "OUT OF STOCK"
        )}
      </button>

      {/* ── Wishlist toggle ─────────────────────────────────────────── */}
      <button
        onClick={(e) => {
          e.preventDefault();
          handleToggleWishlist(productId);
        }}
        disabled={heartMutating}
        className={`border rounded-lg p-2.5 transition
                    disabled:opacity-50 disabled:cursor-not-allowed
                    ${wishlisted
                      ? "border-primary bg-primary/5"
                      : "border-gray-300 hover:border-gray-400"
                    }`}
        aria-label={wishlisted ? "Remove from wishlist" : "Add to wishlist"}
      >
        {heartMutating ? (
          <span className="w-4 h-4 border-2 border-gray-300
                           border-t-primary rounded-full animate-spin
                           block" />
        ) : (
          <Heart
            size={16}
            className={
              wishlisted ? "text-primary fill-primary" : "text-gray-400"
            }
          />
        )}
      </button>

    </div>
  );
}
// // src/features/cart/ui/ProductCardAction.jsx
// import { ShoppingCart, Heart } from "lucide-react";
// import { useCart } from "../model/useCart";
// import { useAuthStore }        from "@entities/user"
// import { useNavigate }         from "react-router-dom"

// /**
//  * ProductCardAction — simple cart action for product listing cards.
//  *
//  * Injected into ProductCard via action prop slot.
//  * ProductCard has zero knowledge of this component.
//  *
//  * Props:
//  *   productId  → product.id (integer — backend expects this)
//  *   isInStock  → controls disabled state and label
//  */
// export default function ProductCardAction({ productId, isInStock }) {
//   const { handleAddToCart, isMutating } = useCart();
//    const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
//   const navigate        = useNavigate()

//   return (
//     <div className="flex items-center gap-2">
//       <button
//         onClick={(e) => {
//           e.preventDefault();
//           if (!isAuthenticated) {
//             navigate("/login")
//             return
//           }
//           handleAddToCart(productId, 1);
          
//         }}
//         disabled={!isInStock || isMutating}
//         className="flex-1 bg-primary text-white py-2.5 rounded-lg
//                    font-bold text-sm flex items-center justify-center
//                    gap-2 hover:bg-red-700 transition
//                    disabled:opacity-50 disabled:cursor-not-allowed"
//       >
//         {isInStock ? (
//           <>ADD TO CART <ShoppingCart size={15} /></>
//         ) : (
//           "OUT OF STOCK"
//         )}
//       </button>

//       <button
//         onClick={(e) => e.preventDefault()}
//         className="border border-gray-300 rounded-lg p-2.5
//                    hover:border-gray-400 transition"
//       >
//         <Heart size={16} className="text-gray-400" />
//       </button>
//     </div>
//   );
// }