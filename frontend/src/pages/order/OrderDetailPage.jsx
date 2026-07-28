// src/pages/OrderDetailPage/OrderDetailPage.jsx

import { useParams, Link } from "react-router-dom"
import {
  ChevronLeft, Package, MapPin, CreditCard,
  AlertCircle, Loader2, XCircle
} from "lucide-react"
import { useOrderDetail } from "@features/order"

// ── Status config ─────────────────────────────────────────────────────────────
const STATUS_STYLES = {
  pending:    "bg-yellow-100 text-yellow-800",
  confirmed:  "bg-blue-100 text-blue-800",
  processing: "bg-indigo-100 text-indigo-800",
  shipped:    "bg-purple-100 text-purple-800",
  delivered:  "bg-green-100 text-green-800",
  cancelled:  "bg-red-100 text-red-800",
  refunded:   "bg-gray-100 text-gray-700",
}

// Linear tracker steps — cancelled/refunded handled separately
const TRACKER_STEPS = ["pending", "confirmed", "processing", "shipped", "delivered"]

function StatusBadge({ status }) {
  const styles = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600"
  return (
    <span className={`
      inline-flex items-center px-3 py-1 rounded-full
      text-xs font-bold uppercase tracking-wide
      ${styles}
    `}>
      {status}
    </span>
  )
}

