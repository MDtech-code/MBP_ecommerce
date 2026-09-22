// src/pages/auth/VerifyEmail.jsx

import { Link } from "react-router-dom"
import { MailCheck } from "lucide-react"

import { AuthIconBadge } from "@widgets/auth"
import { AlertBanner } from "@shared/ui"
import { useVerifyEmailPage } from "@features/auth"
import {AuthPageHeader} from "@widgets/auth"

export default function VerifyEmailPage() {
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

      
      <AuthPageHeader
  title="Verify Your Email"
/>

     
      {/* ──  ─────────────────────────────────────────────────────── */}
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
         

          {/* ── ─────────────────────────────────────────────────── */}
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

          

          {/* ──  ─────────────────────────────────────────────────── */}
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
