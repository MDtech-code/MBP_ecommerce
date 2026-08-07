// src/pages/auth/ResetPassword.jsx

import { Link } from "react-router-dom"
import { Lock } from "lucide-react"

import { FormInput } from "@shared/ui"

import { AuthIconBadge } from "@widgets/auth"
import { useResetPasswordForm } from "@features/auth"
import {AuthPageHeader} from "@widgets/auth"
import  {Toast}  from "@shared/ui"

export default function ResetPasswordPage() {
  const {
    fields,
    handleChange,
    handleSubmit,
    isPending,
    passwordError,
    confirmPasswordError,
    formError,
    tokenMissing,
  } = useResetPasswordForm()

  if (tokenMissing) {
    return (
      <div className="text-center">

        
        <AuthPageHeader
  title="Reset Password"
/>

        {/* ── OLD ────────────────────────────────────────────────────
            <div className="mx-auto w-24 h-24 rounded-full bg-gray-100
                            flex items-center justify-center relative">
              <Lock size={45} className="text-gray-700" />
              <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full
                               bg-primary text-white flex items-center
                               justify-center font-bold">
                ✕
              </span>
            </div>
            ────────────────────────────────────────────────────────── */}

        {/* ── NEW ──────────────────────────────────────────────────── */}
        <div className="mt-6">
          <AuthIconBadge icon={Lock} badge="✕" />
        </div>

        {/* ── OLD ────────────────────────────────────────────────────
            Missing dark mode variants.

            <div className="mt-6 rounded-lg bg-red-50 border border-red-200
                            px-4 py-3 text-sm text-red-600 text-center">
              This reset link is invalid or has expired...
            </div>
            ────────────────────────────────────────────────────────── */}

        {/* ── NEW ──────────────────────────────────────────────────── */}
       {formError && (
               <Toast type="error" >
                 {formError}
               </Toast>
             )}
       

        <div className="mt-6">
          <Link
            to="/forgot-password"
            className="block w-full bg-primary text-white py-3 rounded-lg
                       font-bold text-center hover:opacity-90 transition-opacity
                       shadow-lg shadow-primary/25 touch-manipulation"
          >
            REQUEST NEW LINK
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div>

      {/* ── OLD ────────────────────────────────────────────────────────
          h2 was fully commented out in the valid token flow.
          Kept hidden on mobile/tablet — AuthBrand provides context.
          Added back consistently with other pages.
      ─────────────────────────────────────────────────────────────── */}
      <div className="hidden lg:block">
        <h2 className="text-3xl font-black text-gray-900 dark:text-gray-100">
          Reset Password
        </h2>
      </div>

      {/* ── OLD ────────────────────────────────────────────────────────
          <div className="mx-auto w-24 h-24 rounded-full bg-gray-100
                          flex items-center justify-center relative">
            <Lock size={45} className="text-gray-700" />
            <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full
                             bg-primary text-white flex items-center
                             justify-center font-bold">
              ↻
            </span>
          </div>
          ────────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <AuthIconBadge icon={Lock} badge="↻" />
      </div>

      <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-300">
        Create a new password for your account.
      </p>

      {/* ── OLD ──────────────────────────────────────────────────────────
          Missing dark mode variants.

          {formError && (
            <div className="mt-4 rounded-lg bg-red-50 border border-red-200
                            px-4 py-3 text-sm text-red-600 text-center">
              {formError}
            </div>
          )}
          ────────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────── */}
      {formError && (
               <Toast type="error" >
                 {formError}
               </Toast>
             )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <FormInput
          icon={Lock}
          type="password"
          name="password"
          placeholder="Enter new password"
          value={fields.password}
          onChange={handleChange}
          error={passwordError}
        />

        <FormInput
          icon={Lock}
          type="password"
          name="confirm_password"
          placeholder="Confirm new password"
          value={fields.confirm_password}
          onChange={handleChange}
          error={confirmPasswordError}
        />

        {/* ── OLD ──────────────────────────────────────────────────────
            Missing hover, disabled:cursor-not-allowed,
            touch-manipulation, shadow.

            <button ... className="w-full bg-primary text-white py-3
              rounded-lg font-bold disabled:opacity-60">
            ────────────────────────────────────────────────────────── */}

        {/* ── NEW ──────────────────────────────────────────────────── */}
        <button
          type="submit"
          disabled={isPending}
          className="w-full bg-primary text-white py-3 rounded-lg font-bold
                     hover:opacity-90 transition-opacity
                     disabled:opacity-60 disabled:cursor-not-allowed
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          {isPending ? "RESETTING..." : "RESET PASSWORD"}
        </button>
      </form>
    </div>
  )
}
// // src/pages/account/ResetPassword.jsx

// import { Link } from "react-router-dom";
// import { Lock } from "lucide-react";

// import { FormInput } from "@shared/ui"
// import { useResetPasswordForm } from "@features/auth";



// export default function ResetPassword() {
//   const {
//     fields,
//     handleChange,
//     handleSubmit,
//     isPending,
//     passwordError,
//     confirmPasswordError,
//     formError,
//     tokenMissing,
//   } = useResetPasswordForm();

//   // Token was not in the URL — link is invalid or already used
//   if (tokenMissing) {
//     return (
//       <>
//         <div>
//           <h2 className="hidden lg:block mt-8 text-center text-2xl font-black dark:text-gray-300">
//             Reset Password
//           </h2>

//           <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
//             <Lock size={45} className="text-gray-700" />
//             <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
//               ✕
//             </span>
//           </div>

//           <div className="mt-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 text-center">
//             This reset link is invalid or has expired. Please request a
//             new one.
//           </div>

//           <div className="mt-6">
//             <Link
//               to="/forgot-password"
//               className="block w-full bg-primary text-white py-3 rounded-lg font-bold text-center"
//             >
//               REQUEST NEW LINK
//             </Link>
//           </div>
//         </div>
//       </>
//     );
//   }

//   return (
//     <>
//       <div>
//         {/* <h2 className="mt-8 text-center text-2xl font-black">
//           Reset Password
//         </h2> */}

//         <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
//           <Lock size={45} className="text-gray-700" />
//           <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
//             ↻
//           </span>
//         </div>

//         <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-300">
//           Create a new password for your account.
//         </p>

//         {formError && (
//           <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 text-center">
//             {formError}
//           </div>
//         )}

//         <form onSubmit={handleSubmit} className="mt-7 space-y-4">
//           <FormInput
//             icon={Lock}
//             type="password"
//             name="password"
//             placeholder="Enter new password"
//             value={fields.password}
//             onChange={handleChange}
//             error={passwordError}
//           />

//           <FormInput
//             icon={Lock}
//             type="password"
//             name="confirm_password"
//             placeholder="Confirm new password"
//             value={fields.confirm_password}
//             onChange={handleChange}
//             error={confirmPasswordError}
//           />

//           <button
//             type="submit"
//             disabled={isPending}
//             className="w-full bg-primary text-white py-3 rounded-lg font-bold disabled:opacity-60"
//           >
//             {isPending ? "RESETTING..." : "RESET PASSWORD"}
//           </button>
//         </form>
//       </div>
//     </>
//   );
// }
