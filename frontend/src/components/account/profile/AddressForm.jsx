// src/components/account/profile/AddressForm.jsx

import { X, Save, MapPin } from "lucide-react"
import ProfileEditField from "./ProfileEditField"
import { useAddressForm } from "../../../hooks/account/useAddressForm"

const LABEL_OPTIONS = [
  { value: "home",   label: "🏠 Home" },
  { value: "office", label: "🏢 Office" },
  { value: "other",  label: "📍 Other" },
]

const CITY_OPTIONS = [
  { value: "",               label: "Select your city",   group: null },
  // Punjab
  { value: "Lahore",         label: "Lahore",             group: "Punjab" },
  { value: "Faisalabad",     label: "Faisalabad",         group: "Punjab" },
  { value: "Rawalpindi",     label: "Rawalpindi",         group: "Punjab" },
  { value: "Gujranwala",     label: "Gujranwala",         group: "Punjab" },
  { value: "Multan",         label: "Multan",             group: "Punjab" },
  { value: "Sialkot",        label: "Sialkot",            group: "Punjab" },
  { value: "Bahawalpur",     label: "Bahawalpur",         group: "Punjab" },
  { value: "Sargodha",       label: "Sargodha",           group: "Punjab" },
  { value: "Sheikhupura",    label: "Sheikhupura",        group: "Punjab" },
  { value: "Gujrat",         label: "Gujrat",             group: "Punjab" },
  { value: "Rahim Yar Khan", label: "Rahim Yar Khan",    group: "Punjab" },
  { value: "Jhang",          label: "Jhang",              group: "Punjab" },
  { value: "Sahiwal",        label: "Sahiwal",            group: "Punjab" },
  { value: "Okara",          label: "Okara",              group: "Punjab" },
  { value: "Kasur",          label: "Kasur",              group: "Punjab" },
  // Sindh
  { value: "Karachi",        label: "Karachi",            group: "Sindh" },
  { value: "Hyderabad",      label: "Hyderabad",          group: "Sindh" },
  { value: "Sukkur",         label: "Sukkur",             group: "Sindh" },
  { value: "Larkana",        label: "Larkana",            group: "Sindh" },
  { value: "Nawabshah",      label: "Nawabshah",          group: "Sindh" },
  { value: "Mirpur Khas",    label: "Mirpur Khas",        group: "Sindh" },
  // KPK
  { value: "Peshawar",       label: "Peshawar",           group: "KPK" },
  { value: "Abbottabad",     label: "Abbottabad",         group: "KPK" },
  { value: "Mardan",         label: "Mardan",             group: "KPK" },
  { value: "Swat",           label: "Swat",               group: "KPK" },
  { value: "Kohat",          label: "Kohat",              group: "KPK" },
  { value: "Mingora",        label: "Mingora",            group: "KPK" },
  // Balochistan
  { value: "Quetta",         label: "Quetta",             group: "Balochistan" },
  { value: "Turbat",         label: "Turbat",             group: "Balochistan" },
  { value: "Khuzdar",        label: "Khuzdar",            group: "Balochistan" },
  // Federal / AJK / GB
  { value: "Islamabad",      label: "Islamabad",          group: "Federal" },
  { value: "Muzaffarabad",   label: "Muzaffarabad",       group: "AJK" },
  { value: "Gilgit",         label: "Gilgit",             group: "GB" },
]

