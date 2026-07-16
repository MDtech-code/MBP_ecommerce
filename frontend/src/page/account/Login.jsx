// src/pages/account/Login.jsx
import { Mail, Lock } from "lucide-react"
import { Link } from "react-router-dom"
import AuthLayout from "../../components/account/AuthLayout"
import FormInput from "../../components/common/FormInput"
import SocialLogin from "../../components/account/SocialLogin"
import { useLoginForm } from "../../hooks/account/useLoginForm"

import { ErrorCode } from "../../api/transformers"

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
    <AuthLayout
      brandProps={{
        title: "WELCOME BACK",
        highlight: "RIDER!",
        description:
          "Login to your account and continue your journey with BikeExpress.",
      }}
    >
      <div>
        <h2 className="text-3xl font-black text-gray-900">Welcome Back</h2>

        <p className="mt-2 text-gray-500">Login to manage your account</p>

         {/* ── Resend success — replaces error banner entirely ──────────── */}
        {/* When user clicks resend and it succeeds, the error banner       */}
        {/* disappears and this green confirmation takes its place.         */}
        {isResendSuccess && formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED ? (
          <div
            role="status"
            className="mt-4 text-sm text-green-700 bg-green-50 border border-green-200 rounded-lg px-4 py-3"
          >
            Verification email sent. Please check your inbox.
          </div>

        ) : formError ? (
          /* ── Error banner — wrong credentials, unverified, etc. ──────── */
          <div
            role="alert"
            className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3"
          >
            <p>{formError}</p>

            {/* Resend button — only shown when email_not_verified ────────── */}
            {/* This is the original use case: non-tech user sees message    */}
            {/* + actionable button. No URL manipulation needed.             */}
            {formErrorCode === ErrorCode.EMAIL_NOT_VERIFIED && (
              <button
                type="button"
                onClick={handleResend}
                disabled={isResending}
                className="mt-2 text-xs font-bold underline text-red-700 hover:text-red-900 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isResending
                  ? "Sending verification email..."
                  : "Resend verification email"}
              </button>
            )}
          </div>

        ) : null}

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>

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

          <div className="flex items-center justify-between">
            <label className="flex items-center space-x-2 text-sm">
              <input type="checkbox" className="form-checkbox text-primary" />
              <span>Remember me</span>
            </label>

            <Link
              to="/forgot-password"
              className="text-sm text-primary font-semibold hover:underline"
            >
              Forgot Password?
            </Link>
          </div>

          <SocialLogin />

          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-primary text-white py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isPending ? "LOGGING IN..." : "LOGIN"}
          </button>

        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Don't have an account?{" "}
          <Link
            to="/register"
            className="text-primary font-bold ml-1 hover:underline"
          >
            Create Account
          </Link>
        </p>

      </div>
    </AuthLayout>
  )
}
