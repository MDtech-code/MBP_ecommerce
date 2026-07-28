// src/pages/CheckoutPage/CheckoutPaymentPage.jsx

import { Link } from "react-router-dom"
import {
  ChevronRight, ChevronLeft, Loader2,
  AlertCircle, Package, MapPin, 
  Truck, CreditCard, ShieldCheck
} from "lucide-react"

import { useCheckoutPayment } from "@entities/checkout"

// ── Step indicator (reused pattern) ──────────────────────────────────────────
function CheckoutStepIndicator({ currentStep }) {
  const steps = [
    { key: "address", label: "Address" },
    { key: "payment", label: "Payment" },
  ]
  return (
    <div className="flex items-center gap-2 mb-6">
      {steps.map((step, idx) => {
        const isActive   = step.key === currentStep
        const isComplete = currentStep === "payment" && step.key === "address"
        return (
          <div key={step.key} className="flex items-center gap-2">
            <div className={`
              flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold
              ${isActive   ? "bg-primary text-white" : ""}
              ${isComplete ? "bg-green-100 text-green-700" : ""}
              ${!isActive && !isComplete ? "bg-gray-100 text-gray-400" : ""}
            `}>
              <span>{isComplete ? "✓" : idx + 1}</span>
              <span>{step.label}</span>
            </div>
            {idx < steps.length - 1 && (
              <ChevronRight size={14} className="text-gray-300" />
            )}
          </div>
        )
      })}
    </div>
  )
}

// ── Payment method card ───────────────────────────────────────────────────────
function PaymentMethodCard({ id, label, description, icon, isSelected, isDisabled, onSelect }) {
  return (
    <label className={`
      flex items-start gap-3 p-4 rounded-xl border-2 transition-all
      ${isDisabled
        ? "border-gray-100 bg-gray-50 opacity-60 cursor-not-allowed"
        : isSelected
          ? "border-primary bg-red-50 cursor-pointer"
          : "border-gray-200 bg-white hover:border-gray-300 cursor-pointer"
      }
    `}>
      <input
        type="radio"
        name="payment_method"
        value={id}
        checked={isSelected}
        disabled={isDisabled}
        onChange={() => !isDisabled && onSelect(id)}
        className="mt-0.5 accent-primary shrink-0"
      />
      <div className="flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-gray-800">{label}</span>
          {isDisabled && (
            <span className="text-xs bg-gray-100 text-gray-500
                             font-semibold px-2 py-0.5 rounded-full">
              Coming Soon
            </span>
          )}
        </div>
        {description && !isDisabled && (
          <p className="text-xs text-gray-500 mt-0.5">{description}</p>
        )}
      </div>
      <span className="text-xl shrink-0">{icon}</span>
    </label>
  )
}

