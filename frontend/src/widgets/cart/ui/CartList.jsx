// src/widgets/cart/ui/CartList.jsx

import { ArrowLeft, Trash2 } from "lucide-react"
import { Link } from "react-router-dom"
import { CartItem } from "@entities/cart"


export default function CartList({
  items = [],
  isMutating = false,
  onIncrease,
  onDecrease,
  onRemove,
  onClearCart,
  selectedItemIds = [],
  onToggleItem,
  onSelectAll,
  onClearSelection,
  isAllSelected = false,
}) {
  const selectedCount = selectedItemIds.length
  const totalCount    = items.length

  const handleSelectAllToggle = () => {
    if (isAllSelected) {
      onClearSelection()
    } else {
      onSelectAll(items)
    }
  }

  return (
    <div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

        {/* Header */}
        <div className="grid grid-cols-12 px-6 py-4 border-b border-gray-200 bg-white items-center">

          {/* Select All checkbox + Product label */}
          <div className="col-span-5 flex items-center gap-3">
            <label className="flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={isAllSelected}
                onChange={handleSelectAllToggle}
                disabled={isMutating || items.length === 0}
                className="w-4 h-4 rounded border-gray-300 text-primary
                           focus:ring-primary focus:ring-2
                           disabled:opacity-50 disabled:cursor-not-allowed
                           accent-primary cursor-pointer"
              />
            </label>
            <span className="text-xs font-bold text-gray-700 uppercase tracking-wide">
              Product
            </span>
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

        {/* Selection count label */}
        {totalCount > 0 && (
          <div className="px-6 py-2 bg-gray-50 border-b border-gray-100">
            <p className="text-xs text-gray-500">
              <span className="font-semibold text-gray-700">
                {selectedCount}
              </span>
              {" of "}
              <span className="font-semibold text-gray-700">
                {totalCount}
              </span>
              {" item"}
              {totalCount !== 1 ? "s" : ""}
              {" selected for checkout"}
            </p>
          </div>
        )}

        {/* Items */}
        <div className="px-6">
          {items.map((item) => (
            <CartItem
              key={item.id}
              item={item}
              onIncrease={onIncrease}
              onDecrease={onDecrease}
              onRemove={onRemove}
              onToggleSelect={onToggleItem}
              isSelected={selectedItemIds.includes(item.id)}
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
  )
}
