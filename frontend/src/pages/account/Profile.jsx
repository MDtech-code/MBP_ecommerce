// src/pages/account/Profile.jsx
import { useState } from "react"
import DashboardLayout from "../../components/account/DashboardLayout"
import ProfileView from "../../components/account/profile/ProfileView"
import ProfileEditForm from "../../components/account/profile/ProfileEditForm"
import AvatarModal from "../../components/account/profile/AvatarModal"
import { useAuthStore } from "../../stores/authStore"
import { useProfile } from "../../hooks/account/useAuthMutations"
import { hasAuthToken } from "../../api/auth"

export default function Profile() {
  const user = useAuthStore((state) => state.user)
  const [isEditing, setIsEditing] = useState(false)
  const [showAvatarModal, setShowAvatarModal] = useState(false)

  const { isLoading } = useProfile({
    enabled: hasAuthToken() || !user,
  })

  if (isLoading && !user) {
    return (
      <DashboardLayout>
        <div className="flex items-center justify-center h-64">
          <span className="loading loading-spinner loading-md text-primary" />
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>

      {isEditing ? (
        <ProfileEditForm onCancel={() => setIsEditing(false)} />
      ) : (
        <ProfileView
          user={user}
          onEdit={() => setIsEditing(true)}
          onAvatarClick={() => setShowAvatarModal(true)}
        />
      )}

      {showAvatarModal && (
        <AvatarModal
          currentAvatar={user?.profile?.avatar}
          onClose={() => setShowAvatarModal(false)}
        />
      )}

    </DashboardLayout>
  )
}

// // src/pages/account/Profile.jsx
// import { useState, useRef } from "react"
// import {
//   UserRound, Camera, Mail, Phone, MapPin,
//   Calendar, Venus, Edit3, X, Save, Upload
// } from "lucide-react"
// import DashboardLayout from "../../components/account/DashboardLayout"
// import { useAuthStore } from "../../stores/authStore"
// import { useProfile, useUploadAvatar } from "../../hooks/account/useAuthMutations"
// import { useProfileForm } from "../../hooks/account/useProfileForm"
// import { hasAuthToken } from "../../api/auth"
// import { getMediaUrl } from "../../utils/media"
// import { normalizeError } from "../../api/transformers"


// // ─── Gender and Province maps ─────────────────────────────────────────────────

// const GENDER_OPTIONS = [
//   { value: "",  label: "Select gender" },
//   { value: "M", label: "Male" },
//   { value: "F", label: "Female" },
//   { value: "O", label: "Other" },
//   { value: "N", label: "Prefer not to say" },
// ]

// const PROVINCE_OPTIONS = [
//   { value: "",   label: "Select province" },
//   { value: "PB", label: "Punjab" },
//   { value: "SD", label: "Sindh" },
//   { value: "KP", label: "Khyber Pakhtunkhwa" },
//   { value: "BL", label: "Balochistan" },
//   { value: "GB", label: "Gilgit-Baltistan" },
//   { value: "AK", label: "Azad Jammu & Kashmir" },
//   { value: "IC", label: "Islamabad Capital Territory" },
// ]

// // ─── Sub-components ───────────────────────────────────────────────────────────

// function InfoRow({ icon: Icon, label, value }) {
//   return (
//     <div className="flex items-start gap-3 py-3 border-b border-gray-50 last:border-0">
//       <div className="w-8 h-8 rounded-lg bg-primary/8 flex items-center justify-center shrink-0 mt-0.5">
//         <Icon size={15} className="text-primary" />
//       </div>
//       <div className="min-w-0">
//         <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
//           {label}
//         </p>
//         <p className="text-sm font-semibold text-gray-800 mt-0.5 truncate">
//           {value || <span className="text-gray-300 font-normal">Not provided</span>}
//         </p>
//       </div>
//     </div>
//   )
// }

// function EditField({ label, name, type = "text", value, onChange, error, children }) {
//   return (
//     <div className="flex flex-col gap-1">
//       <label className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
//         {label}
//       </label>
//       {children ? children : (
//         <input
//           type={type}
//           name={name}
//           value={value}
//           onChange={onChange}
//           className={`
//             w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
//             outline-none transition-colors
//             focus:border-primary focus:ring-1 focus:ring-primary/20
//             ${error ? "border-red-400 bg-red-50" : "border-gray-200 bg-white"}
//           `}
//         />
//       )}
//       {error && <p className="text-xs text-red-500">{error}</p>}
//     </div>
//   )
// }

// // ─── Avatar Modal ─────────────────────────────────────────────────────────────

// function AvatarModal({ onClose, currentAvatar }) {
//   const fileRef = useRef(null)
//   const [preview, setPreview] = useState(null)
//   const [selectedFile, setSelectedFile] = useState(null)
//   const { mutate: uploadAvatar, isPending, isError, error } = useUploadAvatar()

//   const normalized = isError ? normalizeError(error) : null
//   const uploadError = normalized?.errors?.avatar?.[0]
//     ?? normalized?.errors?.non_field_errors?.[0]
//     ?? normalized?.message
//     ?? null

//   const handleFileSelect = (e) => {
//     const file = e.target.files[0]
//     if (!file) return
//     setSelectedFile(file)
//     setPreview(URL.createObjectURL(file))
//   }

//   const handleUpload = () => {
//     if (!selectedFile) return
//     const formData = new FormData()
//     formData.append("avatar", selectedFile)
//     uploadAvatar(formData, {
//       onSuccess: () => onClose(),
//     })
//   }

//   return (
//     // DaisyUI modal backdrop
//     <div className="modal modal-open">
//       <div className="modal-box max-w-sm rounded-2xl p-0 overflow-hidden">

//         {/* Modal Header */}
//         <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
//           <h3 className="font-black text-gray-900 text-lg">Update Photo</h3>
//           <button
//             onClick={onClose}
//             className="w-8 h-8 rounded-full hover:bg-gray-100 flex items-center justify-center transition-colors"
//           >
//             <X size={18} className="text-gray-500" />
//           </button>
//         </div>

//         {/* Preview Area */}
//         <div className="px-6 py-6 flex flex-col items-center gap-4">

//           <div className="w-32 h-32 rounded-full bg-gray-100 overflow-hidden border-4 border-gray-200 flex items-center justify-center">
//             {preview ? (
//               <img
//                 src={preview}
//                 alt="Preview"
//                 className="w-full h-full object-cover"
//               />
//             ) : currentAvatar ? (
//               <img
//                 src={getMediaUrl(currentAvatar)}
//                 alt="Current"
//                 className="w-full h-full object-cover"
//               />
//             ) : (
//               <UserRound size={60} className="text-gray-300" />
//             )}
//           </div>

//           {/* Error */}
//           {uploadError && (
//             <div role="alert" className="w-full text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2 text-center">
//               {uploadError}
//             </div>
//           )}

//           {/* File input hidden */}
//           <input
//             ref={fileRef}
//             type="file"
//             accept="image/jpeg,image/png,image/webp"
//             className="hidden"
//             onChange={handleFileSelect}
//           />

//           {/* Select file button */}
//           <button
//             onClick={() => fileRef.current?.click()}
//             className="flex items-center gap-2 border border-gray-200 text-gray-700 px-5 py-2.5 rounded-lg text-sm font-semibold hover:border-primary hover:text-primary transition-colors"
//           >
//             <Camera size={16} />
//             {preview ? "Choose Different" : "Choose Photo"}
//           </button>

//           <p className="text-xs text-gray-400 text-center">
//             JPEG, PNG or WebP · Max 2MB
//           </p>

//         </div>

//         {/* Modal Footer */}
//         <div className="flex gap-3 px-6 py-4 border-t border-gray-100 bg-gray-50">
//           <button
//             onClick={onClose}
//             className="flex-1 border border-gray-200 text-gray-600 py-2.5 rounded-lg text-sm font-bold hover:bg-gray-100 transition-colors"
//           >
//             CANCEL
//           </button>
//           <button
//             onClick={handleUpload}
//             disabled={!selectedFile || isPending}
//             className="flex-1 bg-primary text-white py-2.5 rounded-lg text-sm font-bold hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
//           >
//             {isPending ? (
//               <>
//                 <span className="loading loading-spinner loading-xs" />
//                 UPLOADING...
//               </>
//             ) : (
//               <>
//                 <Upload size={15} />
//                 UPLOAD
//               </>
//             )}
//           </button>
//         </div>

//       </div>

//       {/* Backdrop click to close */}
//       <div className="modal-backdrop bg-black/40" onClick={onClose} />
//     </div>
//   )
// }

// // ─── Profile View Mode ────────────────────────────────────────────────────────

// function ProfileView({ user, onEdit, onAvatarClick }) {
//   const fullAddress = user?.profile?.full_address || null

//   return (
//     <div className="space-y-6">

//       {/* Top Card — Avatar + Name + Edit button */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <div className="flex flex-col sm:flex-row items-center sm:items-start gap-6">

//           {/* Avatar */}
//           <div className="relative shrink-0">
//             <div className="w-24 h-24 rounded-2xl bg-gray-100 overflow-hidden border border-gray-200 flex items-center justify-center">
//               {user?.profile?.avatar ? (
//                 <img
//                   src={getMediaUrl(user.profile.avatar)}
//                   alt={user?.full_name}
//                   className="w-full h-full object-cover"
//                 />
//               ) : (
//                 <UserRound size={48} className="text-gray-300" />
//               )}
//             </div>
//             <button
//               onClick={onAvatarClick}
//               className="absolute -bottom-2 -right-2 w-8 h-8 bg-primary text-white rounded-full flex items-center justify-center shadow-md hover:opacity-90 transition-opacity"
//             >
//               <Camera size={13} />
//             </button>
//           </div>

//           {/* Name + Role */}
//           <div className="flex-1 text-center sm:text-left">
//             <h2 className="text-2xl font-black text-gray-900">
//               {user?.full_name || "—"}
//             </h2>
//             <p className="text-gray-400 text-sm mt-1">{user?.email}</p>
//             <div className="flex items-center justify-center sm:justify-start gap-2 mt-3">
//               <span className="bg-primary/10 text-primary text-xs font-bold px-3 py-1 rounded-full">
//                 {user?.role_display || "Customer"}
//               </span>
//               {user?.is_verified && (
//                 <span className="bg-green-50 text-green-600 text-xs font-bold px-3 py-1 rounded-full">
//                   Verified
//                 </span>
//               )}
//             </div>
//           </div>

//           {/* Edit button */}
//           <button
//             onClick={onEdit}
//             className="flex items-center gap-2 border border-primary text-primary px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-primary hover:text-white transition-all shrink-0"
//           >
//             <Edit3 size={14} />
//             EDIT PROFILE
//           </button>

//         </div>
//       </div>

//       {/* Info Cards Row */}
//       <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

//         {/* Personal Info */}
//         <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//           <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-4">
//             Personal Information
//           </h3>
//           <InfoRow icon={Mail}     label="Email"         value={user?.email} />
//           <InfoRow icon={Phone}    label="Phone"         value={user?.profile?.phone} />
//           <InfoRow icon={Calendar} label="Date of Birth" value={user?.profile?.date_of_birth} />
//           <InfoRow icon={Venus}    label="Gender"        value={user?.profile?.gender_display} />
//         </div>

//         {/* Address */}
//         <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//           <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-4">
//             Address
//           </h3>
//           <InfoRow icon={MapPin} label="Address Line 1" value={user?.profile?.address_line1} />
//           <InfoRow icon={MapPin} label="Address Line 2" value={user?.profile?.address_line2} />
//           <InfoRow icon={MapPin} label="City"           value={user?.profile?.city} />
//           <InfoRow icon={MapPin} label="Province"       value={user?.profile?.province_display} />
//           <InfoRow icon={MapPin} label="Postal Code"    value={user?.profile?.postal_code} />
//           <InfoRow icon={MapPin} label="Country"        value={user?.profile?.country} />
//         </div>

//       </div>

//       {/* Full Address Banner */}
//       {fullAddress && (
//         <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 flex items-center gap-3">
//           <div className="w-9 h-9 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
//             <MapPin size={16} className="text-primary" />
//           </div>
//           <div>
//             <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
//               Full Address
//             </p>
//             <p className="text-sm font-semibold text-gray-800 mt-0.5">
//               {fullAddress}
//             </p>
//           </div>
//         </div>
//       )}

//     </div>
//   )
// }

// // ─── Profile Edit Mode ────────────────────────────────────────────────────────

// function ProfileEdit({ onCancel }) {
//   const {
//     form,
//     fieldErrors,
//     formError,
//     isPending,
//     handleChange,
//     handleSubmit,
//   } = useProfileForm(onCancel)

//   return (
//     <form onSubmit={handleSubmit} className="space-y-6">

//       {/* Header */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <div className="flex items-center justify-between">
//           <div>
//             <h2 className="text-xl font-black text-gray-900">Edit Profile</h2>
//             <p className="text-gray-400 text-sm mt-1">
//               Update your personal information
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
//               className="flex items-center gap-2 bg-primary text-white px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:opacity-90 transition-opacity disabled:opacity-60 disabled:cursor-not-allowed"
//             >
//               <Save size={14} />
//               {isPending ? "SAVING..." : "SAVE CHANGES"}
//             </button>
//           </div>
//         </div>

//         {/* Form error banner */}
//         {formError && (
//           <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
//             {formError}
//           </div>
//         )}
//       </div>

//       {/* Personal Info Fields */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-5">
//           Personal Information
//         </h3>

//         <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

//           <EditField
//             label="Phone Number"
//             name="phone"
//             value={form.phone}
//             onChange={handleChange}
//             error={fieldErrors.phone}
//           />

//           <EditField
//             label="Date of Birth"
//             name="date_of_birth"
//             type="date"
//             value={form.date_of_birth}
//             onChange={handleChange}
//             error={fieldErrors.date_of_birth}
//           />

//           <EditField
//             label="Gender"
//             name="gender"
//             error={fieldErrors.gender}
//           >
//             <select
//               name="gender"
//               value={form.gender}
//               onChange={handleChange}
//               className={`
//                 w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
//                 outline-none transition-colors bg-white
//                 focus:border-primary focus:ring-1 focus:ring-primary/20
//                 ${fieldErrors.gender ? "border-red-400" : "border-gray-200"}
//               `}
//             >
//               {GENDER_OPTIONS.map(({ value, label }) => (
//                 <option key={value} value={value}>{label}</option>
//               ))}
//             </select>
//           </EditField>

//         </div>
//       </div>

//       {/* Address Fields */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-5">
//           Address
//         </h3>

//         <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

//           <EditField
//             label="Address Line 1"
//             name="address_line1"
//             value={form.address_line1}
//             onChange={handleChange}
//             error={fieldErrors.address_line1}
//           />

//           <EditField
//             label="Address Line 2"
//             name="address_line2"
//             value={form.address_line2}
//             onChange={handleChange}
//             error={fieldErrors.address_line2}
//           />

//           <EditField
//             label="City"
//             name="city"
//             value={form.city}
//             onChange={handleChange}
//             error={fieldErrors.city}
//           />

//           <EditField
//             label="Province"
//             name="province"
//             error={fieldErrors.province}
//           >
//             <select
//               name="province"
//               value={form.province}
//               onChange={handleChange}
//               className={`
//                 w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800
//                 outline-none transition-colors bg-white
//                 focus:border-primary focus:ring-1 focus:ring-primary/20
//                 ${fieldErrors.province ? "border-red-400" : "border-gray-200"}
//               `}
//             >
//               {PROVINCE_OPTIONS.map(({ value, label }) => (
//                 <option key={value} value={value}>{label}</option>
//               ))}
//             </select>
//           </EditField>

//           <EditField
//             label="Postal Code"
//             name="postal_code"
//             value={form.postal_code}
//             onChange={handleChange}
//             error={fieldErrors.postal_code}
//           />

//           <EditField
//             label="Country"
//             name="country"
//             value={form.country}
//             onChange={handleChange}
//             error={fieldErrors.country}
//           />

//         </div>
//       </div>

//     </form>
//   )
// }

















// // ─── Main Profile Page ────────────────────────────────────────────────────────

// export default function Profile() {
//   const user = useAuthStore((state) => state.user)
//   const [isEditing, setIsEditing] = useState(false)
//   const [showAvatarModal, setShowAvatarModal] = useState(false)

//   const { isLoading } = useProfile({
//     enabled: hasAuthToken() || !user,
//   })

//   if (isLoading && !user) {
//     return (
//       <DashboardLayout>
//         <div className="flex items-center justify-center h-64">
//           <span className="loading loading-spinner loading-md text-primary" />
//         </div>
//       </DashboardLayout>
//     )
//   }

//   return (
//     <DashboardLayout>

//       {/* Main content — switches between view and edit */}
//       {isEditing ? (
//         <ProfileEdit onCancel={() => setIsEditing(false)} />
//       ) : (
//         <ProfileView
//           user={user}
//           onEdit={() => setIsEditing(true)}
//           onAvatarClick={() => setShowAvatarModal(true)}
//         />
//       )}

//       {/* Avatar upload modal */}
//       {showAvatarModal && (
//         <AvatarModal
//           currentAvatar={user?.profile?.avatar}
//           onClose={() => setShowAvatarModal(false)}
//         />
//       )}

//     </DashboardLayout>
//   )
// }
// src/pages/account/Profile.jsx
// import { getMediaUrl } from "../../utils/media"
// import { UserRound, Camera } from "lucide-react"
// import DashboardLayout from "../../components/account/DashboardLayout"
// import { useAuthStore } from "../../stores/authStore"
// import { useProfile } from "../../hooks/account/useAuthMutations"
// import { hasAuthToken } from "../../api/auth"

// function ProfileInput({ label, value }) {
//   return (
//     <div>
//       <label className="block text-sm font-semibold text-gray-600 mb-1.5">
//         {label}
//       </label>
//       <input
//         value={value || ""}
//         readOnly
//         className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm outline-none bg-white text-gray-700"
//       />
//     </div>
//   )
// }

// export default function Profile() {
//   const user = useAuthStore((state) => state.user)

//   // Fetch profile from backend — runs on page refresh to restore state
//   // enabled: false when no token (interceptor will handle refresh first)
//   const { isLoading } = useProfile({
//     enabled: hasAuthToken() || !user,
//   })

//   // Show loading while fetching after page refresh
//   if (isLoading && !user) {
//     return (
//       <DashboardLayout>
//         <div className="flex items-center justify-center h-64">
//           <p className="text-gray-400 text-sm">Loading profile...</p>
//         </div>
//       </DashboardLayout>
//     )
//   }

//   // Build display values from real backend data
//   const fullAddress = [
//     user?.profile?.address_line1,
//     user?.profile?.city,
//     user?.profile?.province_display,
//     user?.profile?.country,
//   ]
//     .filter(Boolean)
//     .join(", ")

//   return (
//     <DashboardLayout>
//       <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 lg:p-8">

//         {/* Header Row */}
//         <div className="flex items-start justify-between mb-8">
//           <div>
//             <h1 className="text-2xl font-black text-gray-900">
//               Profile Information
//             </h1>
//             <p className="text-gray-400 text-sm mt-1">
//               Manage your personal information
//             </p>
//           </div>
//           <button className="border border-primary text-primary px-5 py-2 rounded-md font-bold text-xs tracking-wide hover:bg-red-50 transition">
//             EDIT PROFILE
//           </button>
//         </div>

//         {/* Body */}
//         <div className="flex flex-col lg:flex-row gap-8">

//           {/* Left — Avatar */}
//           <div className="flex flex-col items-center lg:w-56 shrink-0">

//             <div className="w-32 h-32 rounded-full bg-gray-100 flex items-center justify-center overflow-hidden">
//               {user?.profile?.avatar ? (
//                 <img
//                   src={getMediaUrl(user.profile.avatar)}
//                   alt={user?.full_name}
//                   className="w-full h-full object-cover"
//                 />
//               ) : (
//                 <UserRound size={70} className="text-gray-300" />
//               )}
//             </div>

//             <h2 className="mt-4 font-black text-lg text-gray-900">
//               {user?.full_name || "—"}
//             </h2>

//             <p className="text-gray-400 text-sm mt-1">
//               {user?.email || "—"}
//             </p>

//             <p className="text-gray-600 text-sm font-medium mt-2">
//               {user?.profile?.phone || "No phone added"}
//             </p>

//             <p className="text-gray-400 text-sm mt-1">
//               {user?.profile?.city
//                 ? `${user.profile.city}, ${user.profile.country}`
//                 : user?.profile?.country || "—"}
//             </p>

//             <button className="mt-5 border border-primary text-primary px-5 py-2 rounded-md font-bold text-xs tracking-wide flex items-center gap-2 hover:bg-red-50 transition">
//               <Camera size={15} />
//               CHANGE PHOTO
//             </button>

//           </div>

//           {/* Divider */}
//           <div className="hidden lg:block w-px bg-gray-100 self-stretch" />

//           {/* Right — Form Fields */}
//           <div className="flex-1 space-y-5">

//             <ProfileInput
//               label="Full Name"
//               value={user?.full_name}
//             />

//             <ProfileInput
//               label="Email Address"
//               value={user?.email}
//             />

//             <ProfileInput
//               label="Phone Number"
//               value={user?.profile?.phone}
//             />

//             <ProfileInput
//               label="Address"
//               value={fullAddress || "No address added"}
//             />

//             <div className="flex justify-end pt-4">
//               <button className="bg-primary text-white px-10 py-3 rounded-md font-bold text-sm tracking-wide hover:bg-red-700 transition">
//                 SAVE CHANGES
//               </button>
//             </div>

//           </div>

//         </div>

//       </div>
//     </DashboardLayout>
//   )
// }
// import { UserRound, Camera } from "lucide-react";
// import DashboardLayout from "../../components/account/DashboardLayout";

// const profile = {
//   full_name: "John Rider",
//   email: "rider@example.com",
//   phone: "0312 3456789",
//   address: "Lahore, Punjab, Pakistan",
// };

// export default function Profile() {
//   return (
//     <DashboardLayout>

//       <div className="bg-white rounded-xl border border-gray-100 shadow-sm p-6 lg:p-8">

//         {/* Header Row */}
//         <div className="flex items-start justify-between mb-8">
//           <div>
//             <h1 className="text-2xl font-black text-gray-900">
//               Profile Information
//             </h1>
//             <p className="text-gray-400 text-sm mt-1">
//               Manage your personal information
//             </p>
//           </div>

//           <button className="border border-primary text-primary px-5 py-2 rounded-md font-bold text-xs tracking-wide hover:bg-red-50 transition">
//             EDIT PROFILE
//           </button>
//         </div>

//         {/* Body */}
//         <div className="flex flex-col lg:flex-row gap-8">

//           {/* Left - Avatar */}
//           <div className="flex flex-col items-center lg:w-56 shrink-0">

//             <div className="w-32 h-32 rounded-full bg-gray-100 flex items-center justify-center overflow-hidden">
//               <UserRound size={70} className="text-gray-300" />
//             </div>

//             <h2 className="mt-4 font-black text-lg text-gray-900">
//               {profile.full_name}
//             </h2>

//             <p className="text-gray-400 text-sm mt-1">
//               {profile.email}
//             </p>

//             <p className="text-gray-600 text-sm font-medium mt-2">
//               {profile.phone}
//             </p>

//             <p className="text-gray-400 text-sm mt-1">
//               Lahore, Pakistan
//             </p>

//             <button className="mt-5 border border-primary text-primary px-5 py-2 rounded-md font-bold text-xs tracking-wide flex items-center gap-2 hover:bg-red-50 transition">
//               <Camera size={15} />
//               CHANGE PHOTO
//             </button>

//           </div>

//           {/* Subtle Divider */}
//           <div className="hidden lg:block w-px bg-gray-100 self-stretch" />

//           {/* Right - Form */}
//           <div className="flex-1 space-y-5">

//             <ProfileInput label="Full Name" value={profile.full_name} />
//             <ProfileInput label="Email Address" value={profile.email} />
//             <ProfileInput label="Phone Number" value={profile.phone} />
//             <ProfileInput label="Address" value={profile.address} />

//             <div className="flex justify-end pt-4">
//               <button className="bg-primary text-white px-10 py-3 rounded-md font-bold text-sm tracking-wide hover:bg-red-700 transition">
//                 SAVE CHANGES
//               </button>
//             </div>

//           </div>

//         </div>

//       </div>

//     </DashboardLayout>
//   );
// }

// function ProfileInput({ label, value }) {
//   return (
//     <div>
//       <label className="block text-sm font-semibold text-gray-600 mb-1.5">
//         {label}
//       </label>
//       <input
//         value={value}
//         readOnly
//         className="w-full border border-gray-200 rounded-lg px-4 py-2.5 text-sm outline-none bg-white text-gray-700"
//       />
//     </div>
//   );
// }