// ── Status tracker ────────────────────────────────────────────────────────────
function OrderStatusTracker({ status }) {
  // Terminal states get their own banner — not the linear tracker
  if (status === "cancelled" || status === "refunded") {
    return (
      <div className={`
        flex items-center gap-3 rounded-xl px-4 py-3 border
        ${status === "cancelled"
          ? "bg-red-50 border-red-200"
          : "bg-gray-50 border-gray-200"
        }
      `}>
        <XCircle size={18} className={
          status === "cancelled" ? "text-red-500" : "text-gray-400"
        } />
        <div>
          <p className={`text-sm font-bold ${
            status === "cancelled" ? "text-red-700" : "text-gray-600"
          }`}>
            Order {status === "cancelled" ? "Cancelled" : "Refunded"}
          </p>
          <p className="text-xs text-gray-500 mt-0.5">
            {status === "cancelled"
              ? "This order has been cancelled. Stock has been restored."
              : "This order has been refunded."
            }
          </p>
        </div>
      </div>
    )
  }

  const currentIndex = TRACKER_STEPS.indexOf(status)

  return (
    <div className="flex items-center gap-0">
      {TRACKER_STEPS.map((step, idx) => {
        const isComplete = idx <= currentIndex
        const isCurrent  = idx === currentIndex
        const isLast     = idx === TRACKER_STEPS.length - 1

        return (
          <div key={step} className="flex items-center flex-1 last:flex-none">
            {/* Step circle + label */}
            <div className="flex flex-col items-center gap-1.5">
              <div className={`
                w-7 h-7 rounded-full flex items-center justify-center
                text-xs font-bold transition-colors
                ${isComplete
                  ? isCurrent
                    ? "bg-primary text-white ring-2 ring-primary ring-offset-2"
                    : "bg-primary text-white"
                  : "bg-gray-100 text-gray-400 border border-gray-200"
                }
              `}>
                {isComplete && !isCurrent ? "✓" : idx + 1}
              </div>
              <span className={`
                text-xs font-semibold capitalize whitespace-nowrap
                ${isComplete ? "text-gray-800" : "text-gray-400"}
              `}>
                {step}
              </span>
            </div>

            {/* Connector line */}
            {!isLast && (
              <div className={`
                flex-1 h-0.5 mb-5 mx-1
                ${idx < currentIndex ? "bg-primary" : "bg-gray-200"}
              `} />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Order item row ────────────────────────────────────────────────────────────
function OrderItemRow({ item }) {
  const hasDiscount = parseFloat(item.original_price) !== parseFloat(item.unit_price)
  const lineTotal   = parseFloat(item.subtotal)

  return (
    <div className="flex items-start gap-4 py-4 border-b border-gray-100
                    last:border-b-0">
      {/* Product icon placeholder */}
      <div className="w-12 h-12 bg-gray-50 rounded-lg border border-gray-100
                      flex items-center justify-center shrink-0">
        <Package size={18} className="text-gray-300" />
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-gray-800">{item.product_name}</p>
        <p className="text-xs text-gray-400 mt-0.5">SKU: {item.product_sku}</p>

        {/* Price comparison */}
        <div className="flex items-center gap-2 mt-1.5 flex-wrap">
          {hasDiscount ? (
            <>
              <span className="text-xs text-gray-400 line-through">
                Rs. {parseFloat(item.original_price).toLocaleString("en-PK")}
              </span>
              <span className="text-xs font-bold text-primary">
                Rs. {parseFloat(item.unit_price).toLocaleString("en-PK")}
              </span>
              <span className="text-xs bg-green-100 text-green-700
                               font-semibold px-1.5 py-0.5 rounded">
                Saved Rs. {(
                  (parseFloat(item.original_price) - parseFloat(item.unit_price))
                  * item.quantity
                ).toLocaleString("en-PK")}
              </span>
            </>
          ) : (
            <span className="text-xs font-bold text-gray-700">
              Rs. {parseFloat(item.unit_price).toLocaleString("en-PK")}
            </span>
          )}
          <span className="text-xs text-gray-400">× {item.quantity}</span>
        </div>
      </div>

      {/* Line total */}
      <div className="text-sm font-bold text-gray-800 shrink-0">
        Rs. {lineTotal.toLocaleString("en-PK", { minimumFractionDigits: 0 })}
      </div>
    </div>
  )
}

// ── Pricing summary ───────────────────────────────────────────────────────────
function OrderPricingSummary({ order }) {
  const hasDiscount = parseFloat(order.discount_amount) > 0
  const hasTax      = parseFloat(order.tax_amount) > 0

  return (
    <div className="space-y-2 text-sm">
      <div className="flex justify-between text-gray-600">
        <span>Subtotal</span>
        <span className="font-semibold text-gray-800">
          Rs. {parseFloat(order.subtotal).toLocaleString("en-PK", {
            minimumFractionDigits: 2,
          })}
        </span>
      </div>

      <div className="flex justify-between text-gray-600">
        <span>Shipping to {order.shipping_address?.city}</span>
        <span className="font-semibold text-gray-800">
          Rs. {parseFloat(order.shipping_fee).toLocaleString("en-PK", {
            minimumFractionDigits: 2,
          })}
        </span>
      </div>

      {/* Discount — only when coupon applied */}
      {hasDiscount && (
        <div className="flex justify-between text-green-600">
          <span className="flex items-center gap-1">
            Coupon
            {order.coupon_code_snapshot && (
              <span className="font-mono text-xs bg-green-100 px-1.5 py-0.5 rounded">
                {order.coupon_code_snapshot}
              </span>
            )}
          </span>
          <span className="font-semibold">
            - Rs. {parseFloat(order.discount_amount).toLocaleString("en-PK", {
              minimumFractionDigits: 2,
            })}
          </span>
        </div>
      )}

      {/* Tax — shown on order detail per OI-4 */}
      {hasTax && (
        <div className="flex justify-between text-gray-600">
          <span>Tax</span>
          <span className="font-semibold text-gray-800">
            Rs. {parseFloat(order.tax_amount).toLocaleString("en-PK", {
              minimumFractionDigits: 2,
            })}
          </span>
        </div>
      )}

      <hr className="border-gray-100 my-2" />

      <div className="flex justify-between items-center">
        <span className="font-black text-gray-900">Total</span>
        <span className="text-primary font-black text-lg">
          Rs. {parseFloat(order.total_price).toLocaleString("en-PK", {
            minimumFractionDigits: 2,
          })}
        </span>
      </div>
    </div>
  )
}

// ── Cancel confirmation dialog ────────────────────────────────────────────────
function CancelConfirmDialog({ onConfirm, onDismiss, isCancelling, cancelError }) {
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center
                    z-50 px-4">
      <div className="bg-white rounded-2xl p-6 max-w-sm w-full shadow-xl">
        <h3 className="text-base font-black text-gray-900 mb-2">
          Cancel this order?
        </h3>
        <p className="text-sm text-gray-500 mb-5">
          Are you sure you want to cancel this order?
          This action cannot be undone.
        </p>

        {cancelError && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-200
                          rounded-lg px-3 py-2.5 mb-4">
            <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
            <p className="text-xs text-red-600">{cancelError}</p>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={onDismiss}
            disabled={isCancelling}
            className="flex-1 border border-gray-300 rounded-xl py-2.5
                       text-sm font-bold text-gray-700
                       hover:border-gray-400 transition
                       disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Keep Order
          </button>
          <button
            onClick={onConfirm}
            disabled={isCancelling}
            className="flex-1 bg-red-600 text-white rounded-xl py-2.5
                       text-sm font-bold hover:bg-red-700 transition
                       disabled:opacity-50 disabled:cursor-not-allowed
                       flex items-center justify-center gap-2"
          >
            {isCancelling
              ? <><Loader2 size={14} className="animate-spin" /> Cancelling...</>
              : "Yes, Cancel"
            }
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Format date ───────────────────────────────────────────────────────────────
function formatDateTime(dateString) {
  if (!dateString) return null
  return new Date(dateString).toLocaleDateString("en-PK", {
    day:    "numeric",
    month:  "long",
    year:   "numeric",
    hour:   "2-digit",
    minute: "2-digit",
  })
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function OrderDetailPage() {
  const { orderNumber } = useParams()

  const {
    order,
    isLoading,
    isError,
    errorMessage,
    isCancelling,
    cancelError,
    showCancelConfirm,
    handleCancelClick,
    handleCancelDismiss,
    handleCancelConfirm,
  } = useOrderDetail(orderNumber)

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 w-64 bg-gray-100 rounded" />
        <div className="h-24 bg-gray-100 rounded-xl" />
        <div className="h-48 bg-gray-100 rounded-xl" />
        <div className="h-32 bg-gray-100 rounded-xl" />
      </div>
    )
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (isError || !order) {
    return (
      <div className="text-center py-24">
        <p className="text-4xl mb-4">⚠️</p>
        <p className="font-bold text-gray-700 mb-2">Order not found</p>
        <p className="text-sm text-gray-500 mb-6">
          {errorMessage ?? "This order does not exist or you do not have access."}
        </p>
        <Link
          to="/orders"
          className="bg-primary text-white px-6 py-3 rounded-lg
                     font-bold text-sm hover:bg-red-700 transition"
        >
          Back to Orders
        </Link>
      </div>
    )
  }

  return (
    <>
      {/* Cancel dialog — rendered at root level */}
      {showCancelConfirm && (
        <CancelConfirmDialog
          onConfirm={handleCancelConfirm}
          onDismiss={handleCancelDismiss}
          isCancelling={isCancelling}
          cancelError={cancelError}
        />
      )}

      <div className="space-y-5 max-w-3xl">

        {/* Back link */}
        <Link
          to="/orders"
          className="inline-flex items-center gap-2 text-sm font-bold
                     text-gray-500 hover:text-gray-700 transition"
        >
          <ChevronLeft size={15} />
          Back to My Orders
        </Link>

        {/* Header */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <p className="text-xs text-gray-400 mb-1">Order Number</p>
              <h1 className="text-lg font-black text-gray-900 font-mono">
                {order.order_number}
              </h1>
              <p className="text-xs text-gray-500 mt-1">
                Placed on {formatDateTime(order.placed_at)}
              </p>
              {order.cancelled_at && (
                <p className="text-xs text-red-500 mt-0.5">
                  Cancelled on {formatDateTime(order.cancelled_at)}
                </p>
              )}
            </div>
            <StatusBadge status={order.status} />
          </div>
        </div>

        {/* Status tracker */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-black text-gray-700 mb-5">
            Order Status
          </h2>
          <OrderStatusTracker status={order.status} />
        </div>

        {/* Items */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-black text-gray-700 mb-2">
            Items Ordered ({order.items?.length ?? 0})
          </h2>
          <div>
            {order.items?.map((item) => (
              <OrderItemRow key={item.id} item={item} />
            ))}
          </div>
        </div>

        {/* Delivery address */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-black text-gray-700 mb-4 flex items-center gap-2">
            <MapPin size={14} className="text-gray-400" />
            Delivery Address
          </h2>
          {order.shipping_address && (
            <div className="text-sm text-gray-600 space-y-0.5">
              <p className="font-bold text-gray-800">
                {order.shipping_address.full_name}
              </p>
              <p>{order.shipping_address.address_line1}</p>
              {order.shipping_address.address_line2 && (
                <p>{order.shipping_address.address_line2}</p>
              )}
              <p>
                {order.shipping_address.city},{" "}
                {order.shipping_address.province}{" "}
                — {order.shipping_address.postal_code}
              </p>
              <p>{order.shipping_address.country}</p>
              {order.shipping_address.phone && (
                <p className="text-gray-500 mt-1">
                  📞 {order.shipping_address.phone}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Payment + pricing */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-black text-gray-700 mb-4 flex items-center gap-2">
            <CreditCard size={14} className="text-gray-400" />
            Payment & Pricing
          </h2>

          <div className="flex items-center gap-3 mb-5 pb-4 border-b border-gray-100">
            <div>
              <p className="text-xs text-gray-500">Payment Method</p>
              <p className="text-sm font-bold text-gray-800 capitalize mt-0.5">
                {order.payment_method === "cod"
                  ? "Cash on Delivery"
                  : order.payment_method
                }
              </p>
            </div>
            <div className="ml-auto">
              <p className="text-xs text-gray-500">Payment Status</p>
              <p className="text-sm font-bold text-gray-800 mt-0.5">
                {order.payment_status}
              </p>
            </div>
          </div>

          <OrderPricingSummary order={order} />
        </div>

        {/* Tracking placeholder */}
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h2 className="text-sm font-black text-gray-700 mb-3">
            Tracking
          </h2>
          <p className="text-sm text-gray-400 italic">
            Tracking information will appear here once your order has been shipped.
          </p>
        </div>

        {/* Cancel action — only when is_cancellable */}
        {order.is_cancellable && (
          <div className="bg-white rounded-xl border border-gray-200 p-6">
            <h2 className="text-sm font-black text-gray-700 mb-2">
              Cancel Order
            </h2>
            <p className="text-xs text-gray-500 mb-4">
              You can cancel this order while it is still pending.
              Once confirmed, cancellation is no longer available.
            </p>
            <button
              onClick={handleCancelClick}
              disabled={isCancelling}
              className="border-2 border-red-200 text-red-600 rounded-xl
                         px-5 py-2.5 text-sm font-bold
                         hover:bg-red-50 hover:border-red-400 transition
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Cancel Order
            </button>
          </div>
        )}

      </div>
    </>
  )
}