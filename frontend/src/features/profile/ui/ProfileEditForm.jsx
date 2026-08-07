// src/features/profile/ui/ProfileEditForm.jsx
//
// Changes:
//   - Dark mode added to all cards, inputs, text
//   - AlertBanner adopted for formError (Phase 6 combined here)
//   - OTP panel dark mode added
//   - Select dark mode added

import { X, Save, CheckCircle2, ShieldCheck, AlertCircle } from "lucide-react"
import { FormField } from "@shared/ui"
import { AlertBanner } from "@shared/ui"
import { useProfileForm } from "@features/profile"
import { usePhoneVerification } from "@features/profile"
import { ErrorCode } from "@shared/api"

const GENDER_OPTIONS = [
  { value: "",  label: "Select gender"      },
  { value: "M", label: "Male"               },
  { value: "F", label: "Female"             },
  { value: "O", label: "Other"              },
  { value: "N", label: "Prefer not to say"  },
]

export default function ProfileEditForm({ onCancel }) {
  const {
    form, fieldErrors, formError, isPending,
    isPhoneVerified, handleChange, handleSubmit, handlePhoneVerified,
  } = useProfileForm(onCancel)

  const {
    otpVisible, otp, setOtp, pendingPhone,
    isSending, isVerifying,
    sendFieldError, sendError, verifyError, verifyCode,
    handleSendOtp, handleVerifyOtp, handleCancelOtp,
  } = usePhoneVerification({ onVerified: handlePhoneVerified })

  return (
    <form onSubmit={handleSubmit} className="space-y-6">

      {/* Header */}
      <div className="bg-white dark:bg-[#0a0a0a] rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-black text-gray-900 dark:text-gray-100">
              Edit Profile
            </h2>
            <p className="text-gray-400 dark:text-gray-500 text-sm mt-1">
              Update your personal information
            </p>
          </div>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={onCancel}
              className="flex items-center gap-2 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-400 px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
            >
              <X size={14} /> CANCEL
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

        {/* ── OLD ────────────────────────────────────────────────────
        {formError && (
          <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50
            border border-red-200 rounded-lg px-4 py-2">
            {formError}
          </div>
        )}
        ─────────────────────────────────────────────────────────────── */}

        {/* ── NEW — AlertBanner adopted ─────────────────────────────── */}
        {formError && (
          <AlertBanner type="error" className="mt-4">
            {formError}
          </AlertBanner>
        )}
      </div>

      {/* Personal Info */}
      <div className="bg-white dark:bg-[#0a0a0a] rounded-2xl border border-gray-100 dark:border-gray-800 shadow-sm p-6">
        <h3 className="font-black text-gray-900 dark:text-gray-100 text-sm uppercase tracking-wide mb-5">
          Personal Information
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

          {/* Phone field */}
          <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-1">
            <div className="flex items-end gap-2">
              <div className="flex-1">
                <FormField
                  label="Phone Number"
                  name="phone"
                  value={form.phone}
                  onChange={handleChange}
                  error={fieldErrors.phone || sendFieldError}
                />
              </div>

              {isPhoneVerified ? (
                <div className="pb-2.5 flex items-center gap-1 text-green-600 dark:text-green-400 text-xs font-bold whitespace-nowrap">
                  <CheckCircle2 size={15} />
                  Verified
                </div>
              ) : (
                form.phone && !otpVisible && (
                  <button
                    type="button"
                    disabled={isSending}
                    onClick={() => handleSendOtp(form.phone)}
                    className="pb-0.5 flex items-center gap-1.5 border border-primary text-primary px-3 py-2.5 rounded-xl text-xs font-bold hover:bg-primary hover:text-white transition-all disabled:opacity-50 whitespace-nowrap"
                  >
                    <ShieldCheck size={13} />
                    {isSending ? "Sending..." : "Verify"}
                  </button>
                )
              )}
            </div>

            {sendError && (
              <p className="text-xs text-red-500 dark:text-red-400 flex items-center gap-1">
                <AlertCircle size={12} /> {sendError}
              </p>
            )}

            {/* OTP Panel */}
            {otpVisible && (
              <div className="mt-2 p-4 bg-primary/5 dark:bg-primary/10 border border-primary/20 rounded-xl space-y-3">
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  Enter the 6-digit code sent to{" "}
                  <span className="font-bold text-gray-700 dark:text-gray-200">
                    {pendingPhone}
                  </span>
                </p>

                <div className="flex gap-2">
                  <input
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    placeholder="000000"
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
                    className="flex-1 border border-gray-200 dark:border-gray-700 rounded-lg px-3 py-2 text-sm tracking-widest outline-none bg-transparent dark:bg-transparent text-gray-900 dark:text-white focus:border-primary focus:ring-1 focus:ring-primary/20"
                  />
                  <button
                    type="button"
                    disabled={otp.length < 6 || isVerifying}
                    onClick={handleVerifyOtp}
                    className="bg-primary text-white px-4 py-2 rounded-lg text-xs font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
                  >
                    {isVerifying ? "Verifying..." : "Confirm"}
                  </button>
                  <button
                    type="button"
                    onClick={handleCancelOtp}
                    className="border border-gray-200 dark:border-gray-700 text-gray-500 dark:text-gray-400 px-3 py-2 rounded-lg text-xs font-bold hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                  >
                    Cancel
                  </button>
                </div>

                {verifyError && (
                  <div className="flex items-start gap-1.5">
                    <AlertCircle size={12} className="text-red-500 mt-0.5 shrink-0" />
                    <div>
                      <p className="text-xs text-red-500 dark:text-red-400">
                        {verifyError}
                      </p>
                      {verifyCode === ErrorCode.OTP_EXPIRED && (
                        <button
                          type="button"
                          onClick={() => handleSendOtp(form.phone)}
                          className="text-xs font-bold text-primary hover:underline mt-0.5"
                        >
                          Resend code
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

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
              className={`w-full border rounded-lg px-3 py-2.5 text-sm outline-none transition-colors
                bg-transparent dark:bg-transparent
                text-gray-800 dark:text-white
                focus:border-primary focus:ring-1 focus:ring-primary/20
                ${fieldErrors.gender
                  ? "border-red-400 dark:border-red-500"
                  : "border-gray-200 dark:border-gray-700"
                }`}
            >
              {GENDER_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}
                  className="bg-white dark:bg-gray-900">
                  {label}
                </option>
              ))}
            </select>
          </FormField>

        </div>
      </div>

      <div className="bg-gray-50 dark:bg-gray-800/40 rounded-2xl border border-dashed border-gray-200 dark:border-gray-700 p-5 text-center">
        <p className="text-sm text-gray-400 dark:text-gray-500">
          Manage your shipping addresses from the{" "}
          <span className="font-semibold text-primary">My Addresses</span>{" "}
          section in the sidebar.
        </p>
      </div>

    </form>
  )
}

// // src/components/profile/ProfileEditForm.jsx

// import { X, Save, CheckCircle2, ShieldCheck, AlertCircle } from "lucide-react";
// import { FormField } from "@shared/ui/FormField";
// import { useProfileForm }       from "@features/profile";
// import { usePhoneVerification } from "@features/profile";
// import { ErrorCode } from "@shared/api";

// const GENDER_OPTIONS = [
//   { value: "",  label: "Select gender" },
//   { value: "M", label: "Male" },
//   { value: "F", label: "Female" },
//   { value: "O", label: "Other" },
//   { value: "N", label: "Prefer not to say" },
// ];

// export default function ProfileEditForm({ onCancel }) {
//   const {
//     form,
//     fieldErrors,
//     formError,
//     isPending,
//     isPhoneVerified,
//     handleChange,
//     handleSubmit,
//     handlePhoneVerified,
//   } = useProfileForm(onCancel);

//   const {
//     otpVisible,
//     otp,
//     setOtp,
//     pendingPhone,
//     isSending,
//     isVerifying,
//     sendFieldError,
//     sendError,
//     verifyError,
//     verifyCode,
//     handleSendOtp,
//     handleVerifyOtp,
//     handleCancelOtp,
//   } = usePhoneVerification({ onVerified: handlePhoneVerified });

//   return (
//     <form onSubmit={handleSubmit} className="space-y-6">

//       {/* Header */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <div className="flex items-center justify-between">
//           <div>
//             <h2 className="text-xl font-black text-gray-900">Edit Profile</h2>
//             <p className="text-gray-400 text-sm mt-1">Update your personal information</p>
//           </div>
//           <div className="flex gap-3">
//             <button
//               type="button"
//               onClick={onCancel}
//               className="flex items-center gap-2 border border-gray-200 text-gray-600 px-5 py-2.5 rounded-xl font-bold text-xs tracking-wide hover:bg-gray-50 transition-colors"
//             >
//               <X size={14} /> CANCEL
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

//         {formError && (
//           <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
//             {formError}
//           </div>
//         )}
//       </div>

//       {/* Personal Info */}
//       <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
//         <h3 className="font-black text-gray-900 text-sm uppercase tracking-wide mb-5">
//           Personal Information
//         </h3>

//         <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">

//           {/* ── Phone field ────────────────────────────────────── */}
//           <div className="flex flex-col gap-1 sm:col-span-2 lg:col-span-1">

//             <div className="flex items-end gap-2">
//               <div className="flex-1">
//                 <FormField
//                   label="Phone Number"
//                   name="phone"
//                   value={form.phone}
//                   onChange={handleChange}
//                   error={fieldErrors.phone || sendFieldError}
//                 />
//               </div>

//               {/* Verified badge */}
//               {isPhoneVerified ? (
//                 <div className="pb-2.5 flex items-center gap-1 text-green-600 text-xs font-bold whitespace-nowrap">
//                   <CheckCircle2 size={15} />
//                   Verified
//                 </div>
//               ) : (
//                 /* Verify button — only show when phone has a value and OTP panel not open */
//                 form.phone && !otpVisible && (
//                   <button
//                     type="button"
//                     disabled={isSending}
//                     onClick={() => handleSendOtp(form.phone)}
//                     className="pb-0.5 flex items-center gap-1.5 border border-primary text-primary px-3 py-2.5 rounded-xl text-xs font-bold hover:bg-primary hover:text-white transition-all disabled:opacity-50 whitespace-nowrap"
//                   >
//                     <ShieldCheck size={13} />
//                     {isSending ? "Sending..." : "Verify"}
//                   </button>
//                 )
//               )}
//             </div>

//             {/* Send-level non-field error (e.g. OTP service down) */}
//             {sendError && (
//               <p className="text-xs text-red-500 flex items-center gap-1">
//                 <AlertCircle size={12} /> {sendError}
//               </p>
//             )}

//             {/* OTP panel — slides in after successful send */}
//             {otpVisible && (
//               <div className="mt-2 p-4 bg-primary/5 border border-primary/20 rounded-xl space-y-3">
//                 <p className="text-xs text-gray-500">
//                   Enter the 6-digit code sent to{" "}
//                   <span className="font-bold text-gray-700">{pendingPhone}</span>
//                 </p>

//                 <div className="flex gap-2">
//                   <input
//                     type="text"
//                     inputMode="numeric"
//                     maxLength={6}
//                     placeholder="000000"
//                     value={otp}
//                     onChange={(e) => setOtp(e.target.value.replace(/\D/g, ""))}
//                     className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm tracking-widest outline-none focus:border-primary focus:ring-1 focus:ring-primary/20"
//                   />
//                   <button
//                     type="button"
//                     disabled={otp.length < 6 || isVerifying}
//                     onClick={handleVerifyOtp}
//                     className="bg-primary text-white px-4 py-2 rounded-lg text-xs font-bold hover:opacity-90 transition-opacity disabled:opacity-50"
//                   >
//                     {isVerifying ? "Verifying..." : "Confirm"}
//                   </button>
//                   <button
//                     type="button"
//                     onClick={handleCancelOtp}
//                     className="border border-gray-200 text-gray-500 px-3 py-2 rounded-lg text-xs font-bold hover:bg-gray-50 transition-colors"
//                   >
//                     Cancel
//                   </button>
//                 </div>

//                 {/* OTP error — distinguish expired vs wrong code for UX */}
//                 {verifyError && (
//                   <div className="flex items-start gap-1.5">
//                     <AlertCircle size={12} className="text-red-500 mt-0.5 shrink-0" />
//                     <div>
//                       <p className="text-xs text-red-500">{verifyError}</p>
//                       {verifyCode === ErrorCode.OTP_EXPIRED && (
//                         <button
//                           type="button"
//                           onClick={() => handleSendOtp(form.phone)}
//                           className="text-xs font-bold text-primary hover:underline mt-0.5"
//                         >
//                           Resend code
//                         </button>
//                       )}
//                     </div>
//                   </div>
//                 )}
//               </div>
//             )}
//           </div>
//           {/* ── End phone field ─────────────────────────────────── */}

//           <FormField
//             label="Date of Birth"
//             name="date_of_birth"
//             type="date"
//             value={form.date_of_birth}
//             onChange={handleChange}
//             error={fieldErrors.date_of_birth}
//           />

//           <FormField
//             label="Gender"
//             name="gender"
//             error={fieldErrors.gender}
//           >
//             <select
//               name="gender"
//               value={form.gender}
//               onChange={handleChange}
//               className={`w-full border rounded-lg px-3 py-2.5 text-sm text-gray-800 outline-none transition-colors bg-white focus:border-primary focus:ring-1 focus:ring-primary/20 ${fieldErrors.gender ? "border-red-400" : "border-gray-200"}`}
//             >
//               {GENDER_OPTIONS.map(({ value, label }) => (
//                 <option key={value} value={value}>{label}</option>
//               ))}
//             </select>
//           </FormField>

//         </div>
//       </div>

//       <div className="bg-gray-50 rounded-2xl border border-dashed border-gray-200 p-5 text-center">
//         <p className="text-sm text-gray-400">
//           Manage your shipping addresses separately from the
//           <span className="font-semibold text-primary"> Addresses </span>
//           section on your profile.
//         </p>
//       </div>

//     </form>
//   );
// }
