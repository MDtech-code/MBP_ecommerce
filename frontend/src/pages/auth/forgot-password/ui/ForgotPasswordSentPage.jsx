// src/pages/auth/ForgotPasswordSent.jsx

import { Link, useLocation } from "react-router-dom"
import { Mail } from "lucide-react"

import { AuthIconBadge } from "@widgets/auth"
import {AuthPageHeader} from "@widgets/auth"

export default function ForgotPasswordSentPage() {
  const location = useLocation()
  const email = location.state?.email ?? "your email address"

  return (
    <div className="text-center">

      
      <AuthPageHeader
  title="Check Your Email"
/>

      {/* ── OLD ──────────────────────────────────────────────────────
          No badge on this page — icon circle without badge span.
          Was hand-rolled inline.

          <div className="mx-auto w-24 h-24 rounded-full bg-gray-100
                          flex items-center justify-center">
            <Mail size={45} className="text-gray-700" />
          </div>
          ──────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          badge omitted — AuthIconBadge defaults to null, renders
          no badge. Matches original design intent for this page.
      ─────────────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <AuthIconBadge icon={Mail} />
      </div>

      <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-200">
        We sent a password reset link to
        <br />
        <span className="font-bold text-gray-900 dark:text-gray-300">
          {email}
        </span>
      </p>

      <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-200">
        Did not receive it? Check your spam folder or try again.
      </p>

      <div className="mt-7 space-y-3">
        <Link
          to="/forgot-password"
          className="block w-full bg-primary text-white py-3 rounded-lg
                     font-bold text-center hover:opacity-90 transition-opacity
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          TRY AGAIN
        </Link>

        <Link
          to="/login"
          className="block w-full text-center text-primary text-sm
                     font-semibold py-2 hover:underline"
        >
          Back to Login
        </Link>
      </div>
    </div>
  )
}
// // src/pages/account/ForgotPasswordSent.jsx

// import { Link, useLocation } from "react-router-dom";
// import { Mail } from "lucide-react";



// export default function ForgotPasswordSent() {
//   const location = useLocation();
//   // Email passed via navigate state from useForgotPasswordForm
//   const email = location.state?.email ?? "your email address";

//   return (
//     <>
//       <div>
//         <h2 className="hidden lg:block mt-8 text-2xl text-center text-grey-300 font-black">
//           Check Your Email
//         </h2>

//         <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center">
//           <Mail size={45} className="text-gray-700" />
//         </div>

//         <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-200">
//           We sent a password reset link to
//           <br />
//           <span className="font-bold text-gray-900 dark:text-gray-300">{email}</span>
//         </p>

//         <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-200">
//           Did not receive it? Check your spam folder or try again.
//         </p>

//         <div className="mt-7 space-y-3">
//           <Link
//             to="/forgot-password"
//             className="block w-full bg-primary text-white py-3 rounded-lg font-bold text-center"
//           >
//             TRY AGAIN
//           </Link>

//           <Link
//             to="/login"
//             className="block w-full text-center text-primary text-sm font-semibold py-2"
//           >
//             Back to Login
//           </Link>
//         </div>
//       </div>
//     </>
//   );
// }