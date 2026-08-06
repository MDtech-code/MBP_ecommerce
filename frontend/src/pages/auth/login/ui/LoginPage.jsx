// src/pages/login/Login.jsx

import { Mail, Lock } from "lucide-react"
import { Link } from "react-router-dom"

import { FormInput } from "@shared/ui"
import { AlertBanner } from "@shared/ui"
import { SocialLogin } from "@features/auth"
import { useLoginForm } from "@features/auth"
import { ErrorCode } from "@shared/api"

export default function Login() {
  const {
    form,
    fieldErrors,
    formError,
    formErrorCode,
    isPending,
    isResending,
    isResendSuccess,
    handleResend,
    handleChange,
    handleSubmit,
  } = useLoginForm()

  return (
    <div>
      {/* Desktop heading — hidden on mobile/tablet, AuthBrand handles those */}
      <div className="hidden lg:block">
        {/* ── OLD ──────────────────────────────────────────────────
        <h2 className="text-3xl font-black text-gray-900 dark:text-gray-200">
          Hello Again!
        </h2>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Login to manage your account
        </p>
        ─────────────────────────────────────────────────────────── */}

        {/* ── NEW ──────────────────────────────────────────────────
            dark:text-gray-100 unified across all auth page headings.
            was dark:text-gray-200 here vs dark:text-gray-100 on
            Register — one step difference, now consistent.
        ─────────────────────────────────────────────────────────── */}
        <h2 className="text-3xl font-black text-gray-900 dark:text-gray-100">
          Hello Again!
        </h2>
        <p className="mt-2 text-gray-500 dark:text-gray-400">
          Login to manage your account
        </p>
      </div>

      {/* ── Form level feedback ────────────────────────────────────
          ── OLD ────────────────────────────────────────────────────
          Two separate hand-rolled banner divs with full inline
          className strings. Success banner used py-2, error used py-3.
          Dark mode variants were present here but missing on other pages.

          {isResendSuccess && formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED ? (
            <div role="status" className="mt-4 text-sm text-green-700
              dark:text-green-400 bg-green-50 dark:bg-green-900/20
              border border-green-200 dark:border-green-800
              rounded-lg px-4 py-3">
              Verification email sent. Please check your inbox.
            </div>
          ) : formError ? (
            <div role="alert" className="mt-4 text-sm text-red-600
              dark:text-red-400 bg-red-50 dark:bg-red-900/20
              border border-red-200 dark:border-red-800
              rounded-lg px-4 py-3">
              <p>{formError}</p>
              {formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED && (
                <button
                  type="button"
                  onClick={handleResend}
                  disabled={isResending}
                  className="mt-2 min-h-11 py-1 text-xs font-bold underline
                    text-red-700 dark:text-red-400 hover:text-red-900
                    dark:hover:text-red-300 disabled:opacity-50
                    disabled:cursor-not-allowed touch-manipulation"
                >
                  {isResending
                    ? "Sending verification email..."
                    : "Resend verification email"}
                </button>
              )}
            </div>
          ) : null}
          ──────────────────────────────────────────────────────────

          ── NEW ────────────────────────────────────────────────────
          AlertBanner handles role, colors, dark mode, padding.
          Resend button lives inside the error banner as a child —
          same behavior, cleaner markup.
          className="mt-4" passed externally — AlertBanner is not
          opinionated about its own margin.
      ─────────────────────────────────────────────────────────── */}
      {isResendSuccess && formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED ? (
        <AlertBanner type="success" className="mt-4">
          Verification email sent. Please check your inbox.
        </AlertBanner>
      ) : formError ? (
        <AlertBanner type="error" className="mt-4">
          <p>{formError}</p>
          {formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED && (
            <button
              type="button"
              onClick={handleResend}
              disabled={isResending}
              className="mt-2 min-h-11 py-1 text-xs font-bold underline
                         text-red-700 dark:text-red-400
                         hover:text-red-900 dark:hover:text-red-300
                         disabled:opacity-50 disabled:cursor-not-allowed
                         touch-manipulation"
            >
              {isResending
                ? "Sending verification email..."
                : "Resend verification email"}
            </button>
          )}
        </AlertBanner>
      ) : null}

      {/* ── OLD ────────────────────────────────────────────────────
      <form className="mt-6 lg:mt-8 space-y-4 sm:space-y-5" onSubmit={handleSubmit}>
      ─────────────────────────────────────────────────────────────

      ── NEW ────────────────────────────────────────────────────────
          space-y-4 unified — was space-y-4 sm:space-y-5 which added
          extra breathing room on sm+ for no clear reason.
          mt-6 lg:mt-8 unified to mt-6 — consistent with Register.
      ─────────────────────────────────────────────────────────── */}
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        <FormInput
          icon={Mail}
          type="email"
          name="email"
          placeholder="Email address"
          value={form.email}
          onChange={handleChange}
          error={fieldErrors.email}
        />

        <FormInput
          icon={Lock}
          type="password"
          name="password"
          placeholder="Password"
          value={form.password}
          onChange={handleChange}
          error={fieldErrors.password}
        />

        <div className="flex flex-wrap items-center justify-between gap-2">
          <label className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300 min-h-11 cursor-pointer group select-none">
            <input
              type="checkbox"
              className="form-checkbox text-primary rounded border-gray-300 dark:border-gray-600 dark:bg-[#121212] focus:ring-primary/50 cursor-pointer"
            />
            <span className="group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
              Remember me
            </span>
          </label>

          <Link
            to="/forgot-password"
            className="text-sm text-primary font-semibold hover:underline min-h-11 flex items-center px-1"
          >
            Forgot Password?
          </Link>
        </div>

        <SocialLogin />

        {/* ── OLD ────────────────────────────────────────────────
        <button
          type="submit"
          disabled={isPending}
          className="w-full bg-primary text-white py-3.5 sm:py-3 rounded-lg
                     font-bold disabled:opacity-60 disabled:cursor-not-allowed
                     hover:bg-red-700 transition-colors
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          {isPending ? "LOGGING IN..." : "LOGIN"}
        </button>
        ──────────────────────────────────────────────────────────

        ── NEW ────────────────────────────────────────────────────
            py-3.5 sm:py-3 → py-3 unified across all pages.
            hover:bg-red-700 → hover:opacity-90 — was hardcoded red,
            bypassed --color-primary token entirely.
            transition-colors → transition-opacity matches hover style.
            rounded-lg kept — Register was rounded-xl, Login was
            rounded-lg, unified to rounded-lg (matches FormInput).
        ─────────────────────────────────────────────────────────── */}
        <button
          type="submit"
          disabled={isPending}
          className="w-full bg-primary text-white py-3 rounded-lg font-bold
                     hover:opacity-90 transition-opacity
                     disabled:opacity-60 disabled:cursor-not-allowed
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          {isPending ? "LOGGING IN..." : "LOGIN"}
        </button>
      </form>

      <p className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400">
        Don't have an account?{" "}
        <Link
          to="/register"
          className="text-primary font-bold sm:ml-1 hover:underline min-h-11 items-center justify-center py-2 sm:py-0"
        >
          Create Account
        </Link>
      </p>
    </div>
  )
}
// import { Mail, Lock } from "lucide-react"
// import { Link } from "react-router-dom"

