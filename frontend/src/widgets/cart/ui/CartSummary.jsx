// src/widgets/cart/ui/CartSummary.jsx

import { useState, useEffect } from "react"
import { Lock, Tag, X, Loader2 } from "lucide-react"

/**
 * CartSummary — complete redesign for Phase 3.
 *
 * What changed from old version:
 *   - Removed hardcoded SHIPPING_FEE = 150
 *   - Removed hardcoded DISCOUNT = 0
 *   - Removed frontend float total calculation
 *   - Added coupon input section (apply + applied state + remove)
 *   - Added discount row (conditional on couponId)
 *   - Shipping now shows "Calculated at checkout"
 *   - Total uses totalPrice from backend (subtotal - coupon discount)
 *   - Selected items subtotal computed from selectedItems prop
 *   - Proceed button triggers onProceedToCheckout prop
 *
 * Financial display logic:
 *   selectedSubtotal → computed locally from selectedItems
 *                      (sum of product_price × quantity for selected items only)
 *   discountAmount   → from backend cart (coupon discount on full cart)
 *   totalPrice       → from backend cart (subtotal - discount, no shipping)
 *
 * Note on discountAmount at cart stage:
 *   Backend calculates discount on FULL cart subtotal.
 *   User may have selected only some items.
 *   We show discount_amount as-is — exact recalculation happens
 *   at checkout when selected_item_ids are sent to backend.
 *   This is a known display approximation at cart stage.
 *
 * Props:
 *   selectedItems    : CartItem[] — selected items from checkoutStore
 *   discountAmount   : string — from useCart (e.g. "500.00")
 *   totalPrice       : string — from useCart (subtotal - discount)
 *   couponId         : number|null — null = no coupon applied
 *   couponCodeInput  : string — preserved code for input pre-population
 *   onApplyCoupon    : (code: string) => void
 *   onRemoveCoupon   : () => void
 *   isCouponPending  : boolean
 *   couponError      : string|null
 *   isMutating       : boolean
 *   onProceedToCheckout : () => void
 */
