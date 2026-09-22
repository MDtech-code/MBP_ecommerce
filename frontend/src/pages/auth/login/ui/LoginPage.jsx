// src/pages/login/Login.jsx

import { Mail, Lock } from "lucide-react"
import { Link } from "react-router-dom"

import { FormInput } from "@shared/ui"
import { AlertBanner } from "@shared/ui"
import { SocialLogin } from "@features/auth"
import { useLoginForm } from "@features/auth"
import { ErrorCode } from "@shared/api"
import {AuthPageHeader} from "@widgets/auth"

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
      <AuthPageHeader
  title="Hello Again!"
  subtitle="Login to manage your account"
/>
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
