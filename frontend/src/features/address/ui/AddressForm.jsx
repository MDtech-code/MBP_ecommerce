// src/features/address/ui/AddressForm.jsx

import { X, Save, MapPin } from "lucide-react"
import { FormField } from "@shared/ui"
import { AlertBanner } from "@shared/ui"
import { useAddressForm } from "../model/useAddressForm"

import {LABEL_OPTIONS,CITY_GROUPS} from "../data/countryOptions"







const selectClass = (error) => `
  w-full border rounded-lg px-3 py-2.5 text-sm outline-none transition-colors
  bg-transparent dark:bg-transparent
  text-gray-800 dark:text-white
  focus:border-primary focus:ring-1 focus:ring-primary/20
  ${error
    ? "border-red-400 dark:border-red-500"
    : "border-gray-200 dark:border-gray-700"
  }
`

export default function AddressForm({ existingAddress = null, onCancel }) {
  const {
    form,
    fieldErrors,
    formError,
    isPending,
    isEditing,
    postalPreview,
    handleChange,
    handleSubmit,
  } = useAddressForm(existingAddress, onCancel)

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Header */}
      <div className="bg-white dark:bg-[#0a0a0a] rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-black text-gray-900 dark:text-gray-100">
            {isEditing ? "Edit Address" : "Add New Address"}
          </h2>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="flex items-center gap-2 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <X size={14} />
              CANCEL
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="flex items-center gap-2 bg-primary text-white px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:opacity-90 transition-opacity disabled:opacity-60 disabled:cursor-not-allowed"
            >
              <Save size={14} />
              {isPending ? "SAVING..." : "SAVE ADDRESS"}
            </button>
          </div>
        </div>

        
        {formError && (
          <AlertBanner type="error" className="mt-4">
            {formError}
          </AlertBanner>
        )}
      </div>

      {/* Fields */}
      <div className="bg-white dark:bg-[#0a0a0a] rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          {/* Label / Address Type */}
          <FormField label="Address Type" name="label" error={fieldErrors.label}>
            <select
              name="label"
              value={form.label}
              onChange={handleChange}
              className={selectClass(fieldErrors.label)}
            >
              {LABEL_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}
                  className="bg-white dark:bg-gray-900">
                  {label}
                </option>
              ))}
            </select>
          </FormField>

          {/* City */}
          <FormField label="City" name="city" error={fieldErrors.city}>
            <select
              name="city"
              value={form.city}
              onChange={handleChange}
              className={selectClass(fieldErrors.city)}
            >
              <option value="">Select your city</option>
              {CITY_GROUPS.map(({ label, values }) => (
                <optgroup key={label} label={label}>
                  {values.map(({ value, label: cityLabel }) => (
                    <option key={value} value={value}
                      className="bg-white dark:bg-gray-900">
                      {cityLabel}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </FormField>

          
          <FormField label="Postal Code">
            <div className="flex items-center gap-2 w-full border border-gray-100 dark:border-gray-700 rounded-lg px-3 py-2.5 bg-gray-50 dark:bg-gray-800/40">
              <MapPin size={14} className="text-gray-300 dark:text-gray-600 shrink-0" />
              <span className={`text-sm ${form.city ? "text-gray-700 dark:text-gray-200 font-semibold" : "text-gray-300 dark:text-gray-600"}`}>
                {postalPreview}
              </span>
              {form.city && (
                <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
                  Auto-filled
                </span>
              )}
            </div>
          </FormField>

          {/* Country — fixed */}
          <FormField label="Country">
            <div className="flex items-center gap-2 w-full border border-gray-100 dark:border-gray-700 rounded-lg px-3 py-2.5 bg-gray-50 dark:bg-gray-800/40">
              <span className="text-sm text-gray-700 dark:text-gray-200 font-semibold">
                🇵🇰 Pakistan
              </span>
              <span className="ml-auto text-xs text-gray-400 dark:text-gray-500">
                Fixed
              </span>
            </div>
          </FormField>

          {/* Phone */}
          <FormField
            label="Phone Number"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            error={fieldErrors.phone}
          />

          {/* Address Line 1 */}
          <div className="sm:col-span-2">
            <FormField
              label="Street Address"
              name="address_line1"
              value={form.address_line1}
              onChange={handleChange}
              error={fieldErrors.address_line1}
            />
          </div>

          {/* Address Line 2 */}
          <div className="sm:col-span-2">
            <FormField
              label="Apartment / Floor / Area (Optional)"
              name="address_line2"
              value={form.address_line2}
              onChange={handleChange}
              error={fieldErrors.address_line2}
            />
          </div>

        </div>
      </div>

    </form>
  )
}