// import { FormInput } from "@shared/ui"
// import { SocialLogin } from "@features/auth"
// import { useLoginForm } from "@features/auth"
// import { ErrorCode } from "@shared/api"

// export default function Login() {
//   const {
//     form,
//     fieldErrors,
//     formError,
//     formErrorCode,
//     isPending,
//     isResending,
//     isResendSuccess,
//     handleResend,
//     handleChange,
//     handleSubmit,
//   } = useLoginForm()

//   return (
//     <>
//       <div>
//         {/* HIDE on mobile/tablet to prevent repeating AuthBrand. Shows only on desktop. */}
//         <div className="hidden lg:block">
//           <h2 className="text-3xl font-black text-gray-900 dark:text-gray-200">
//             Hello Again!
//           </h2>
//           <p className="mt-2 text-gray-500 dark:text-gray-400">
//             Login to manage your account
//           </p>
//         </div>

//         {isResendSuccess && formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED ? (
//           <div
//             role="status"
//             className="mt-4 text-sm text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3"
//           >
//             Verification email sent. Please check your inbox.
//           </div>
//         ) : formError ? (
//           <div
//             role="alert"
//             className="mt-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3"
//           >
//             <p>{formError}</p>

//             {formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED && (
//               <button
//                 type="button"
//                 onClick={handleResend}
//                 disabled={isResending}
//                 className="mt-2 min-h-11 py-1 text-xs font-bold underline text-red-700 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
//               >
//                 {isResending
//                   ? "Sending verification email..."
//                   : "Resend verification email"}
//               </button>
//             )}
//           </div>
//         ) : null}

//         <form className="mt-6 lg:mt-8 space-y-4 sm:space-y-5" onSubmit={handleSubmit}>
//           <FormInput
//             icon={Mail}
//             type="email"
//             name="email"
//             placeholder="Email address"
//             value={form.email}
//             onChange={handleChange}
//             error={fieldErrors.email}
//           />

//           <FormInput
//             icon={Lock}
//             type="password"
//             name="password"
//             placeholder="Password"
//             value={form.password}
//             onChange={handleChange}
//             error={fieldErrors.password}
//           />

//           <div className="flex flex-wrap items-center justify-between gap-2">
//             <label className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300 min-h-11 cursor-pointer group select-none">
//               <input 
//                 type="checkbox" 
//                 className="form-checkbox text-primary rounded border-gray-300 dark:border-gray-600 dark:bg-[#121212] focus:ring-primary/50 cursor-pointer" 
//               />
//               <span className="group-hover:text-gray-900 dark:group-hover:text-white transition-colors">Remember me</span>
//             </label>