// Group cities for optgroup rendering
const CITY_GROUPS = [
  { label: "Punjab",      values: CITY_OPTIONS.filter(c => c.group === "Punjab") },
  { label: "Sindh",       values: CITY_OPTIONS.filter(c => c.group === "Sindh") },
  { label: "KPK",         values: CITY_OPTIONS.filter(c => c.group === "KPK") },
  { label: "Balochistan", values: CITY_OPTIONS.filter(c => c.group === "Balochistan") },
  { label: "Federal / AJK / GB", values: CITY_OPTIONS.filter(c => ["Federal","AJK","GB"].includes(c.group)) },
]

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
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black text-gray-900">
              {isEditing ? "Edit Address" : "Add New Address"}
            </h2>
            <p className="text-gray-400 text-sm mt-1">
              Province and postal code are auto-filled when you select a city
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
              {isPending ? "SAVING..." : "SAVE ADDRESS"}
            </button>
          </div>
        </div>

        {formError && (
          <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
            {formError}
          </div>
        )}
      </div>

      {/* Fields */}
      <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          {/* Label */}
          <ProfileEditField
            label="Address Type"
            name="label"
            error={fieldErrors.label}
          >
            <select
              name="label"
              value={form.label}
              onChange={handleChange}
              className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 outline-none bg-white focus:border-primary focus:ring-1 focus:ring-primary/20"
            >
              {LABEL_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </ProfileEditField>

          {/* City — grouped dropdown */}
          <ProfileEditField
            label="City"
            name="city"
            error={fieldErrors.city}
          >
            <select
              name="city"
              value={form.city}
              onChange={handleChange}
              className={`
                w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
                outline-none bg-white
                focus:border-primary focus:ring-1 focus:ring-primary/20
                ${fieldErrors.city ? "border-red-400" : "border-gray-200"}
              `}
            >
              <option value="">Select your city</option>
              {CITY_GROUPS.map(({ label, values }) => (
                <optgroup key={label} label={label}>
                  {values.map(({ value, label: cityLabel }) => (
                    <option key={value} value={value}>{cityLabel}</option>
                  ))}
                </optgroup>
              ))}
            </select>
          </ProfileEditField>

          {/* Postal code — read only, auto-filled from city */}
          <ProfileEditField label="Postal Code">
            <div className="flex items-center gap-2 w-full border border-gray-100 rounded-lg px-3 py-2.5 bg-gray-50">
              <MapPin size={14} className="text-gray-300 shrink-0" />
              <span className={`text-sm ${form.city ? "text-gray-700 font-semibold" : "text-gray-300"}`}>
                {postalPreview}
              </span>
              {form.city && (
                <span className="ml-auto text-xs text-gray-400">Auto-filled</span>
              )}
            </div>
          </ProfileEditField>

          {/* Country — always Pakistan */}
          <ProfileEditField label="Country">
            <div className="flex items-center gap-2 w-full border border-gray-100 rounded-lg px-3 py-2.5 bg-gray-50">
              <span className="text-sm text-gray-700 font-semibold">🇵🇰 Pakistan</span>
              <span className="ml-auto text-xs text-gray-400">Fixed</span>
            </div>
          </ProfileEditField>
          {/* Phone */}
          <ProfileEditField
                      label="Phone Number"
                      name="phone"
                      value={form.phone}
                      onChange={handleChange}
                      error={fieldErrors.phone}
                    />

          {/* Address Line 1 — full width */}
          <div className="sm:col-span-2">
            <ProfileEditField
              label="Street Address"
              name="address_line1"
              value={form.address_line1}
              onChange={handleChange}
              error={fieldErrors.address_line1}
            />
          </div>

          {/* Address Line 2 — full width, optional */}
          <div className="sm:col-span-2">
            <ProfileEditField
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

// // src/components/account/profile/AddressForm.jsx

// import { X, Save } from "lucide-react"
// import ProfileEditField from "./ProfileEditField"
// import { useAddressForm } from "../../../hooks/account/useAddressForm"

// const LABEL_OPTIONS = [
//   { value: "home",   label: "Home" },
//   { value: "office", label: "Office" },
//   { value: "other",  label: "Other" },
// ]

// // City list mirrors backend City choices
// const CITY_OPTIONS = [
//   { value: "",                label: "Select city" },
//   // Punjab
//   { value: "Lahore",          label: "Lahore" },
//   { value: "Faisalabad",      label: "Faisalabad" },
//   { value: "Rawalpindi",      label: "Rawalpindi" },
//   { value: "Gujranwala",      label: "Gujranwala" },
//   { value: "Multan",          label: "Multan" },
//   { value: "Sialkot",         label: "Sialkot" },
//   { value: "Bahawalpur",      label: "Bahawalpur" },
//   { value: "Sargodha",        label: "Sargodha" },
//   { value: "Sheikhupura",     label: "Sheikhupura" },
//   { value: "Gujrat",          label: "Gujrat" },
//   { value: "Rahim Yar Khan",  label: "Rahim Yar Khan" },
//   { value: "Jhang",           label: "Jhang" },
//   { value: "Sahiwal",         label: "Sahiwal" },
//   { value: "Okara",           label: "Okara" },
//   { value: "Kasur",           label: "Kasur" },
//   // Sindh
//   { value: "Karachi",         label: "Karachi" },
//   { value: "Hyderabad",       label: "Hyderabad" },
//   { value: "Sukkur",          label: "Sukkur" },
//   { value: "Larkana",         label: "Larkana" },
//   { value: "Nawabshah",       label: "Nawabshah" },
//   { value: "Mirpur Khas",     label: "Mirpur Khas" },
//   // KPK
//   { value: "Peshawar",        label: "Peshawar" },
//   { value: "Abbottabad",      label: "Abbottabad" },
//   { value: "Mardan",          label: "Mardan" },
//   { value: "Swat",            label: "Swat" },
//   { value: "Kohat",           label: "Kohat" },
//   { value: "Mingora",         label: "Mingora" },
//   // Balochistan
//   { value: "Quetta",          label: "Quetta" },
//   { value: "Turbat",          label: "Turbat" },
//   { value: "Khuzdar",         label: "Khuzdar" },
//   // Federal / AJK / GB
//   { value: "Islamabad",       label: "Islamabad" },
//   { value: "Muzaffarabad",    label: "Muzaffarabad" },
//   { value: "Gilgit",          label: "Gilgit" },
// ]

// export default function AddressForm({ existingAddress = null, onCancel }) {
//   const {
//     form,
//     fieldErrors,
//     formError,
//     isPending,
//     handleChange,
//     handleSubmit,
//     CITY_POSTAL_MAP,
//   } = useAddressForm(existingAddress, onCancel)

//   const isEditing = Boolean(existingAddress)

//   return (
//     <form onSubmit={handleSubmit} className="space-y-6">

//       {/* Header */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <div className="flex items-center justify-between">
//           <div>
//             <h2 className="text-xl font-black text-gray-900">
//               {isEditing ? "Edit Address" : "Add New Address"}
//             </h2>
//             <p className="text-gray-400 text-sm mt-1">
//               Province and postal code are auto-filled from your city selection
//             </p>
//           </div>
//           <div className="flex gap-3">
//             <button
//               type="button"
//               onClick={onCancel}
//               className="flex items-center gap-2 border border-gray-200 text-gray-600 px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-gray-50 transition-colors"
//             >
//               <X size={14} />
//               CANCEL
//             </button>
//             <button
//               type="submit"
//               disabled={isPending}
//               className="flex items-center gap-2 bg-primary text-white px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:opacity-90 transition-opacity disabled:opacity-60"
//             >
//               <Save size={14} />
//               {isPending ? "SAVING..." : "SAVE ADDRESS"}
//             </button>
//           </div>
//         </div>

//         {formError && (
//           <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
//             {formError}
//           </div>
//         )}
//       </div>

//       {/* Fields */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

//           {/* Label */}
//           <ProfileEditField label="Address Label" name="label" error={fieldErrors.label}>
//             <select
//               name="label"
//               value={form.label}
//               onChange={handleChange}
//               className="w-full border border-gray-200 rounded-lg px-3 py-2.5 text-sm text-gray-800 outline-none bg-white focus:border-primary focus:ring-1 focus:ring-primary/20"
//             >
//               {LABEL_OPTIONS.map(({ value, label }) => (
//                 <option key={value} value={value}>{label}</option>
//               ))}
//             </select>
//           </ProfileEditField>

//           {/* City — drives province and postal code */}
//           <ProfileEditField label="City" name="city" error={fieldErrors.city}>
//             <select
//               name="city"
//               value={form.city}
//               onChange={handleChange}
//               className={`
//                 w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
//                 outline-none bg-white focus:border-primary focus:ring-1 focus:ring-primary/20
//                 ${fieldErrors.city ? "border-red-400" : "border-gray-200"}
//               `}
//             >
//               {CITY_OPTIONS.map(({ value, label }) => (
//                 <option key={value} value={value}>{label}</option>
//               ))}
//             </select>
//           </ProfileEditField>

//           {/* Postal code — auto preview */}
//           <ProfileEditField label="Postal Code (Auto)" name="postal_code">
//             <input
//               type="text"
//               readOnly
//               value={form.city ? (CITY_POSTAL_MAP[form.city] || "—") : "—"}
//               className="w-full border border-gray-100 rounded-lg px-3 py-2.5 text-sm text-gray-400 bg-gray-50 cursor-not-allowed"
//               placeholder="Auto-filled from city"
//             />
//           </ProfileEditField>

//           {/* Country — always Pakistan */}
//           <ProfileEditField label="Country" name="country">
//             <input
//               type="text"
//               readOnly
//               value="Pakistan"
//               className="w-full border border-gray-100 rounded-lg px-3 py-2.5 text-sm text-gray-400 bg-gray-50 cursor-not-allowed"
//             />
//           </ProfileEditField>

//           {/* Address Line 1 — full width */}
//           <div className="sm:col-span-2">
//             <ProfileEditField
//               label="Address Line 1"
//               name="address_line1"
//               value={form.address_line1}
//               onChange={handleChange}
//               error={fieldErrors.address_line1}
//             />
//           </div>

//           {/* Address Line 2 — full width */}
//           <div className="sm:col-span-2">
//             <ProfileEditField
//               label="Address Line 2 (Optional)"
//               name="address_line2"
//               value={form.address_line2}
//               onChange={handleChange}
//               error={fieldErrors.address_line2}
//             />
//           </div>

//         </div>
//       </div>

//     </form>
//   )
// }