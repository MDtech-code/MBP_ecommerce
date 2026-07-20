// src/pages/security/ui/NewEmailOTPPage.jsx


import {OTPInput}      from "@shared/ui/OTPInput";
import { useNewEmailOTPForm } from "@features/auth";


export default function NewEmailOTPPage() {
  const {
    otp,
    inputRefs,
    maskedNewEmail,
    formError,
    attemptsLeft,
    isPending,
    isComplete,
    handleOtpChange,
    handleKeyDown,
    handlePaste,
    handleSubmit,
  } = useNewEmailOTPForm();

  return (
    <div className="w-full">

      <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8 lg:p-10">

        <div className="max-w-md mx-auto text-center">

          <div className="w-16 h-16 bg-green-50 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <span className="text-3xl">✉️</span>
          </div>

          <h1 className="text-2xl font-black text-gray-900">
            Confirm New Email
          </h1>

          <p className="mt-2 text-gray-500 text-sm">
            Enter the 6-digit code sent to your new address:{" "}
            <span className="font-bold text-gray-800">{maskedNewEmail}</span>
          </p>

          <p className="mt-1 text-xs text-gray-400">
            After confirming, you will be logged out and must log in with your new email.
          </p>
        </div>

        <div className="mt-8 max-w-sm mx-auto space-y-6">

          <OTPInput
            otp={otp}
            inputRefs={inputRefs}
            onChange={handleOtpChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            disabled={isPending}
            hasError={!!formError}
          />

          {formError && (
            <div role="alert" className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-xl px-4 py-3 text-center">
              {formError}
              {attemptsLeft !== null && (
                <span className="block font-semibold mt-0.5">
                  {attemptsLeft} attempt{attemptsLeft !== 1 ? "s" : ""} remaining.
                </span>
              )}
            </div>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isComplete || isPending}
            className="w-full bg-primary text-white py-3.5 rounded-xl font-bold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isPending ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Confirming...
              </span>
            ) : "Confirm New Email"}
          </button>

          <p className="text-xs text-gray-400 text-center">
            Did not receive the code? Go back and request a new email change.
          </p>

        </div>
      </div>
    </div>
  );
}