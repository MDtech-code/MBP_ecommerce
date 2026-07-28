// src/widgets/cart/ui/CartList.jsx

import { ArrowLeft, Trash2 } from "lucide-react"
import { Link } from "react-router-dom"
import { CartItem } from "@entities/cart"

/**
 * CartList — driven by real backend cart shape.
 *
 * New selection props:
 *   selectedItemIds  : number[] — from checkoutStore
 *   onToggleItem     : (itemId, item) => void
 *   onSelectAll      : () => void — calls checkoutStore.selectAll(items)
 *   onClearSelection : () => void — calls checkoutStore.clearSelection()
 *   isAllSelected    : boolean
 *
 * Selection count label:
 *   "X of Y items selected" shown below header when items exist.
 *   Helps user understand checkout will only process selected items.
 *
 * Proceed to Checkout:
 *   Moved from CartSummary button to here conceptually — but actual
 *   navigation is triggered from CartPage which has access to both
 *   CartList (selection) and navigation. CartList receives
 *   onProceedToCheckout prop from CartPage.
 */
export default function CartList({
  items = [],
  isMutating = false,
  onIncrease,
  onDecrease,
  onRemove,
  onClearCart,
  // Selection props
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
// // src/components/cart/CartList.jsx
// import { ArrowLeft, Trash2 } from "lucide-react";
// import { Link } from "react-router-dom";
// import { CartItem } from "@entities/cart"

// /**
//  * CartList — driven by real backend cart shape.
//  *
//  * Props:
//  *   items       : cart.items[] from useCart hook
//  *   isMutating  : boolean — any mutation pending
//  *   onIncrease  : (itemId, quantity) => void
//  *   onDecrease  : (itemId, quantity) => void
//  *   onRemove    : (itemId) => void
//  *   onClearCart : () => void
//  *
//  * Why no local state here:
//  *   All cart state lives in TanStack Query cache via useCart.
//  *   CartList is purely display + event delegation.
//  */
// export default function CartList({
//   items = [],
//   isMutating = false,
//   onIncrease,
//   onDecrease,
//   onRemove,
//   onClearCart,
// }) {
//   return (
//     <div>

//       {/* Table */}
//       <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">

//         {/* Header */}
//         <div className="grid grid-cols-12 px-6 py-4 border-b border-gray-200 bg-white">
//           <div className="col-span-5 text-xs font-bold text-gray-700 uppercase tracking-wide">
//             Product
//           </div>
//           <div className="col-span-2 text-xs font-bold text-gray-700 uppercase tracking-wide">
//             Price
//           </div>
//           <div className="col-span-2 text-xs font-bold text-gray-700 uppercase tracking-wide">
//             Quantity
//           </div>
//           <div className="col-span-2 text-xs font-bold text-gray-700 uppercase tracking-wide">
//             Total
//           </div>
//           <div className="col-span-1 text-xs font-bold text-gray-700 uppercase tracking-wide text-center">
//             Action
//           </div>
//         </div>

//         {/* Items */}
//         <div className="px-6">
//           {items.map((item) => (
//             <CartItem
//               key={item.id}
//               item={item}
//               onIncrease={onIncrease}
//               onDecrease={onDecrease}
//               onRemove={onRemove}
//               isMutating={isMutating}
//             />
//           ))}
//         </div>

//       </div>

//       {/* Bottom Buttons */}
//       <div className="flex items-center justify-between mt-5">
//         <Link
//           to="/product"
//           className="flex items-center gap-2 border border-gray-300 rounded-lg
//                      px-5 py-2.5 text-sm font-bold text-gray-700
//                      hover:border-gray-400 transition"
//         >
//           <ArrowLeft size={16} />
//           CONTINUE SHOPPING
//         </Link>

//         <button
//           onClick={onClearCart}
//           disabled={isMutating || items.length === 0}
//           className="flex items-center gap-2 border border-gray-300 rounded-lg
//                      px-5 py-2.5 text-sm font-bold text-gray-700
//                      hover:border-gray-400 transition
//                      disabled:opacity-50 disabled:cursor-not-allowed"
//         >
//           <Trash2 size={16} />
//           CLEAR CART
//         </button>
//       </div>

//     </div>
//   );
// }
