// src/pages/auth/VerifyEmail.jsx

import { Link } from "react-router-dom"
import { MailCheck } from "lucide-react"

import { AuthIconBadge } from "@shared/ui"
import { AlertBanner } from "@shared/ui"
import { useVerifyEmailPage } from "@features/auth"

export default function VerifyEmail() {
  const {
    email,
    tokenFromUrl,
    isVerifying,
    isResending,
    isVerifySuccess,
    verifyErrorMsg,
    resendErrorMsg,
    resendSuccessMsg,
    handleResend,
  } = useVerifyEmailPage()

  const showVerifyingState = tokenFromUrl && !verifyErrorMsg

  return (
    <div className="text-center">

      {/* ── OLD ──────────────────────────────────────────────────────
          text-black-400 — invalid, black has no shade scale in Tailwind.
          dark:text-grey-300 — invalid, British spelling, silently ignored.
          Text was rendering with no color applied, inheriting unpredictably.

          <h2 className="hidden lg:block mt-8 text-2xl font-black
                         text-black-400 dark:text-grey-300">
            Verify Your Email
          </h2>
          ──────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          Valid color classes. Consistent with Login and Register h2.
          mt-2 instead of mt-8 — mt-8 pushed icon too far down on desktop,
          AuthBrand already provides top spacing context on mobile/tablet.
      ─────────────────────────────────────────────────────────────── */}
      <div className="hidden lg:block">
        <h2 className="text-3xl font-black text-gray-900 dark:text-gray-100">
          Verify Your Email
        </h2>
      </div>

      {/* ── OLD ──────────────────────────────────────────────────────
          Hand-rolled icon circle with badge — repeated pattern.

          <div className="mx-auto w-24 h-24 rounded-full bg-gray-100
                          flex items-center justify-center relative">
            <MailCheck size={45} className="text-gray-700" />
            <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full
                             bg-primary text-white flex items-center
                             justify-center font-bold">
              ✓
            </span>
          </div>
          ──────────────────────────────────────────────────────────── */}

      {/* ── NEW ─────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <AuthIconBadge icon={MailCheck} badge="✓" />
      </div>

      {showVerifyingState ? (
        <p className="mt-5 text-gray-600 text-sm font-semibold">
          {isVerifying || !isVerifySuccess
            ? "Verifying your email, please wait..."
            : "Email verified! Redirecting..."}
        </p>
      ) : (
        <>
          {/* ── OLD ────────────────────────────────────────────────
              Hand-rolled alert banners.

              {verifyErrorMsg && (
                <div role="alert" className="mt-5 text-sm text-red-600
                  bg-red-50 border border-red-200 rounded-lg px-4 py-3
                  font-semibold">
                  {verifyErrorMsg} — Please request a new verification
                  link below.
                </div>
              )}
              ──────────────────────────────────────────────────────── */}

          {/* ── NEW ─────────────────────────────────────────────────── */}
          {verifyErrorMsg && (
            <AlertBanner type="error" className="mt-5">
              {verifyErrorMsg} — Please request a new verification link below.
            </AlertBanner>
          )}

          <p className="mt-5 text-gray-600 dark:text-gray-200 text-sm">
            We have sent a verification link to
            <br />
            <span className="font-bold text-gray-900 dark:text-gray-300">
              {email || "your email address"}
            </span>
          </p>

          <p className="mt-5 text-sm text-gray-500 dark:text-gray-300">
            Please check your inbox and click on the verification link to
            activate your account.
          </p>

          {/* ── OLD ────────────────────────────────────────────────
              {resendSuccessMsg && (
                <div role="status" className="mt-4 text-sm text-green-700
                  bg-green-50 border border-green-200 rounded-lg px-4 py-2">
                  {resendSuccessMsg}
                </div>
              )}
              {resendErrorMsg && (
                <div role="alert" className="mt-4 text-sm text-red-600
                  bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                  {resendErrorMsg}
                </div>
              )}
              ──────────────────────────────────────────────────────── */}

          {/* ── NEW ─────────────────────────────────────────────────── */}
          {resendSuccessMsg && (
            <AlertBanner type="success" className="mt-4">
              {resendSuccessMsg}
            </AlertBanner>
          )}
          {resendErrorMsg && (
            <AlertBanner type="error" className="mt-4">
              {resendErrorMsg}
            </AlertBanner>
          )}

          <button
            onClick={handleResend}
            disabled={isResending}
            className="mt-8 w-full border border-primary text-primary py-3
                       rounded-lg font-bold
                       hover:bg-primary hover:text-white transition-colors
                       disabled:opacity-60 disabled:cursor-not-allowed
                       touch-manipulation"
          >
            {isResending ? "SENDING..." : "RESEND EMAIL"}
          </button>

          <Link
            to="/login"
            className="mt-4 block text-primary font-semibold text-sm hover:underline"
          >
            Back to Login
          </Link>
        </>
      )}
    </div>
  )
}
// // src/pages/account/VerifyEmail.jsx
// import { Link } from "react-router-dom";
// import { MailCheck } from "lucide-react";

// import { useVerifyEmailPage } from "@features/auth";



// export default function VerifyEmail() {
//   const {
//     email,
//     tokenFromUrl,
//     isVerifying,
//     isResending,
//     isVerifySuccess,
//     verifyErrorMsg,
//     resendErrorMsg,
//     resendSuccessMsg,
//     handleResend,
//   } = useVerifyEmailPage();

//   // Only show the loading screen if we have a token AND it hasn't errored out
//   const showVerifyingState = tokenFromUrl && !verifyErrorMsg;

//   return (
//     <>
//       <div className="text-center">
//         <h2 className="hidden lg:block mt-8 text-2xl font-black text-black-400 dark:text-grey-300">
//           Verify Your Email
//         </h2>

//         <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
//           <MailCheck size={45} className="text-gray-700" />
//           <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
//             ✓
//           </span>
//         </div>

//         {showVerifyingState ? (
//           <p className="mt-5 text-gray-600 text-sm font-semibold">
//             {isVerifying || !isVerifySuccess
//               ? "Verifying your email, please wait..."
//               : "Email verified! Redirecting..."}
//           </p>
//         ) : (
//           <>
//             {/* If the URL token failed (expired/invalid), display why right here */}
//             {verifyErrorMsg && (
//               <div role="alert" className="mt-5 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 font-semibold">
//                 {verifyErrorMsg} — Please request a new verification link below.
//               </div>
//             )}

//             <p className="mt-5 text-gray-600 dark:text-gray-200 text-sm">
//               We have sent a verification link to
//               <br />
//               <span className="font-bold text-gray-900 dark:text-gray-300">
//                 {email || "your email address"}
//               </span>
//             </p>

//             <p className="mt-5 text-sm text-gray-500 dark:text-gray-300">
//               Please check your inbox and click on the verification link to
//               activate your account.
//             </p>

//             {resendSuccessMsg && (
//               <div role="status" className="mt-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2">
//                 {resendSuccessMsg}
//               </div>
//             )}

//             {resendErrorMsg && (
//               <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
//                 {resendErrorMsg}
//               </div>
//             )}

//             <button
//               onClick={handleResend}
//               disabled={isResending}
//               className="mt-8 w-full border border-primary text-primary py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed hover:bg-primary hover:text-white transition-colors"
//             >
//               {isResending ? "SENDING..." : "RESEND EMAIL"}
//             </button>

//             <Link
//               to="/login"
//               className="mt-8 block text-primary font-semibold text-sm hover:underline"
//             >
//               Back to Login
//             </Link>
//           </>
//         )}
//       </div>
//     </>
//   );
// }