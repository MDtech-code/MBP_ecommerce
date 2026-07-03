import { Link } from "react-router-dom"
import { MailCheck } from "lucide-react";
import AuthLayout from "../../components/account/AuthLayout";
import { useVerifyEmailPage } from "../../hooks/account/useVerifyEmailPage"

const BRAND_PROPS = {
  title: "CHECK YOUR",
  highlight: "INBOX!",
  description: "One step away from joining the BikeExpress family.",
}
export default function VerifyEmail() {
  const {
    email,
    tokenFromUrl,
    isVerifying,
    isResending,
    verifyErrorMsg,
    resendErrorMsg,
    resendSuccessMsg,
    handleResend,
  } = useVerifyEmailPage()
    console.log(tokenFromUrl)
    return (
    <AuthLayout brandProps={BRAND_PROPS}>
      <div className="text-center">

        <h2 className="mt-8 text-2xl font-black text-black-400">
          Verify Your Email
        </h2>

        <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
          <MailCheck size={45} className="text-gray-700" />
          <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
            ✓
          </span>
        </div>

        {/* Token in URL — verifying automatically */}
        {tokenFromUrl ? (
          
          
          <p className="mt-5 text-gray-600 text-sm">
            {isVerifying
              ? "Verifying your email, please wait..."
              : verifyErrorMsg
              ? verifyErrorMsg
              : "Redirecting..."}
          </p>
              
        ) : (
          // No token — normal waiting state after register
          <>
            <p className="mt-5 text-gray-600 text-sm">
              We have sent a verification link to
              <br />
              <span className="font-bold text-gray-900">
                {email || "your email address"}
              </span>
            </p>

            <p className="mt-5 text-sm text-gray-500">
              Please check your inbox and click on the verification
              link to activate your account.
            </p>

            {resendSuccessMsg && (
              <div role="status" className="mt-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-2">
                {resendSuccessMsg}
              </div>
            )}

            {resendErrorMsg && (
              <div role="alert" className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2">
                {resendErrorMsg}
              </div>
            )}

            <button
              onClick={handleResend}
              disabled={isResending}
              className="mt-8 w-full border border-primary text-primary py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isResending ? "SENDING..." : "RESEND EMAIL"}
            </button>

            <Link
              to="/login"
              className="mt-8 block text-primary font-semibold text-sm hover:underline"
            >
              Back to Login
            </Link>
          </>
        )}

      </div>
    </AuthLayout>
  )
}
//   return (
//     <AuthLayout brandProps={BRAND_PROPS}>
//       <div className="text-center">
//         <h2 className="mt-8 text-2xl font-black text-black-400">
//           Verify Your Email
//         </h2>
//         <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
//           <MailCheck size={45} className="text-gray-700" />
//           <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
//             ✓
//           </span>
//         </div>

        

//         <p className="mt-5 text-gray-600 text-sm">
//           We have sent a verification link to
//           <br />
//           <span className="font-bold text-gray-900">rider@example.com</span>
//         </p>

//         <p className="mt-5 text-sm text-gray-500">
//           Please check your inbox and click on the verification link to activate
//           your account.
//         </p>

//         <button className="mt-8 w-full border border-primary text-primary py-3 rounded-lg font-bold">
//           RESEND EMAIL
//         </button>

//         <p className="mt-8 text-primary font-semibold text-sm">Back to Login</p>
//       </div>
//     </AuthLayout>
//   );
// }

