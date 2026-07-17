// src/features/cart/ui/ProductActions.jsx
import { ShoppingCart, Plus, Minus } from "lucide-react";
import { useState } from "react";
import { useCart } from "../model/useCart";
import { useAuthStore }        from "@entities/user"
import { useNavigate }         from "react-router-dom"
/**
 * ProductActions — full cart action block for Product Detail Page.
 *
 * Responsibilities:
 *   - Quantity selector with stock guard
 *   - ADD TO CART button (wired to useCart)
 *   - BUY NOW button (future feature)
 *
 * Props:
 *   isInStock: boolean — from product.is_in_stock
 *   stock:     number  — from product.stock (max qty guard)
 *
 * Cart wiring:
 *   handleAddToCart(productId, qty) from useCart
 *   productId passed as prop from ProductDetailPage
 *   via useProductDetail hook
 */
export default function ProductActions({ productId, isInStock = true, stock = 0 }) {
  const [qty, setQty] = useState(1);
  const { handleAddToCart, isMutating } = useCart();
   const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const navigate        = useNavigate()

  const maxQty = stock > 0 ? stock : 1;


  const handleAddToCartClick = () => {
    if (!isAuthenticated) {
      navigate("/login")
      return
    }
    handleAddToCart(productId, qty)
  }

  return (
    <div className="mt-6">

      {/* Quantity selector */}
      {isInStock && (
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold text-gray-700">
            Quantity:
          </span>
          <div className="flex items-center border border-gray-300
                          rounded-lg overflow-hidden">
            <button
              onClick={() => setQty(Math.max(1, qty - 1))}
              disabled={isMutating}
              className="px-3 py-2 hover:bg-gray-100 transition
                         disabled:opacity-50"
            >
              <Minus size={16} />
            </button>
            <span className="px-5 py-2 font-bold text-sm
                             border-x border-gray-300">
              {qty}
            </span>
            <button
              onClick={() => setQty(Math.min(maxQty, qty + 1))}
              disabled={isMutating}
              className="px-3 py-2 hover:bg-gray-100 transition
                         disabled:opacity-50"
            >
              <Plus size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-4 mt-5">
        <button
          onClick={handleAddToCartClick}
          disabled={!isInStock || isMutating}
          className="flex-1 bg-primary text-white py-4 rounded-lg
                     font-black flex justify-center items-center gap-2
                     hover:bg-red-700 transition text-sm
                     disabled:opacity-50 disabled:cursor-not-allowed
                     disabled:hover:bg-primary"
        >
          <ShoppingCart size={18} />
          {isInStock ? "ADD TO CART" : "OUT OF STOCK"}
        </button>

        <button
          disabled={!isInStock}
          className="flex-1 border-2 border-primary text-primary
                     py-4 rounded-lg font-black hover:bg-red-50
                     transition text-sm
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          BUY NOW
        </button>
      </div>

    </div>
  );
}