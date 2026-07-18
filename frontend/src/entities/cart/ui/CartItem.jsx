// src/entities/cart/ui/CartItem.jsx
import { Trash2, Minus, Plus } from "lucide-react";
import { Link } from "react-router-dom";

/**
 * CartItem — driven by real backend cart item shape.
 *
 * Backend fields used:
 *   id             → passed to handlers (CartItem.id not product id)
 *   product_name   → item title
 *   product_slug   → link to product detail page
 *   product_price  → unit price string from backend
 *   product_image  → absolute URL or null
 *   is_in_stock    → disables increase button when false
 *   quantity       → current quantity
 *   subtotal       → backend-computed subtotal string (price × qty)
 *
 * Why subtotal comes from backend not computed here:
 *   Backend uses Decimal precision.
 *   Frontend float would produce rounding errors on large prices.
 *
 * Props:
 *   item        : CartItemSerializer output (one item from cart.items[])
 *   onIncrease  : (itemId, quantity) => void
 *   onDecrease  : (itemId, quantity) => void
 *   onRemove    : (itemId) => void
 *   isMutating  : boolean — disable buttons during any pending mutation
 */

const FALLBACK_IMG = "/placeholder-part.png";

export default function CartItem({
  item,
  onIncrease,
  onDecrease,
  onRemove,
  isMutating = false,
}) {
  const {
    id,
    product_name,
    product_slug,
    product_price,
    product_image,
    is_in_stock,
    quantity,
    subtotal,
  } = item;

  const unitPrice = parseFloat(product_price).toLocaleString();
  const itemSubtotal = parseFloat(subtotal).toLocaleString();

  return (
    <div className="flex flex-col md:grid md:grid-cols-12 gap-4 md:gap-0 items-start md:items-center py-5 border-b border-gray-100 last:border-b-0">

      {/* Product */}
      <div className="w-full md:w-auto md:col-span-5 flex items-center gap-4">
        <Link to={`/product/${product_slug}`} className="shrink-0">
          <img
            src={product_image || FALLBACK_IMG}
            alt={product_name}
            className="w-20 h-20 object-contain"
            onError={(e) => { e.currentTarget.src = FALLBACK_IMG; }}
          />
        </Link>
        <div className="flex-1">
          <Link
            to={`/product/${product_slug}`}
            className="font-bold text-gray-900 text-sm hover:text-primary transition-colors line-clamp-2"
          >
            {product_name}
          </Link>
          {!is_in_stock && (
            <p className="text-xs text-red-500 font-semibold mt-0.5">
              Out of Stock
            </p>
          )}
        </div>
        {/* Mobile Remove Button (Hidden on Desktop) */}
        <button
          onClick={() => onRemove(id)}
          disabled={isMutating}
          className="md:hidden text-gray-400 hover:text-red-500 transition disabled:opacity-50 ml-auto shrink-0"
        >
          <Trash2 size={18} />
        </button>
      </div>

      {/* Unit Price */}
      <div className="w-full md:w-auto md:col-span-2 text-primary font-bold text-sm flex justify-between md:block">
        <span className="md:hidden text-gray-500 font-normal">Price:</span>
        Rs. {unitPrice}
      </div>

      {/* Quantity */}
      <div className="w-full md:w-auto md:col-span-2 flex justify-between md:block items-center">
        <span className="md:hidden text-gray-500 font-normal text-sm">Quantity:</span>
        <div className="flex items-center border border-gray-300 rounded-lg w-fit">
          <button
            onClick={() => onDecrease(id, quantity)}
            disabled={isMutating}
            className="px-2.5 py-1.5 hover:bg-gray-100 transition
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Minus size={14} />
          </button>
          <span className="px-3 py-1.5 text-sm font-semibold border-x border-gray-300">
            {quantity}
          </span>
          <button
            onClick={() => onIncrease(id, quantity)}
            disabled={isMutating || !is_in_stock}
            className="px-2.5 py-1.5 hover:bg-gray-100 transition
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Plus size={14} />
          </button>
        </div>
      </div>

      {/* Subtotal — from backend */}
      <div className="w-full md:w-auto md:col-span-2 text-primary font-bold text-sm flex justify-between md:block">
        <span className="md:hidden text-gray-500 font-normal">Subtotal:</span>
        Rs. {itemSubtotal}
      </div>

      {/* Desktop Remove */}
      <div className="hidden md:flex md:col-span-1 justify-center">
        <button
          onClick={() => onRemove(id)}
          disabled={isMutating}
          className="text-gray-400 hover:text-red-500 transition
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Trash2 size={18} />
        </button>
      </div>

    </div>
  );
}
// // src/entities/cart/ui/CartItem.jsx
// import { Trash2, Minus, Plus } from "lucide-react";
// import { Link } from "react-router-dom";

