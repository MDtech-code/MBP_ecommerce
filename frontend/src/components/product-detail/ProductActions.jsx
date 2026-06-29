// components/product-detail/ProductActions.jsx
import { ShoppingCart, Plus, Minus } from "lucide-react";
import { useState } from "react";

export default function ProductActions() {
  const [qty, setQty] = useState(1);

  return (
    <div className="mt-6">

      {/* Quantity */}
      <div className="flex items-center gap-4">
        <span className="text-sm font-bold text-gray-700">Quantity:</span>
        <div className="flex items-center border border-gray-300 rounded-lg overflow-hidden">
          <button
            onClick={() => setQty(Math.max(1, qty - 1))}
            className="px-3 py-2 hover:bg-gray-100 transition"
          >
            <Minus size={16} />
          </button>
          <span className="px-5 py-2 font-bold text-sm border-x border-gray-300">
            {qty}
          </span>
          <button
            onClick={() => setQty(qty + 1)}
            className="px-3 py-2 hover:bg-gray-100 transition"
          >
            <Plus size={16} />
          </button>
        </div>
      </div>

      {/* Buttons */}
      <div className="flex gap-4 mt-5">
        <button className="flex-1 bg-primary text-white py-4 rounded-lg font-black flex justify-center items-center gap-2 hover:bg-red-700 transition text-sm">
          <ShoppingCart size={18} />
          ADD TO CART
        </button>
        <button className="flex-1 border-2 border-primary text-primary py-4 rounded-lg font-black hover:bg-red-50 transition text-sm">
          BUY NOW
        </button>
      </div>

    </div>
  );
}