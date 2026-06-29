// components/cart/CartList.jsx

import { ArrowLeft, Trash2 } from "lucide-react";
import CartItem from "./CartItem";

export default function CartList({ items, setItems }) {

  function handleIncrease(id) {
    setItems(items.map(item =>
      item.id === id ? { ...item, quantity: item.quantity + 1 } : item
    ));
  }

  function handleDecrease(id) {
    setItems(items.map(item =>
      item.id === id && item.quantity > 1
        ? { ...item, quantity: item.quantity - 1 }
        : item
    ));
  }

  function handleRemove(id) {
    setItems(items.filter(item => item.id !== id));
  }

  function handleClearCart() {
    setItems([]);
  }

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
          {items.map(item => (
            <CartItem
              key={item.id}
              item={item}
              onIncrease={handleIncrease}
              onDecrease={handleDecrease}
              onRemove={handleRemove}
            />
          ))}
        </div>

      </div>

      {/* Bottom Buttons */}
      <div className="flex items-center justify-between mt-5">
        <button className="flex items-center gap-2 border border-gray-300 rounded-lg px-5 py-2.5 text-sm font-bold text-gray-700 hover:border-gray-400 transition">
          <ArrowLeft size={16} />
          CONTINUE SHOPPING
        </button>
        <button
          onClick={handleClearCart}
          className="flex items-center gap-2 border border-gray-300 rounded-lg px-5 py-2.5 text-sm font-bold text-gray-700 hover:border-gray-400 transition"
        >
          <Trash2 size={16} />
          CLEAR CART
        </button>
      </div>

    </div>
  );
}