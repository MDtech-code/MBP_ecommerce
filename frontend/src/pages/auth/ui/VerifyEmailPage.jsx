// src/pages/account/VerifyEmail.jsx
import { Link } from "react-router-dom";
import { MailCheck } from "lucide-react";
import {AuthLayout} from "@widgets/auth-layout";
import { useVerifyEmail } from "@features/auth";

const BRAND_PROPS = {
  title: "CHECK YOUR",
  highlight: "INBOX!",
  description: "One step away from joining the BikeExpress family.",
};

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
  } = useVerifyEmail();

  // Only show the loading screen if we have a token AND it hasn't errored out
  const showVerifyingState = tokenFromUrl && !verifyErrorMsg;

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

        {showVerifyingState ? (
          <p className="mt-5 text-gray-600 text-sm font-semibold">
            {isVerifying || !isVerifySuccess
              ? "Verifying your email, please wait..."
              : "Email verified! Redirecting..."}
          </p>
        ) : (
          <>
            {/* If the URL token failed (expired/invalid), display why right here */}
            {verifyErrorMsg && (
              <div role="alert" className="mt-5 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3 font-semibold">
                {verifyErrorMsg} — Please request a new verification link below.
              </div>
            )}

            <p className="mt-5 text-gray-600 text-sm">
              We have sent a verification link to
              <br />
              <span className="font-bold text-gray-900">
                {email || "your email address"}
              </span>
            </p>

            <p className="mt-5 text-sm text-gray-500">
              Please check your inbox and click on the verification link to
              activate your account.
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
              className="mt-8 w-full border border-primary text-primary py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed hover:bg-primary hover:text-white transition-colors"
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
  );
}