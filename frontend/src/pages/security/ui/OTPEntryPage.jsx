// src/pages/security/ui/OTPEntryPage.jsx

import { ArrowLeft } from "lucide-react";
import { useNavigate }          from "react-router-dom";
import {OTPInput   }              from "@shared/ui/OTPInput";
import {ResendTimer}              from "@shared/ui/ResendTimer";
import { useOTPEntryForm }      from "@features/auth";

const PURPOSE_LABELS = {
  change_password: "Change Password",
  change_email:    "Change Email Address",
  delete_account:  "Delete Account",
};

export default function OTPEntryPage() {
  const navigate = useNavigate();

  const {
    otp,
    inputRefs,
    purpose,
    maskedEmail,
    formError,
    attemptsLeft,
    isVerifying,
    isResending,
    isComplete,
    resendSeconds,
    handleOtpChange,
    handleKeyDown,
    handlePaste,
    handleSubmit,
    handleResend,
  } = useOTPEntryForm();

  const purposeLabel = PURPOSE_LABELS[purpose] ?? "Verification";

  return (
    <div className="w-full">

      {/* Back — goes back to gate page */}
      <button
        type="button"
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-primary transition-colors mb-8"
      >
        <ArrowLeft size={18} />
        Use another way
      </button>

      {/* Card */}
      <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8 lg:p-10">

        {/* Header */}
        <div className="max-w-md mx-auto text-center">

          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-5">
            <span className="text-3xl">📧</span>
          </div>

          <h1 className="text-2xl font-black text-gray-900">
            Enter Verification Code
          </h1>

          <p className="mt-2 text-gray-500 text-sm">
            We sent a 6-digit code to{" "}
            <span className="font-bold text-gray-800">{maskedEmail}</span>
            {" "}for{" "}
            <span className="font-semibold text-gray-700">{purposeLabel}</span>.
          </p>

          <p className="mt-1 text-xs text-gray-400">
            Code expires in 10 minutes.
          </p>
        </div>

        {/* OTP Input */}
        <div className="mt-8 max-w-sm mx-auto space-y-6">

          <OTPInput
            otp={otp}
            inputRefs={inputRefs}
            onChange={handleOtpChange}
            onKeyDown={handleKeyDown}
            onPaste={handlePaste}
            disabled={isVerifying}
            hasError={!!formError}
          />

          {/* Error */}
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

          {/* Submit */}
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!isComplete || isVerifying}
            className="w-full bg-primary text-white py-3.5 rounded-xl font-bold hover:opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isVerifying ? (
              <span className="flex items-center justify-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Verifying...
              </span>
            ) : "Verify Code"}
          </button>

          {/* Resend */}
          <ResendTimer
            seconds={resendSeconds}
            onResend={handleResend}
            isResending={isResending}
          />

        </div>
      </div>
    </div>
  );
}