//             <Link
//               to="/forgot-password"
//               className="text-sm text-primary font-semibold hover:underline min-h-11 flex items-center px-1"
//             >
//               Forgot Password?
//             </Link>
//           </div>

//           <SocialLogin />

//           <button
//             type="submit"
//             disabled={isPending}
//             className="w-full bg-primary text-white py-3.5 sm:py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed hover:bg-red-700 transition-colors shadow-lg shadow-primary/25 touch-manipulation"
//           >
//             {isPending ? "LOGGING IN..." : "LOGIN"}
//           </button>
//         </form>

//         <p className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400 ">
//           Don't have an account?{" "}
//           <Link
//             to="/register"
//             className="text-primary font-bold sm:ml-1 hover:underline min-h-11  items-center justify-center py-2 sm:py-0"
//           >
//             Create Account
//           </Link>
//         </p>
//       </div>
//     </>
//   )
// }
// import { Mail, Lock } from "lucide-react"
// import { Link } from "react-router-dom"

// import { FormInput } from "@shared/ui"
// import { SocialLogin } from "@features/auth"
// import { useLoginForm } from "@features/auth"
// import { ErrorCode } from "@shared/api"

// export default function Login() {
//   const {
//     form,
//     fieldErrors,
//     formError,
//     formErrorCode,
//     isPending,
//     isResending,
//     isResendSuccess,
//     handleResend,
//     handleChange,
//     handleSubmit,
//   } = useLoginForm()

//   return (
//     <>
//       <div>
//         {/* HIDE on mobile/tablet to prevent repeating AuthBrand. Shows only on desktop. */}
//         <div className="hidden lg:block">
//           <h2 className="text-3xl font-black text-gray-900 dark:text-white">
//             Welcome Back
//           </h2>
//           <p className="mt-2 text-gray-500 dark:text-gray-400">
//             Login to manage your account
//           </p>
//         </div>

//         {isResendSuccess && formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED ? (
//           <div
//             role="status"
//             className="mt-4 text-sm text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg px-4 py-3"
//           >
//             Verification email sent. Please check your inbox.
//           </div>
//         ) : formError ? (
//           <div
//             role="alert"
//             className="mt-4 text-sm text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg px-4 py-3"
//           >
//             <p>{formError}</p>

//             {formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED && (
//               <button
//                 type="button"
//                 onClick={handleResend}
//                 disabled={isResending}
//                 className="mt-2 min-h-11 py-1 text-xs font-bold underline text-red-700 dark:text-red-400 hover:text-red-900 dark:hover:text-red-300 disabled:opacity-50 disabled:cursor-not-allowed touch-manipulation"
//               >
//                 {isResending
//                   ? "Sending verification email..."
//                   : "Resend verification email"}
//               </button>
//             )}
//           </div>
//         ) : null}

//         <form className="mt-6 lg:mt-8 space-y-4 sm:space-y-5" onSubmit={handleSubmit}>
//           <FormInput
//             icon={Mail}
//             type="email"
//             name="email"
//             placeholder="Email address"
//             value={form.email}
//             onChange={handleChange}
//             error={fieldErrors.email}
//           />

//           <FormInput
//             icon={Lock}
//             type="password"
//             name="password"
//             placeholder="Password"
//             value={form.password}
//             onChange={handleChange}
//             error={fieldErrors.password}
//           />

//           <div className="flex flex-wrap items-center justify-between gap-2">
//             <label className="flex items-center space-x-2 text-sm text-gray-700 dark:text-gray-300 min-h-11 cursor-pointer group select-none">
//               <input 
//                 type="checkbox" 
//                 className="form-checkbox text-primary rounded border-gray-300 dark:border-gray-600 dark:bg-[#121212] focus:ring-primary/50 cursor-pointer" 
//               />
//               <span className="group-hover:text-gray-900 dark:group-hover:text-white transition-colors">Remember me</span>
//             </label>

//             <Link
//               to="/forgot-password"
//               className="text-sm text-primary font-semibold hover:underline min-h-11 flex items-center px-1"
//             >
//               Forgot Password?
//             </Link>
//           </div>

//           <SocialLogin />

//           <button
//             type="submit"
//             disabled={isPending}
//             className="w-full bg-primary text-white py-3.5 sm:py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed hover:bg-red-700 transition-colors shadow-lg shadow-primary/25 touch-manipulation"
//           >
//             {isPending ? "LOGGING IN..." : "LOGIN"}
//           </button>
//         </form>

//         <p className="mt-8 text-center text-sm text-gray-600 dark:text-gray-400 flex flex-col sm:block">
//           Don't have an account?{" "}
//           <Link
//             to="/register"
//             className="text-primary font-bold sm:ml-1 hover:underline min-h-[44px] inline-flex items-center justify-center py-2 sm:py-0"
//           >
//             Create Account
//           </Link>
//         </p>
//       </div>
//     </>
//   )
// }