// src/pages/CheckoutPage/CheckoutAddressPage.jsx

import { useState } from "react"
import { Link } from "react-router-dom"
import {
  MapPin, Home, Briefcase, Plus, ChevronRight,
  Loader2, AlertCircle, Package,
} from "lucide-react"

import { FormField } from "@shared/ui/FormField"
import { useCheckoutAddress } from "@entities/checkout"
import { useCreateAddress } from "@features/address"
import { normalizeError } from "@shared/api"
import {
  CITY_POSTAL_MAP,
  getProvinceForCity,
} from "@shared/lib/locationData"

// ── City grouped dropdown data ────────────────────────────────────────────────
const CITY_GROUPS = [
  {
    label: "Punjab",
    cities: [
      "Lahore", "Faisalabad", "Rawalpindi", "Gujranwala", "Multan",
      "Sialkot", "Bahawalpur", "Sargodha", "Sheikhupura", "Gujrat",
      "Rahim Yar Khan", "Jhang", "Sahiwal", "Okara", "Kasur",
    ],
  },
  {
    label: "Sindh",
    cities: ["Karachi", "Hyderabad", "Sukkur", "Larkana", "Nawabshah", "Mirpur Khas"],
  },
  {
    label: "KPK",
    cities: ["Peshawar", "Abbottabad", "Mardan", "Swat", "Kohat", "Mingora"],
  },
  {
    label: "Balochistan",
    cities: ["Quetta", "Turbat", "Khuzdar"],
  },
  {
    label: "Federal / AJK / GB",
    cities: ["Islamabad", "Muzaffarabad", "Gilgit"],
  },
]

const LABEL_OPTIONS = [
  { value: "home",   label: "🏠 Home" },
  { value: "office", label: "🏢 Office" },
  { value: "other",  label: "📍 Other" },
]

// ── Label icon helper ─────────────────────────────────────────────────────────
function AddressLabelIcon({ label }) {
  if (label === "home")   return <Home size={15} className="text-primary shrink-0" />
  if (label === "office") return <Briefcase size={15} className="text-primary shrink-0" />
  return <MapPin size={15} className="text-primary shrink-0" />
}

// ── Step indicator ────────────────────────────────────────────────────────────
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
              <span>{idx + 1}</span>
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

// ── Order summary right column ────────────────────────────────────────────────
function CheckoutOrderSummary({ selectedItems, shippingFee, addressCity }) {
  const subtotal = selectedItems.reduce((sum, item) => {
    return sum + parseFloat(item.product_price) * item.quantity
  }, 0)

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit sticky top-6">
      <h3 className="font-black text-gray-900 mb-4">Order Summary</h3>

      {/* Items list */}
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
              <p className="text-xs text-gray-400">
                × {item.quantity}
              </p>
            </div>
            <span className="text-xs font-bold text-gray-800 shrink-0">
              Rs. {(parseFloat(item.product_price) * item.quantity)
                .toLocaleString("en-PK", { minimumFractionDigits: 0 })}
            </span>
          </div>
        ))}
      </div>

      <hr className="border-gray-100 mb-4" />

      {/* Pricing rows */}
      <div className="space-y-2 text-sm">
        <div className="flex justify-between text-gray-600">
          <span>Subtotal ({selectedItems.length} items)</span>
          <span className="font-semibold text-gray-800">
            Rs. {subtotal.toLocaleString("en-PK", { minimumFractionDigits: 2 })}
          </span>
        </div>

        <div className="flex justify-between text-gray-600">
          <span>
            {addressCity
              ? `Shipping to ${addressCity}`
              : "Shipping"
            }
          </span>
          {shippingFee !== null ? (
            <span className="font-semibold text-gray-800">
              Rs. {shippingFee}
            </span>
          ) : (
            <span className="text-gray-400 italic text-xs mt-0.5">
              Select city to calculate
            </span>
          )}
        </div>
      </div>

      <hr className="border-gray-100 my-4" />

      <div className="flex justify-between items-center">
        <div>
          <span className="font-black text-gray-900">Total</span>
          {shippingFee === null && (
            <p className="text-xs text-gray-400">Excl. shipping</p>
          )}
        </div>
        <span className="text-primary font-black text-xl">
          Rs. {shippingFee !== null
            ? (subtotal + shippingFee).toLocaleString("en-PK", { minimumFractionDigits: 2 })
            : subtotal.toLocaleString("en-PK", { minimumFractionDigits: 2 })
          }
        </span>
      </div>
    </div>
  )
}

