// src/pages/auth/ForgotPassword.jsx

import { Link } from "react-router-dom"
import { Lock, Mail } from "lucide-react"

import { FormInput } from "@shared/ui"

import { AuthIconBadge } from "@widgets/auth"
import { useForgotPasswordForm } from "@features/auth"
import {AuthPageHeader} from "@widgets/auth"
import  {Toast}  from "@shared/ui"

export default function ForgotPassword() {
  const {
    email,
    handleEmailChange,
    handleSubmit,
    isPending,
    emailError,
    formError,
  } = useForgotPasswordForm()

  return (
    <div className="text-center">

      

      
      <AuthPageHeader
  title="Forgot Password?"
/>

      {/* ── OLD ──────────────────────────────────────────────────────
          <div className="mx-auto w-24 h-24 rounded-full bg-gray-100
                          flex items-center justify-center relative">
            <Lock size={45} className="text-gray-700" />
            <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full
                             bg-primary text-white flex items-center
                             justify-center font-bold">
              ?
            </span>
          </div>
          ──────────────────────────────────────────────────────────── */}

      {/* ── NEW ─────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <AuthIconBadge icon={Lock} badge="?" />
      </div>

      <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-200">
        Enter your email address and we will send you a link to reset
        your password.
      </p>

      {/* ── OLD ──────────────────────────────────────────────────────
          Missing dark mode variants on this banner.

          {formError && (
            <div className="mt-4 rounded-lg bg-red-50 border border-red-200
                            px-4 py-3 text-sm text-red-600 text-center">
              {formError}
            </div>
          )}
          ──────────────────────────────────────────────────────────── */}

      {/* ── NEW ─────────────────────────────────────────────────────── */}
      {formError && (
              <Toast type="error" >
                {formError}
              </Toast>
            )}
      

      <form onSubmit={handleSubmit} className="mt-6">
        <FormInput
          icon={Mail}
          type="email"
          name="email"
          placeholder="Enter your email"
          value={email}
          onChange={handleEmailChange}
          error={emailError}
        />

        {/* ── OLD ──────────────────────────────────────────────────
            Missing hover, disabled:cursor-not-allowed, touch-manipulation,
            shadow — inconsistent with Login and Register buttons.

            <button ... className="mt-5 w-full bg-primary text-white
              py-3 rounded-lg font-bold disabled:opacity-60">
            ──────────────────────────────────────────────────────── */}

        {/* ── NEW ─────────────────────────────────────────────────── */}
        <button
          type="submit"
          disabled={isPending}
          className="mt-5 w-full bg-primary text-white py-3 rounded-lg font-bold
                     hover:opacity-90 transition-opacity
                     disabled:opacity-60 disabled:cursor-not-allowed
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          {isPending ? "SENDING..." : "SEND RESET LINK"}
        </button>
      </form>

      <p className="mt-8 text-center text-sm font-semibold">
        <Link to="/login" className="text-primary hover:underline">
          Back to Login
        </Link>
      </p>
    </div>
  )
}
// // src/pages/account/ForgotPassword.jsx

// import { Link } from "react-router-dom";
// import { Lock, Mail } from "lucide-react";

// import { FormInput } from "@shared/ui"
// import { useForgotPasswordForm } from "@features/auth"



// export default function ForgotPassword() {
//   const {
//     email,
//     handleEmailChange,
//     handleSubmit,
//     isPending,
//     emailError,
//     formError,
//   } = useForgotPasswordForm();

//   return (
//     <>
//       <div>
//         <h2 className=" hidden lg:block mt-8 text-2xl text-center font-black dark:text-gray-300">
//           Forgot Password?
//         </h2>

//         <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
//           <Lock size={45} className="text-gray-700" />
//           <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
//             ?
//           </span>
//         </div>

//         <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-200">
//           Enter your email address and we will send you a link to reset
//           your password.
//         </p>

//         {formError && (
//           <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 text-center">
//             {formError}
//           </div>
//         )}

//         <form onSubmit={handleSubmit} className="mt-7">
//           <FormInput
//             icon={Mail}
//             type="email"
//             name="email"
//             placeholder="Enter your email"
//             value={email}
//             onChange={handleEmailChange}
//             error={emailError}
//           />

//           <button
//             type="submit"
//             disabled={isPending}
//             className="mt-5 w-full bg-primary text-white py-3 rounded-lg font-bold disabled:opacity-60"
//           >
//             {isPending ? "SENDING..." : "SEND RESET LINK"}
//           </button>
//         </form>

//         <p className="mt-8 text-center text-sm font-semibold">
//           <Link to="/login" className="text-primary">
//             Back to Login
//           </Link>
//         </p>
//       </div>
//     </>
//   );
// }
