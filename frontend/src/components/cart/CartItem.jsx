// components/cart/CartItem.jsx
import { Trash2, Minus, Plus } from "lucide-react";

export default function CartItem({ item, onIncrease, onDecrease, onRemove }) {
  return (
    <div className="grid grid-cols-12 items-center py-5 border-b border-gray-100 last:border-b-0">

      {/* Product */}
      <div className="col-span-5 flex items-center gap-4">
        <img
          src={item.image}
          alt={item.name}
          className="w-20 h-20 object-contain shrink-0"
        />
        <div>
          <h3 className="font-bold text-gray-900 text-sm">{item.name}</h3>
          <p className="text-sm text-gray-500 mt-0.5">{item.bike}</p>
          <p className="text-sm text-gray-500">Brand: {item.brand}</p>
        </div>
      </div>

      {/* Price */}
      <div className="col-span-2 text-primary font-bold text-sm">
        Rs. {item.price.toLocaleString()}
      </div>

      {/* Quantity */}
      <div className="col-span-2">
        <div className="flex items-center border border-gray-300 rounded-lg w-fit">
          <button
            onClick={() => onDecrease(item.id)}
            className="px-2.5 py-1.5 hover:bg-gray-100 transition"
          >
            <Minus size={14} />
          </button>
          <span className="px-3 py-1.5 text-sm font-semibold border-x border-gray-300">
            {item.quantity}
          </span>
          <button
            onClick={() => onIncrease(item.id)}
            className="px-2.5 py-1.5 hover:bg-gray-100 transition"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {/* Total */}
      <div className="col-span-2 text-primary font-bold text-sm">
        Rs. {(item.price * item.quantity).toLocaleString()}
      </div>

      {/* Action */}
      <div className="col-span-1 flex justify-center">
        <button
          onClick={() => onRemove(item.id)}
          className="text-gray-400 hover:text-red-500 transition"
        >
          <Trash2 size={18} />
        </button>
      </div>

    </div>
  );
}