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

     

      {/* ── NEW ─────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <AuthIconBadge icon={Lock} badge="?" />
      </div>

      <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-200">
        Enter your email address and we will send you a link to reset
        your password.
      </p>

      

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
