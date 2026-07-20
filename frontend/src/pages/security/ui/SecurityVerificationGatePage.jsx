// src/pages/security/ui/SecurityVerificationGatePage.jsx

import { Mail, Smartphone, ArrowLeft, ShieldCheck } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";
import { useSecurityGate } from "@features/auth";

const PURPOSE_LABELS = {
  change_password: "Change Password",
  change_email:    "Change Email Address",
  delete_account:  "Delete Account",
};

export default function SecurityVerificationGatePage() {
  const [searchParams]  = useSearchParams();
  const purpose         = searchParams.get("purpose") ?? "change_password";
  const purposeLabel    = PURPOSE_LABELS[purpose] ?? "Sensitive Action";

  const {
    isPending,
    formError,
    secondsRemaining,
    handleEmailVerification,
  } = useSecurityGate(purpose);

  return (
    <div className="w-full">

      {/* Back */}
      <Link
        to="/security"
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-primary transition-colors mb-8"
      >
        <ArrowLeft size={18} />
        Back to Security
      </Link>

      {/* Card */}
      <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8 lg:p-10">

        {/* Header */}
        <div className="flex items-center gap-4 mb-2">
          <div className="p-3 bg-primary/10 rounded-2xl">
            <ShieldCheck size={24} className="text-primary" />
          </div>
          <div>
            <h1 className="text-2xl font-black text-gray-900">
              Verify Your Identity
            </h1>
            <p className="text-sm text-gray-500 mt-0.5">
              To continue with <span className="font-semibold text-gray-700">{purposeLabel}</span>
            </p>
          </div>
        </div>

        <p className="text-gray-500 text-sm mt-4 mb-8 max-w-lg">
          For your security, we need to verify your identity before
          making changes to your account. Choose a verification method below.
        </p>

        {/* Error */}
        {formError && (
          <div
            role="alert"
            className="mb-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 max-w-lg"
          >
            {formError}
            {secondsRemaining && (
              <span className="font-semibold"> Wait {secondsRemaining}s before retrying.</span>
            )}
          </div>
        )}

        {/* Verification Methods */}
        <div className="space-y-4 max-w-lg">

          {/* Email — active */}
          <button
            type="button"
            onClick={handleEmailVerification}
            disabled={isPending}
            className="w-full flex items-center gap-4 p-5 rounded-2xl border-2 border-gray-200 hover:border-primary hover:bg-primary/5 transition-all text-left disabled:opacity-60 disabled:cursor-not-allowed group"
          >
            <div className="p-3 bg-blue-50 rounded-xl group-hover:bg-primary/10 transition-colors">
              <Mail size={22} className="text-blue-600 group-hover:text-primary" />
            </div>
            <div className="flex-1">
              <p className="font-bold text-gray-900">Email Verification</p>
              <p className="text-sm text-gray-500 mt-0.5">
                We will send a 6-digit code to your registered email address.
              </p>
            </div>
            {isPending && (
              <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            )}
          </button>

          {/* Mobile — disabled */}
          <div className="w-full flex items-center gap-4 p-5 rounded-2xl border-2 border-gray-100 bg-gray-50 opacity-60 cursor-not-allowed">
            <div className="p-3 bg-gray-100 rounded-xl">
              <Smartphone size={22} className="text-gray-400" />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <p className="font-bold text-gray-500">Mobile OTP</p>
                <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full font-semibold">
                  Coming Soon
                </span>
              </div>
              <p className="text-sm text-gray-400 mt-0.5">
                Verify via SMS code sent to your phone number.
              </p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}