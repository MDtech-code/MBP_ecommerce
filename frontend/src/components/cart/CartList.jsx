// src/components/cart/CartList.jsx
import { ArrowLeft, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import CartItem from "./CartItem";

/**
 * CartList — driven by real backend cart shape.
 *
 * Props:
 *   items       : cart.items[] from useCart hook
 *   isMutating  : boolean — any mutation pending
 *   onIncrease  : (itemId, quantity) => void
 *   onDecrease  : (itemId, quantity) => void
 *   onRemove    : (itemId) => void
 *   onClearCart : () => void
 *
 * Why no local state here:
 *   All cart state lives in TanStack Query cache via useCart.
 *   CartList is purely display + event delegation.
 */
export default function CartList({
  items = [],
  isMutating = false,
  onIncrease,
  onDecrease,
  onRemove,
  onClearCart,
}) {
  return (
    <div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

        {/* Header */}
        <div className="grid grid-cols-12 px-6 py-4 border-b border-gray-200 bg-white">
          <div className="col-span-5 text-xs font-bold text-gray-700 uppercase tracking-wide">
            Product
          </div>
          <div className="col-span-2 text-xs font-bold text-gray-700 uppercase tracking-wide">
            Price
          </div>
          <div className="col-span-2 text-xs font-bold text-gray-700 uppercase tracking-wide">
            Quantity
          </div>
          <div className="col-span-2 text-xs font-bold text-gray-700 uppercase tracking-wide">
            Total
          </div>
          <div className="col-span-1 text-xs font-bold text-gray-700 uppercase tracking-wide text-center">
            Action
          </div>
        </div>

        {/* Items */}
        <div className="px-6">
          {items.map((item) => (
            <CartItem
              key={item.id}
              item={item}
              onIncrease={onIncrease}
              onDecrease={onDecrease}
              onRemove={onRemove}
              isMutating={isMutating}
            />
          ))}
        </div>

      </div>

      {/* Bottom Buttons */}
      <div className="flex items-center justify-between mt-5">
        <Link
          to="/product"
          className="flex items-center gap-2 border border-gray-300 rounded-lg
                     px-5 py-2.5 text-sm font-bold text-gray-700
                     hover:border-gray-400 transition"
        >
          <ArrowLeft size={16} />
          CONTINUE SHOPPING
        </Link>

        <button
          onClick={onClearCart}
          disabled={isMutating || items.length === 0}
          className="flex items-center gap-2 border border-gray-300 rounded-lg
                     px-5 py-2.5 text-sm font-bold text-gray-700
                     hover:border-gray-400 transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 size={16} />
          CLEAR CART
        </button>
      </div>

    </div>
  );
}