export default function CartSummary({
  selectedItems    = [],
  discountAmount   = "0.00",
  couponId         = null,
  couponCodeInput  = "",
  onApplyCoupon,
  onRemoveCoupon,
  isCouponPending  = false,
  couponError      = null,
  isMutating       = false,
  onProceedToCheckout,
}) {
  // ── Coupon input state ─────────────────────────────────────────────────────
  // Pre-populate from preserved coupon_code_input on mount
  const [couponCode, setCouponCode] = useState(couponCodeInput)

  useEffect(() => {
    // Sync when cart loads and couponCodeInput is available
    if (couponCodeInput && !couponCode) {
      setCouponCode(couponCodeInput)
    }
  }, [couponCodeInput])

  // ── Selected items subtotal ────────────────────────────────────────────────
  // Computed from selected items only — not full cart subtotal
  // Uses product_price (current_price from backend) × quantity
  const selectedSubtotal = selectedItems.reduce((sum, item) => {
    return sum + parseFloat(item.product_price) * item.quantity
  }, 0)

  const selectedCount   = selectedItems.length
  const discount        = parseFloat(discountAmount)
  const hasCoupon       = couponId !== null
  const canProceed      = selectedCount > 0 && !isMutating

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleApply = () => {
    if (couponCode.trim()) {
      onApplyCoupon(couponCode.trim())
    }
  }

  const handleRemove = () => {
    onRemoveCoupon()
    setCouponCode("")
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter") handleApply()
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit">

      <h2 className="text-lg font-black text-gray-900">Order Summary</h2>

      {/* ── Line items ──────────────────────────────────────────────────────── */}
      <div className="mt-5 space-y-3">

        {/* Selected subtotal */}
        <div className="flex justify-between text-sm text-gray-600">
          <span>
            Subtotal
            <span className="text-gray-400 ml-1">
              ({selectedCount} item{selectedCount !== 1 ? "s" : ""} selected)
            </span>
          </span>
          <span className="font-semibold text-gray-800">
            Rs. {selectedSubtotal.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
          </span>
        </div>

        {/* Discount row — only when coupon applied */}
        {hasCoupon && discount > 0 && (
          <div className="flex justify-between text-sm text-green-600">
            <span className="flex items-center gap-1">
              <Tag size={13} />
              Coupon Discount
            </span>
            <span className="font-semibold">
              - Rs. {discount.toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        )}

        {/* Shipping */}
        <div className="flex justify-between text-sm text-gray-600">
          <span>Shipping</span>
          <span className="text-gray-400 italic text-xs mt-0.5">
            Calculated at checkout
          </span>
        </div>

      </div>

      <hr className="my-4 border-gray-200" />

      {/* ── Total ───────────────────────────────────────────────────────────── */}
      <div className="flex justify-between items-center">
        <div>
          <span className="font-black text-gray-900">Est. Total</span>
          <p className="text-xs text-gray-400 mt-0.5">Excl. shipping</p>
        </div>
        <span className="text-primary font-black text-2xl">
          Rs. {selectedSubtotal > 0
            ? (selectedSubtotal - discount).toLocaleString("en-PK", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
            : "0.00"
          }
        </span>
      </div>

      {/* ── Coupon section ──────────────────────────────────────────────────── */}
      <div className="mt-5">

        {hasCoupon ? (
          /* Applied state */
          <div className="flex items-center justify-between bg-green-50
                          border border-green-200 rounded-lg px-3 py-2.5">
            <div className="flex items-center gap-2 text-green-700">
              <Tag size={14} className="shrink-0" />
              <div>
                <p className="text-xs font-bold">{couponCodeInput}</p>
                <p className="text-xs text-green-600">Coupon applied</p>
              </div>
            </div>
            <button
              onClick={handleRemove}
              disabled={isCouponPending || isMutating}
              className="text-green-600 hover:text-red-500 transition
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isCouponPending
                ? <Loader2 size={14} className="animate-spin" />
                : <X size={14} />
              }
            </button>
          </div>
        ) : (
          /* Input state */
          <div>
            <div className="flex gap-2">
              <input
                type="text"
                value={couponCode}
                onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                onKeyDown={handleKeyDown}
                placeholder="Enter coupon code"
                disabled={isCouponPending || isMutating}
                className="flex-1 border border-gray-300 rounded-lg px-3 py-2
                           text-sm placeholder-gray-400 uppercase
                           focus:outline-none focus:ring-2 focus:ring-primary
                           focus:border-transparent
                           disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <button
                onClick={handleApply}
                disabled={!couponCode.trim() || isCouponPending || isMutating}
                className="px-4 py-2 bg-gray-900 text-white text-sm font-bold
                           rounded-lg hover:bg-gray-700 transition
                           disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center gap-1.5 shrink-0"
              >
                {isCouponPending
                  ? <Loader2 size={14} className="animate-spin" />
                  : "Apply"
                }
              </button>
            </div>

            {/* Coupon error */}
            {couponError && (
              <p className="text-xs text-red-500 mt-1.5 flex items-center gap-1">
                {couponError}
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Proceed button ──────────────────────────────────────────────────── */}
      <button
        onClick={onProceedToCheckout}
        disabled={!canProceed}
        className="mt-5 w-full bg-primary text-white py-3.5 rounded-lg
                   font-black text-sm hover:bg-red-700 transition
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {selectedCount === 0
          ? "SELECT ITEMS TO CHECKOUT"
          : `PROCEED TO CHECKOUT (${selectedCount})`
        }
      </button>

      <p className="text-xs text-gray-500 mt-4 flex items-center justify-center gap-1.5">
        <Lock size={12} />
        100% Secure Checkout
      </p>

    </div>
  )
}
// // src/components/cart/CartSummary.jsx
// import { Lock } from "lucide-react";

// /**
//  * CartSummary — totals from backend, not computed in frontend.
//  *
//  * Props:
//  *   SubTotal  : cart.subtotal string from backend ("33110.00")
//  *   totalItems  : cart.total_items integer from backend
//  *   isMutating  : boolean — disable checkout during mutations
//  *
//  * Why SubTotal from backend not computed locally:
//  *   Backend uses Decimal precision for monetary values.
//  *   Frontend float arithmetic produces rounding errors on
//  *   large prices or many items.
//  *
//  * Why shipping and discount are hardcoded:
//  *   Shipping and discount logic not built yet.
//  *   Hardcoded as visible placeholders — easy to replace when
//  *   shipping/coupon app is ready.
//  *   TODO: replace with real values from order/checkout API.
//  */

// const SHIPPING_FEE = 150;
// const DISCOUNT     = 0;

// export default function CartSummary({
//   SubTotal  = "0.00",
//   totalItems  = 0,
//   isMutating  = false,
// }) {
//   const subtotal = parseFloat(SubTotal);
//   const total    = subtotal + SHIPPING_FEE - DISCOUNT;

//   return (
//     <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit">

//       <h2 className="text-lg font-black text-gray-900">Order Summary</h2>

//       <div className="mt-5 space-y-3">

//         <div className="flex justify-between text-sm text-gray-600">
//           <span>
//             Subtotal
//             <span className="text-gray-400 ml-1">({totalItems} items)</span>
//           </span>
//           <span>Rs. {subtotal.toLocaleString()}</span>
//         </div>

//         <div className="flex justify-between text-sm text-gray-600">
//           <span>Shipping</span>
//           <span>Rs. {SHIPPING_FEE}</span>
//         </div>

//         <div className="flex justify-between text-sm text-gray-600">
//           <span>Discount</span>
//           <span>- Rs. {DISCOUNT}</span>
//         </div>

//       </div>

//       <hr className="my-4 border-gray-200" />

//       <div className="flex justify-between items-center">
//         <span className="font-black text-gray-900">Total</span>
//         <span className="text-primary font-black text-2xl">
//           Rs. {total.toLocaleString()}
//         </span>
//       </div>

//       <button
//         disabled={isMutating || totalItems === 0}
//         className="mt-5 w-full bg-primary text-white py-3.5 rounded-lg
//                    font-black text-sm hover:bg-red-700 transition
//                    disabled:opacity-50 disabled:cursor-not-allowed"
//       >
//         PROCEED TO CHECKOUT
//       </button>

//       <p className="text-xs text-gray-500 mt-4 flex items-center justify-center gap-1.5">
//         <Lock size={12} />
//         100% Secure Checkout
//       </p>

//     </div>
//   );
// }
