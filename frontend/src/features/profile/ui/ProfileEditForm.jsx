// src/components/profile/ProfileEditForm.jsx
import { X, Save } from "lucide-react"

import { FormField } from "@shared/ui/FormField"

import { useProfileForm } from "../../../features/profile/model/useProfileForm"

const GENDER_OPTIONS = [
  { value: "",  label: "Select gender" },
  { value: "M", label: "Male" },
  { value: "F", label: "Female" },
  { value: "O", label: "Other" },
  { value: "N", label: "Prefer not to say" },
]



export default function ProfileEditForm({ onCancel }) {
  const {
    form,
    fieldErrors,
    formError,
    isPending,
    handleChange,
    handleSubmit,
  } = useProfileForm(onCancel)

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Header */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black text-gray-900">Edit Profile</h2>
            <p className="text-gray-400 text-sm mt-1">
              Update your personal information
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="flex items-center gap-2 border border-gray-200 text-gray-600 px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-gray-50 transition-colors"
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
              {isPending ? "SAVING..." : "SAVE CHANGES"}
            </button>
          </div>
        </div>

        {formError && (
          <div
            role="alert"
            className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2"
          >
            {formError}
          </div>
        )}
      </div>

      {/* Personal Info */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-5">
          Personal Information
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          <FormField
            label="Phone Number"
            name="phone"
            value={form.phone}
            onChange={handleChange}
            error={fieldErrors.phone}
          />

          <FormField
            label="Date of Birth"
            name="date_of_birth"
            type="date"
            value={form.date_of_birth}
            onChange={handleChange}
            error={fieldErrors.date_of_birth}
          />

          <FormField
            label="Gender"
            name="gender"
            error={fieldErrors.gender}
          >
            <select
              name="gender"
              value={form.gender}
              onChange={handleChange}
              className={`
                w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
                outline-none transition-colors bg-white
                focus:border-primary focus:ring-1 focus:ring-primary/20
                ${fieldErrors.gender ? "border-red-400" : "border-gray-200"}
              `}
            >
              {GENDER_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </FormField>

        </div>
      </div>

      {/* Address section removed — managed via AddressManager component */}
      <div className="bg-gray-50 rounded-2xl border border-dashed border-gray-200 p-5 text-center">
        <p className="text-sm text-gray-400">
          Manage your shipping addresses separately from the
          <span className="font-semibold text-primary"> Addresses </span>
          section on your profile.
        </p>
      </div>

    </form>
  )
}