// ── Order summary right column ────────────────────────────────────────────────
function CheckoutOrderSummary({ selectedItems, shippingFee, addressForm }) {
  const subtotal = selectedItems.reduce((sum, item) => {
    return sum + parseFloat(item.product_price) * item.quantity
  }, 0)

  const total = shippingFee !== null
    ? subtotal + shippingFee
    : subtotal

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit sticky top-6">
      <h3 className="font-black text-gray-900 mb-4">Order Summary</h3>

      {/* Items */}
      <div className="space-y-3 mb-4">
        {selectedItems.map((item) => (
          <div key={item.id} className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-50 rounded-lg border border-gray-100
                            flex items-center justify-center shrink-0 overflow-hidden">
              {item.product_image ? (
                <img
                  src={item.product_image}
                  alt={item.product_name}
                  className="w-full h-full object-contain"
                />
              ) : (
                <Package size={16} className="text-gray-300" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-semibold text-gray-800 line-clamp-1">
                {item.product_name}
              </p>
              <p className="text-xs text-gray-400">× {item.quantity}</p>
            </div>
            <span className="text-xs font-bold text-gray-800 shrink-0">
              Rs. {(parseFloat(item.product_price) * item.quantity)
                .toLocaleString("en-PK", { minimumFractionDigits: 0 })}
            </span>
          </div>
        ))}
      </div>

      <hr className="border-gray-100 mb-4" />

      {/* Pricing */}
      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between text-gray-600">
          <span>Subtotal ({selectedItems.length} items)</span>
          <span className="font-semibold text-gray-800">
            Rs. {subtotal.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
          </span>
        </div>
        <div className="flex justify-between text-gray-600">
          <span>Shipping to {addressForm.city}</span>
          <span className="font-semibold text-gray-800">
            Rs. {shippingFee ?? "—"}
          </span>
        </div>
      </div>

      <hr className="border-gray-100 mb-4" />

      <div className="flex justify-between items-center mb-5">
        <span className="font-black text-gray-900">Total</span>
        <span className="text-primary font-black text-xl">
          Rs. {total.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
        </span>
      </div>

      {/* Delivery address snapshot */}
      <div className="bg-gray-50 rounded-lg p-3 border border-gray-100">
        <div className="flex items-start gap-2">
          <MapPin size={13} className="text-gray-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-xs font-bold text-gray-700 mb-0.5">
              Delivering to
            </p>
            <p className="text-xs text-gray-600">{addressForm.full_name}</p>
            <p className="text-xs text-gray-500">
              {addressForm.address_line1}
              {addressForm.address_line2 && `, ${addressForm.address_line2}`}
            </p>
            <p className="text-xs text-gray-500">
              {addressForm.city}, {addressForm.province} — {addressForm.postal_code}
            </p>
            {addressForm.phone && (
              <p className="text-xs text-gray-400 mt-1">📞 {addressForm.phone}</p>
            )}
          </div>
        </div>
        <Link
          to="/checkout/address"
          className="text-xs text-primary font-bold hover:text-red-700
                     transition mt-2 inline-block"
        >
          Edit Address
        </Link>
      </div>

    </div>
  )
}

// ── Error code → user message ─────────────────────────────────────────────────
function getErrorDisplay(errorMessage, errorCode) {
  const codeMessages = {
    cart_empty:           "Your cart is empty. Please return to cart.",
    product_unavailable:  "Some items are no longer available. Please update your cart.",
    insufficient_stock:   errorMessage,
    coupon_invalid:       "Your coupon is no longer valid. Try removing it from your cart.",
    coupon_already_used:  "You have already used this coupon.",
    coupon_limit_reached: "This coupon's usage limit has been reached.",
    coupon_expired:       "This coupon has expired.",
    invalid_cart_items:   "Some selected items are invalid. Please return to cart.",
  }
  return codeMessages[errorCode] ?? errorMessage ?? "Something went wrong. Please try again."
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CheckoutPaymentPage() {
  const {
    paymentMethod,
    notes,
    addressForm,
    shippingFee,
    selectedItems,
    setPaymentMethod,
    setNotes,
    handlePlaceOrder,
    isPlacing,
    errorMessage,
    errorCode,
  } = useCheckoutPayment()

  const errorDisplay = (errorMessage || errorCode)
    ? getErrorDisplay(errorMessage, errorCode)
    : null

  return (
    <div className="bg-gray-50 min-h-screen">
      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500 mb-5 flex items-center gap-2">
          <Link to="/" className="hover:text-primary transition-colors">Home</Link>
          <span>›</span>
          <Link to="/cart" className="hover:text-primary transition-colors">Cart</Link>
          <span>›</span>
          <Link to="/checkout/address" className="hover:text-primary transition-colors">
            Address
          </Link>
          <span>›</span>
          <span className="text-gray-800">Payment</span>
        </nav>

        <h1 className="text-2xl font-black text-gray-900 mb-2">Checkout</h1>

        {/* Step indicator */}
        <CheckoutStepIndicator currentStep="payment" />

        {/* Two column layout */}
        <div className="grid lg:grid-cols-5 gap-6 items-start">

          {/* ── Left column ──────────────────────────────────────────────── */}
          <div className="lg:col-span-3 space-y-4">

            {/* Payment method */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-black text-gray-900 mb-4 flex items-center gap-2">
                <CreditCard size={16} className="text-gray-500" />
                Payment Method
              </h2>

              <div className="space-y-3">
                <PaymentMethodCard
                  id="cod"
                  label="Cash on Delivery"
                  description="Pay when your order arrives at your door"
                  icon="💵"
                  isSelected={paymentMethod === "cod"}
                  isDisabled={false}
                  onSelect={setPaymentMethod}
                />

                {/* COD confirmation note */}
                {paymentMethod === "cod" && (
                  <div className="flex items-start gap-2 bg-blue-50 border
                                  border-blue-100 rounded-lg px-3 py-2.5">
                    <span className="text-blue-500 shrink-0 mt-0.5">ℹ️</span>
                    <p className="text-xs text-blue-700">
                      Our team will call you to confirm your order.
                      Please ensure your phone is reachable.
                    </p>
                  </div>
                )}

                <PaymentMethodCard
                  id="jazzcash"
                  label="JazzCash"
                  icon="📱"
                  isSelected={false}
                  isDisabled={true}
                  onSelect={() => {}}
                />
                <PaymentMethodCard
                  id="easypaisa"
                  label="Easypaisa"
                  icon="💚"
                  isSelected={false}
                  isDisabled={true}
                  onSelect={() => {}}
                />
                <PaymentMethodCard
                  id="safepay"
                  label="Safepay"
                  icon="🔐"
                  isSelected={false}
                  isDisabled={true}
                  onSelect={() => {}}
                />
                <PaymentMethodCard
                  id="bank"
                  label="Bank Transfer"
                  icon="🏦"
                  isSelected={false}
                  isDisabled={true}
                  onSelect={() => {}}
                />
              </div>
            </div>

            {/* Delivery notes */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-black text-gray-900 mb-1 flex items-center gap-2">
                <Truck size={16} className="text-gray-500" />
                Delivery Notes
                <span className="text-xs font-normal text-gray-400">(Optional)</span>
              </h2>
              <p className="text-xs text-gray-400 mb-3">
                Any special instructions for delivery?
              </p>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                maxLength={500}
                rows={3}
                placeholder="e.g. Please ring the bell twice. Leave at gate if not home."
                className="w-full border border-gray-200 rounded-lg px-3 py-2.5
                           text-sm text-gray-800 placeholder-gray-400
                           focus:outline-none focus:ring-2 focus:ring-primary
                           focus:border-transparent resize-none"
              />
              <p className="text-xs text-gray-400 text-right mt-1">
                {notes.length}/500
              </p>
            </div>

            {/* Error banner */}
            {errorDisplay && (
              <div className="flex items-start gap-3 bg-red-50 border border-red-200
                              rounded-xl px-4 py-3">
                <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm font-bold text-red-700">Order failed</p>
                  <p className="text-sm text-red-600 mt-0.5">{errorDisplay}</p>
                  {(errorCode === "cart_empty" || errorCode === "invalid_cart_items") && (
                    <Link
                      to="/cart"
                      className="text-xs font-bold text-red-700 underline mt-1 inline-block"
                    >
                      Return to Cart
                    </Link>
                  )}
                  {(errorCode === "product_unavailable" ||
                    errorCode === "insufficient_stock") && (
                    <Link
                      to="/cart"
                      className="text-xs font-bold text-red-700 underline mt-1 inline-block"
                    >
                      Update Cart
                    </Link>
                  )}
                </div>
              </div>
            )}

            {/* Action buttons */}
            <div className="flex items-center gap-3">
              <Link
                to="/checkout/address"
                className="flex items-center gap-2 border border-gray-300
                           rounded-xl px-5 py-3 text-sm font-bold text-gray-700
                           hover:border-gray-400 transition shrink-0"
              >
                <ChevronLeft size={15} />
                Back
              </Link>

              <button
                type="button"
                onClick={handlePlaceOrder}
                disabled={isPlacing}
                className="flex-1 bg-primary text-white py-3 rounded-xl
                           font-black text-sm hover:bg-red-700 transition
                           disabled:opacity-50 disabled:cursor-not-allowed
                           flex items-center justify-center gap-2"
              >
                {isPlacing ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Placing Order...
                  </>
                ) : (
                  <>
                    <ShieldCheck size={16} />
                    Place Order
                  </>
                )}
              </button>
            </div>

            <p className="text-xs text-gray-400 text-center">
              🔒 Your order is protected. You only pay on delivery.
            </p>

          </div>

          {/* ── Right column — Order summary ──────────────────────────────── */}
          <div className="lg:col-span-2">
            <CheckoutOrderSummary
              selectedItems={selectedItems}
              shippingFee={shippingFee}
              addressForm={addressForm}
            />
          </div>

        </div>
      </div>
    </div>
  )
}