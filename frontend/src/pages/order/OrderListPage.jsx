// src/pages/OrderListPage/OrderListPage.jsx

import { Link } from "react-router-dom"
import { Package, ChevronRight } from "lucide-react"
import { Pagination } from "@shared/ui"
import { useOrderList } from "@features/order"

// ── Status badge config ───────────────────────────────────────────────────────
const STATUS_STYLES = {
  pending:    "bg-yellow-100 text-yellow-800",
  confirmed:  "bg-blue-100 text-blue-800",
  processing: "bg-indigo-100 text-indigo-800",
  shipped:    "bg-purple-100 text-purple-800",
  delivered:  "bg-green-100 text-green-800",
  cancelled:  "bg-red-100 text-red-800",
  refunded:   "bg-gray-100 text-gray-700",
}

function StatusBadge({ status }) {
  const styles = STATUS_STYLES[status] ?? "bg-gray-100 text-gray-600"
  return (
    <span className={`
      inline-flex items-center px-2.5 py-0.5 rounded-full
      text-xs font-bold uppercase tracking-wide
      ${styles}
    `}>
      {status}
    </span>
  )
}

// ── Format date from placed_at ────────────────────────────────────────────────
function formatDate(dateString) {
  if (!dateString) return "—"
  return new Date(dateString).toLocaleDateString("en-PK", {
    day:   "numeric",
    month: "short",
    year:  "numeric",
  })
}

// ── Order card ────────────────────────────────────────────────────────────────
function OrderCard({ order }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5
                    hover:border-gray-300 transition-colors">
      <div className="flex items-start justify-between gap-4">

        {/* Left — order info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-3 flex-wrap mb-2">
            <StatusBadge status={order.status} />
            <span className="text-sm font-bold text-gray-800 font-mono">
              {order.order_number}
            </span>
          </div>

          <div className="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
            <span>📅 {formatDate(order.placed_at)}</span>
            <span>·</span>
            <span>
              {order.item_count} item{order.item_count !== 1 ? "s" : ""}
            </span>
            {order.city && (
              <>
                <span>·</span>
                <span>{order.city}, {order.province}</span>
              </>
            )}
          </div>
        </div>

        {/* Right — total + link */}
        <div className="flex flex-col items-end gap-2 shrink-0">
          <span className="text-base font-black text-primary">
            Rs. {parseFloat(order.total_price).toLocaleString("en-PK", {
              minimumFractionDigits: 0,
            })}
          </span>
          <Link
            to={`/orders/${order.order_number}`}
            className="flex items-center gap-1 text-xs font-bold text-gray-600
                       hover:text-primary transition-colors"
          >
            View Order
            <ChevronRight size={13} />
          </Link>
        </div>

      </div>
    </div>
  )
}

// ── Loading skeleton ──────────────────────────────────────────────────────────
function OrderCardSkeleton() {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 animate-pulse">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 space-y-2">
          <div className="flex gap-3">
            <div className="h-5 w-20 bg-gray-100 rounded-full" />
            <div className="h-5 w-40 bg-gray-100 rounded" />
          </div>
          <div className="h-4 w-56 bg-gray-100 rounded" />
        </div>
        <div className="space-y-2">
          <div className="h-5 w-24 bg-gray-100 rounded" />
          <div className="h-4 w-20 bg-gray-100 rounded" />
        </div>
      </div>
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyOrders() {
  return (
    <div className="flex flex-col items-center justify-center
                    py-24 text-center bg-white rounded-xl border border-gray-200">
      <Package size={48} className="text-gray-200 mb-4" />
      <p className="font-bold text-gray-700 text-lg mb-2">No orders yet</p>
      <p className="text-sm text-gray-500 mb-6">
        Browse our products and place your first order.
      </p>
      <Link
        to="/product"
        className="bg-primary text-white px-6 py-3 rounded-lg
                   font-bold text-sm hover:bg-red-700 transition"
      >
        Start Shopping
      </Link>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function OrderListPage() {
  const {
    orders,
    meta,
    isLoading,
    isFetching,
    isError,
    errorMessage,
    
    setPage,
  } = useOrderList()

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-2xl font-black text-gray-900">My Orders</h1>
        <p className="text-sm text-gray-500 mt-1">
          Track and manage your orders
        </p>
      </div>

      {/* Error */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-xl
                        px-4 py-3 text-sm text-red-600">
          {errorMessage ?? "Failed to load orders. Please try again."}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <OrderCardSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Orders list */}
      {!isLoading && !isError && (
        <>
          {orders.length === 0 ? (
            <EmptyOrders />
          ) : (
            <div className={`space-y-3 ${
              isFetching ? "opacity-60 transition-opacity duration-200" : ""
            }`}>
              {orders.map((order) => (
                <OrderCard key={order.order_number} order={order} />
              ))}
            </div>
          )}

          {/* Pagination */}
          <Pagination
            currentPage={meta.page          ?? 1}
            totalPages={meta.total_pages    ?? 1}
            hasNext={meta.has_next          ?? false}
            hasPrevious={meta.has_previous  ?? false}
            onPageChange={setPage}
          />
        </>
      )}

    </div>
  )
}