// ── Inline new address form ────────────────────────────────────────────────────
// Writes directly to checkoutStore via handleAddressFieldChange.
// Does NOT use useAddressForm hook — that hook is for saved address CRUD.
// This form populates checkout addressForm fields in real time.
function InlineNewAddressForm({ addressForm, onFieldChange, onSaveNew, isSavingNew, saveError }) {
  const postalPreview   = addressForm.city ? CITY_POSTAL_MAP[addressForm.city] || "—" : "—"
  const provincePreview = addressForm.city ? getProvinceForCity(addressForm.city) || "—" : "—"

  return (
    <div className="border border-gray-200 rounded-xl p-5 bg-gray-50 space-y-4">
      <h4 className="text-sm font-bold text-gray-700">New Delivery Address</h4>

      {saveError && (
        <div className="flex items-start gap-2 bg-red-50 border border-red-200
                        rounded-lg px-3 py-2.5 text-xs text-red-600">
          <AlertCircle size={13} className="shrink-0 mt-0.5" />
          {saveError}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

        {/* Full Name */}
        <FormField
          label="Full Name"
          name="full_name"
          value={addressForm.full_name}
          onChange={(e) => onFieldChange("full_name", e.target.value)}
        />

        {/* Phone */}
        <FormField
          label="Phone Number"
          name="phone"
          value={addressForm.phone}
          onChange={(e) => onFieldChange("phone", e.target.value)}
        />

        {/* Address Line 1 — full width */}
        <div className="sm:col-span-2">
          <FormField
            label="Street Address"
            name="address_line1"
            value={addressForm.address_line1}
            onChange={(e) => onFieldChange("address_line1", e.target.value)}
          />
        </div>

        {/* Address Line 2 — full width, optional */}
        <div className="sm:col-span-2">
          <FormField
            label="Apartment / Floor / Landmark (Optional)"
            name="address_line2"
            value={addressForm.address_line2}
            onChange={(e) => onFieldChange("address_line2", e.target.value)}
          />
        </div>

        {/* City — grouped dropdown */}
        <FormField label="City" name="city">
          <select
            name="city"
            value={addressForm.city}
            onChange={(e) => onFieldChange("city", e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5
                       text-sm text-gray-800 outline-none bg-white
                       focus:border-primary focus:ring-1 focus:ring-primary/20"
          >
            <option value="">Select city</option>
            {CITY_GROUPS.map(({ label, cities }) => (
              <optgroup key={label} label={label}>
                {cities.map((city) => (
                  <option key={city} value={city}>{city}</option>
                ))}
              </optgroup>
            ))}
          </select>
        </FormField>

        {/* Province — auto-derived, read only */}
        <FormField label="Province">
          <div className="flex items-center gap-2 w-full border border-gray-100
                          rounded-lg px-3 py-2.5 bg-white">
            <span className={`text-sm ${addressForm.city ? "text-gray-700 font-semibold" : "text-gray-300"}`}>
              {addressForm.city ? provincePreview : "Auto-filled from city"}
            </span>
            {addressForm.city && (
              <span className="ml-auto text-xs text-gray-400">Auto</span>
            )}
          </div>
        </FormField>

        {/* Postal Code — auto-derived, read only */}
        <FormField label="Postal Code">
          <div className="flex items-center gap-2 w-full border border-gray-100
                          rounded-lg px-3 py-2.5 bg-white">
            <MapPin size={13} className="text-gray-300 shrink-0" />
            <span className={`text-sm ${addressForm.city ? "text-gray-700 font-semibold" : "text-gray-300"}`}>
              {addressForm.city ? postalPreview : "Auto-filled from city"}
            </span>
            {addressForm.city && (
              <span className="ml-auto text-xs text-gray-400">Auto</span>
            )}
          </div>
        </FormField>

        {/* Label */}
        <FormField label="Address Label">
          <select
            value={addressForm.label || "home"}
            onChange={(e) => onFieldChange("label", e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2.5
                       text-sm text-gray-800 outline-none bg-white
                       focus:border-primary focus:ring-1 focus:ring-primary/20"
          >
            {LABEL_OPTIONS.map(({ value, label }) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </FormField>

      </div>

      {/* Save to account option */}
      <div className="pt-2 flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Province and postal code are auto-filled from your city selection.
        </p>
        <button
          type="button"
          onClick={onSaveNew}
          disabled={isSavingNew}
          className="flex items-center gap-1.5 text-xs font-bold text-primary
                     hover:text-red-700 transition disabled:opacity-50
                     disabled:cursor-not-allowed"
        >
          {isSavingNew
            ? <Loader2 size={12} className="animate-spin" />
            : null
          }
          {isSavingNew ? "Saving..." : "Save to my addresses"}
        </button>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function CheckoutAddressPage() {
  const {
    addresses,
    isLoading,
    isError,
    addressMode,
    selectedAddressId,
    addressForm,
    shippingFee,
    isAddressComplete,
    selectedItems,
    handleSelectSavedAddress,
    handleSwitchToNew,
    handleSwitchToSaved,
    handleAddressFieldChange,
    handleContinueToPayment,
  } = useCheckoutAddress()

  // ── Save new address to account (optional action) ─────────────────────────
  // Separate from checkout flow — user can proceed without saving.
  // Saving is convenience only — address is already in checkoutStore.
  const createAddressMutation = useCreateAddress()
  const [savedSuccess, setSavedSuccess] = useState(false)

  const handleSaveNewToAccount = () => {
    const { full_name: _fn, ...addressData } = addressForm
    createAddressMutation.mutate(
      {
        label:         addressData.label || "home",
        address_line1: addressData.address_line1,
        address_line2: addressData.address_line2 || "",
        city:          addressData.city,
        phone:         addressData.phone || "",
      },
      {
        onSuccess: () => setSavedSuccess(true),
      }
    )
  }

  const createError = createAddressMutation.error
    ? normalizeError(createAddressMutation.error).message
    : null

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-5xl mx-auto px-6 py-8">
          <div className="grid lg:grid-cols-5 gap-6">
            <div className="lg:col-span-3 space-y-4">
              {[...Array(2)].map((_, i) => (
                <div key={i} className="bg-white rounded-xl border border-gray-200
                                        p-5 animate-pulse h-24" />
              ))}
            </div>
            <div className="lg:col-span-2 bg-white rounded-xl border
                            border-gray-200 p-6 animate-pulse h-64" />
          </div>
        </div>
      </div>
    )
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="bg-gray-50 min-h-screen flex items-center justify-center">
        <div className="text-center py-24">
          <p className="text-4xl mb-4">⚠️</p>
          <p className="font-bold text-gray-700 mb-2">Failed to load addresses</p>
          <p className="text-sm text-gray-500 mb-6">Please try again.</p>
          <button
            onClick={() => window.location.reload()}
            className="bg-primary text-white px-6 py-3 rounded-lg
                       font-bold text-sm hover:bg-red-700 transition"
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-50 min-h-screen">
      <div className="max-w-5xl mx-auto px-6 py-8">

        {/* Breadcrumb */}
        <nav className="text-sm text-gray-500 mb-5 flex items-center gap-2">
          <Link to="/" className="hover:text-primary transition-colors">Home</Link>
          <span>›</span>
          <Link to="/cart" className="hover:text-primary transition-colors">Cart</Link>
          <span>›</span>
          <span className="text-gray-800">Checkout</span>
        </nav>

        <h1 className="text-2xl font-black text-gray-900 mb-2">Checkout</h1>

        {/* Step indicator */}
        <CheckoutStepIndicator currentStep="address" />

        {/* Two column layout */}
        <div className="grid lg:grid-cols-5 gap-6 items-start">

          {/* ── Left column — Address selection ──────────────────────────── */}
          <div className="lg:col-span-3 space-y-4">

            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h2 className="text-base font-black text-gray-900 mb-4">
                Delivery Address
              </h2>

              {/* Saved addresses list */}
              {addresses.length > 0 && addressMode === "saved" && (
                <div className="space-y-3 mb-4">
                  {addresses.map((address) => (
                    <label
                      key={address.id}
                      className={`
                        flex items-start gap-3 p-4 rounded-xl border-2 cursor-pointer
                        transition-all
                        ${selectedAddressId === address.id
                          ? "border-primary bg-red-50"
                          : "border-gray-200 hover:border-gray-300 bg-white"
                        }
                      `}
                    >
                      {/* Radio */}
                      <input
                        type="radio"
                        name="selected_address"
                        checked={selectedAddressId === address.id}
                        onChange={() => handleSelectSavedAddress(address)}
                        className="mt-0.5 accent-primary shrink-0"
                      />

                      {/* Address details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <AddressLabelIcon label={address.label} />
                          <span className="text-sm font-bold text-gray-800 capitalize">
                            {address.label_display}
                          </span>
                          {address.is_default && (
                            <span className="text-xs bg-green-100 text-green-700
                                             font-semibold px-2 py-0.5 rounded-full">
                              Default
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600">
                          {address.address_line1}
                          {address.address_line2 && `, ${address.address_line2}`}
                        </p>
                        <p className="text-sm text-gray-500">
                          {address.city}, {address.province_display} — {address.postal_code}
                        </p>
                        {address.phone && (
                          <p className="text-xs text-gray-400 mt-1">
                            📞 {address.phone}
                          </p>
                        )}
                      </div>
                    </label>
                  ))}
                </div>
              )}

              {/* Add new address toggle */}
              {addressMode === "saved" && (
                <button
                  type="button"
                  onClick={handleSwitchToNew}
                  className="flex items-center gap-2 text-sm font-bold text-primary
                             hover:text-red-700 transition mt-2"
                >
                  <Plus size={15} />
                  Add New Address
                </button>
              )}

              {/* New address form */}
              {addressMode === "new" && (
                <>
                  <InlineNewAddressForm
                    addressForm={addressForm}
                    onFieldChange={handleAddressFieldChange}
                    onSaveNew={handleSaveNewToAccount}
                    isSavingNew={createAddressMutation.isPending}
                    saveError={createError}
                  />

                  {savedSuccess && (
                    <p className="text-xs text-green-600 font-semibold mt-2">
                      ✓ Address saved to your account
                    </p>
                  )}

                  {/* Back to saved — only if saved addresses exist */}
                  {addresses.length > 0 && (
                    <button
                      type="button"
                      onClick={handleSwitchToSaved}
                      className="flex items-center gap-2 text-sm font-bold
                                 text-gray-500 hover:text-gray-700 transition mt-3"
                    >
                      ← Use saved address
                    </button>
                  )}
                </>
              )}
            </div>

            {/* Full name field — always shown, separate from address card */}
            {/* Shown when saved address selected — full_name not on UserAddress */}
            {addressMode === "saved" && selectedAddressId && (
              <div className="bg-white rounded-xl border border-gray-200 p-6">
                <h3 className="text-sm font-bold text-gray-700 mb-4">
                  Recipient Details
                </h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <FormField
                    label="Full Name"
                    name="full_name"
                    value={addressForm.full_name}
                    onChange={(e) =>
                      handleAddressFieldChange("full_name", e.target.value)
                    }
                  />
                  <FormField
                    label="Phone Number"
                    name="phone"
                    value={addressForm.phone}
                    onChange={(e) =>
                      handleAddressFieldChange("phone", e.target.value)
                    }
                  />
                </div>
                <p className="text-xs text-gray-400 mt-3">
                  This name and phone will appear on your delivery.
                </p>
              </div>
            )}

            {/* Continue button */}
            <button
              type="button"
              onClick={handleContinueToPayment}
              disabled={!isAddressComplete}
              className="w-full bg-primary text-white py-3.5 rounded-xl
                         font-black text-sm hover:bg-red-700 transition
                         disabled:opacity-50 disabled:cursor-not-allowed
                         flex items-center justify-center gap-2"
            >
              {isAddressComplete
                ? <>Continue to Payment <ChevronRight size={16} /></>
                : "Complete address to continue"
              }
            </button>

          </div>

          {/* ── Right column — Order summary ──────────────────────────────── */}
          <div className="lg:col-span-2">
            <CheckoutOrderSummary
              selectedItems={selectedItems}
              shippingFee={shippingFee}
              addressCity={addressForm.city}
            />
          </div>

        </div>
      </div>
    </div>
  )
}