// src/pages/auth/ResetPassword.jsx

import { Link } from "react-router-dom"
import { Lock } from "lucide-react"

import { FormInput } from "@shared/ui"

import { AuthIconBadge } from "@widgets/auth"
import { useResetPasswordForm } from "@features/auth"
import {AuthPageHeader} from "@widgets/auth"
import  {Toast}  from "@shared/ui"

export default function ResetPasswordPage() {
  const {
    fields,
    handleChange,
    handleSubmit,
    isPending,
    passwordError,
    confirmPasswordError,
    formError,
    tokenMissing,
  } = useResetPasswordForm()

  if (tokenMissing) {
    return (
      <div className="text-center">

        
        <AuthPageHeader
  title="Reset Password"
/>

      

        {/* ── NEW ──────────────────────────────────────────────────── */}
        <div className="mt-6">
          <AuthIconBadge icon={Lock} badge="✕" />
        </div>

        
        {/* ── NEW ──────────────────────────────────────────────────── */}
       {formError && (
               <Toast type="error" >
                 {formError}
               </Toast>
             )}
       

        <div className="mt-6">
          <Link
            to="/forgot-password"
            className="block w-full bg-primary text-white py-3 rounded-lg
                       font-bold text-center hover:opacity-90 transition-opacity
                       shadow-lg shadow-primary/25 touch-manipulation"
          >
            REQUEST NEW LINK
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div>

     
      <div className="hidden lg:block">
        <h2 className="text-3xl font-black text-gray-900 dark:text-gray-100">
          Reset Password
        </h2>
      </div>

      

      {/* ── NEW ──────────────────────────────────────────────────────── */}
      <div className="mt-6">
        <AuthIconBadge icon={Lock} badge="↻" />
      </div>

      <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-300">
        Create a new password for your account.
      </p>

      

      {/* ── NEW ──────────────────────────────────────────────────────── */}
      {formError && (
               <Toast type="error" >
                 {formError}
               </Toast>
             )}

      <form onSubmit={handleSubmit} className="mt-6 space-y-4">
        <FormInput
          icon={Lock}
          type="password"
          name="password"
          placeholder="Enter new password"
          value={fields.password}
          onChange={handleChange}
          error={passwordError}
        />

        <FormInput
          icon={Lock}
          type="password"
          name="confirm_password"
          placeholder="Confirm new password"
          value={fields.confirm_password}
          onChange={handleChange}
          error={confirmPasswordError}
        />

        {/* ── NEW ──────────────────────────────────────────────────── */}
        <button
          type="submit"
          disabled={isPending}
          className="w-full bg-primary text-white py-3 rounded-lg font-bold
                     hover:opacity-90 transition-opacity
                     disabled:opacity-60 disabled:cursor-not-allowed
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          {isPending ? "RESETTING..." : "RESET PASSWORD"}
        </button>
      </form>
    </div>
  )
}
