// src/components/cart/CartSummary.jsx
import { Lock } from "lucide-react";

/**
 * CartSummary — totals from backend, not computed in frontend.
 *
 * Props:
 *   SubTotal  : cart.subtotal string from backend ("33110.00")
 *   totalItems  : cart.total_items integer from backend
 *   isMutating  : boolean — disable checkout during mutations
 *
 * Why SubTotal from backend not computed locally:
 *   Backend uses Decimal precision for monetary values.
 *   Frontend float arithmetic produces rounding errors on
 *   large prices or many items.
 *
 * Why shipping and discount are hardcoded:
 *   Shipping and discount logic not built yet.
 *   Hardcoded as visible placeholders — easy to replace when
 *   shipping/coupon app is ready.
 *   TODO: replace with real values from order/checkout API.
 */

const SHIPPING_FEE = 150;
const DISCOUNT     = 0;

export default function CartSummary({
  SubTotal  = "0.00",
  totalItems  = 0,
  isMutating  = false,
}) {
  const subtotal = parseFloat(SubTotal);
  const total    = subtotal + SHIPPING_FEE - DISCOUNT;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit">

      <h2 className="text-lg font-black text-gray-900">Order Summary</h2>

      <div className="mt-5 space-y-3">

        <div className="flex justify-between text-sm text-gray-600">
          <span>
            Subtotal
            <span className="text-gray-400 ml-1">({totalItems} items)</span>
          </span>
          <span>Rs. {subtotal.toLocaleString()}</span>
        </div>

        <div className="flex justify-between text-sm text-gray-600">
          <span>Shipping</span>
          <span>Rs. {SHIPPING_FEE}</span>
        </div>

        <div className="flex justify-between text-sm text-gray-600">
          <span>Discount</span>
          <span>- Rs. {DISCOUNT}</span>
        </div>

      </div>

      <hr className="my-4 border-gray-200" />

      <div className="flex justify-between items-center">
        <span className="font-black text-gray-900">Total</span>
        <span className="text-primary font-black text-2xl">
          Rs. {total.toLocaleString()}
        </span>
      </div>

      <button
        disabled={isMutating || totalItems === 0}
        className="mt-5 w-full bg-primary text-white py-3.5 rounded-lg
                   font-black text-sm hover:bg-red-700 transition
                   disabled:opacity-50 disabled:cursor-not-allowed"
      >
        PROCEED TO CHECKOUT
      </button>

      <p className="text-xs text-gray-500 mt-4 flex items-center justify-center gap-1.5">
        <Lock size={12} />
        100% Secure Checkout
      </p>

    </div>
  );
}
// // components/cart/CartSummary.jsx
// import { Lock } from "lucide-react";

// export default function CartSummary({ items }) {

//   const subtotal = items.reduce((sum, item) => sum + item.price * item.quantity, 0);
//   const shipping = 150;
//   const discount = 0;
//   const total = subtotal + shipping - discount;

//   return (
//     <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit">

//       <h2 className="text-lg font-black text-gray-900">Order Summary</h2>

//       <div className="mt-5 space-y-3">
//         <div className="flex justify-between text-sm text-gray-600">
//           <span>Subtotal</span>
//           <span>Rs. {subtotal.toLocaleString()}</span>
//         </div>
//         <div className="flex justify-between text-sm text-gray-600">
//           <span>Shipping</span>
//           <span>Rs. {shipping}</span>
//         </div>
//         <div className="flex justify-between text-sm text-gray-600">
//           <span>Discount</span>
//           <span>- Rs. {discount}</span>
//         </div>
//       </div>

//       <hr className="my-4 border-gray-200" />

//       <div className="flex justify-between items-center">
//         <span className="font-black text-gray-900">Total</span>
//         <span className="text-primary font-black text-2xl">
//           Rs. {total.toLocaleString()}
//         </span>
//       </div>

//       <button className="mt-5 w-full bg-primary text-white py-3.5 rounded-lg font-black text-sm hover:bg-red-700 transition">
//         PROCEED TO CHECKOUT
//       </button>

//       <p className="text-xs text-gray-500 mt-4 flex items-center justify-center gap-1.5">
//         <Lock size={12} />
//         Secure 100% Secure Checkout
//       </p>

//     </div>
//   );
// }