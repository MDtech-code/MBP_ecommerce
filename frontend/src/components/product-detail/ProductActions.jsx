// src/components/product-detail/ProductActions.jsx
import { ShoppingCart, Plus, Minus } from "lucide-react";
import { useState } from "react";

/**
 * ProductActions
 *
 * Props:
 *   isInStock: boolean — from product.is_in_stock
 *   stock:     number  — from product.stock (for max qty guard)
 *
 * Cart functionality not built yet.
 * Buttons are wired for future cart hook integration.
 * is_in_stock disables both buttons when false.
 */
export default function ProductActions({ isInStock = true, stock = 0 }) {
  const [qty, setQty] = useState(1);

  const maxQty = stock > 0 ? stock : 1;

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
              className="px-3 py-2 hover:bg-gray-100 transition"
            >
              <Minus size={16} />
            </button>
            <span className="px-5 py-2 font-bold text-sm
                             border-x border-gray-300">
              {qty}
            </span>
            <button
              onClick={() => setQty(Math.min(maxQty, qty + 1))}
              className="px-3 py-2 hover:bg-gray-100 transition"
            >
              <Plus size={16} />
            </button>
          </div>
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-4 mt-5">
        <button
          disabled={!isInStock}
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