// /**
//  * CartItem — driven by real backend cart item shape.
//  *
//  * Backend fields used:
//  *   id             → passed to handlers (CartItem.id not product id)
//  *   product_name   → item title
//  *   product_slug   → link to product detail page
//  *   product_price  → unit price string from backend
//  *   product_image  → absolute URL or null
//  *   is_in_stock    → disables increase button when false
//  *   quantity       → current quantity
//  *   subtotal       → backend-computed subtotal string (price × qty)
//  *
//  * Why subtotal comes from backend not computed here:
//  *   Backend uses Decimal precision.
//  *   Frontend float would produce rounding errors on large prices.
//  *
//  * Props:
//  *   item        : CartItemSerializer output (one item from cart.items[])
//  *   onIncrease  : (itemId, quantity) => void
//  *   onDecrease  : (itemId, quantity) => void
//  *   onRemove    : (itemId) => void
//  *   isMutating  : boolean — disable buttons during any pending mutation
//  */

// const FALLBACK_IMG = "/placeholder-part.png";

// export default function CartItem({
//   item,
//   onIncrease,
//   onDecrease,
//   onRemove,
//   isMutating = false,
// }) {
//   const {
//     id,
//     product_name,
//     product_slug,
//     product_price,
//     product_image,
//     is_in_stock,
//     quantity,
//     subtotal,
//   } = item;

//   const unitPrice = parseFloat(product_price).toLocaleString();
//   const itemSubtotal = parseFloat(subtotal).toLocaleString();

//   return (
//     <div className="grid grid-cols-12 items-center py-5 border-b border-gray-100 last:border-b-0">

//       {/* Product */}
//       <div className="col-span-5 flex items-center gap-4">
//         <Link to={`/product/${product_slug}`} className="shrink-0">
//           <img
//             src={product_image || FALLBACK_IMG}
//             alt={product_name}
//             className="w-20 h-20 object-contain"
//             onError={(e) => { e.currentTarget.src = FALLBACK_IMG; }}
//           />
//         </Link>
//         <div>
//           <Link
//             to={`/product/${product_slug}`}
//             className="font-bold text-gray-900 text-sm hover:text-primary transition-colors"
//           >
//             {product_name}
//           </Link>
//           {!is_in_stock && (
//             <p className="text-xs text-red-500 font-semibold mt-0.5">
//               Out of Stock
//             </p>
//           )}
//         </div>
//       </div>

//       {/* Unit Price */}
//       <div className="col-span-2 text-primary font-bold text-sm">
//         Rs. {unitPrice}
//       </div>

//       {/* Quantity */}
//       <div className="col-span-2">
//         <div className="flex items-center border border-gray-300 rounded-lg w-fit">
//           <button
//             onClick={() => onDecrease(id, quantity)}
//             disabled={isMutating}
//             className="px-2.5 py-1.5 hover:bg-gray-100 transition
//                        disabled:opacity-50 disabled:cursor-not-allowed"
//           >
//             <Minus size={14} />
//           </button>
//           <span className="px-3 py-1.5 text-sm font-semibold border-x border-gray-300">
//             {quantity}
//           </span>
//           <button
//             onClick={() => onIncrease(id, quantity)}
//             disabled={isMutating || !is_in_stock}
//             className="px-2.5 py-1.5 hover:bg-gray-100 transition
//                        disabled:opacity-50 disabled:cursor-not-allowed"
//           >
//             <Plus size={14} />
//           </button>
//         </div>
//       </div>

//       {/* Subtotal — from backend */}
//       <div className="col-span-2 text-primary font-bold text-sm">
//         Rs. {itemSubtotal}
//       </div>

//       {/* Remove */}
//       <div className="col-span-1 flex justify-center">
//         <button
//           onClick={() => onRemove(id)}
//           disabled={isMutating}
//           className="text-gray-400 hover:text-red-500 transition
//                      disabled:opacity-50 disabled:cursor-not-allowed"
//         >
//           <Trash2 size={18} />
//         </button>
//       </div>

//     </div>
//   );
// }
