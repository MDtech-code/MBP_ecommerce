// src/pages/security/ui/ChangeEmailFormPage.jsx

import { Mail, ArrowLeft, CheckCircle } from "lucide-react";
import { Link, useNavigate }            from "react-router-dom";
import { FormInput }                    from "@shared/ui";
import { useChangeEmailForm }           from "@features/auth";

export default function ChangeEmailFormPage() {
  const {
    newEmail,
    verificationToken,
    fieldErrors,
    formError,
    isPending,
    isSuccess,
    maskedNewEmail,
    handleChange,
    handleSubmit,
    handleGoToNewEmailOTP,
  } = useChangeEmailForm();

  const navigate = useNavigate();

  // ── No verification token — redirect to gate ───────────────────────────────
  if (!verificationToken) {
    return (
      <div className="w-full">
        <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-10 text-center max-w-md mx-auto">
          <p className="text-gray-500 mb-4">
            Identity verification required before changing your email.
          </p>
          <button
            onClick={() => navigate("/security/verify?purpose=change_email")}
            className="bg-primary text-white px-6 py-3 rounded-xl font-bold hover:opacity-90 transition"
          >
            Verify Identity First
          </button>
        </div>
      </div>
    );
  }

  // ── Success — OTP sent to new email ───────────────────────────────────────
  if (isSuccess) {
    return (
      <div className="w-full">
        <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-10">
          <div className="max-w-md mx-auto text-center">
            <CheckCircle size={56} className="text-green-500 mx-auto mb-4" />
            <h2 className="text-2xl font-black text-gray-900 mb-2">
              Verification Code Sent
            </h2>
            <p className="text-sm text-gray-500 mb-1">
              We sent a 6-digit code to your new address:
            </p>
            <p className="text-base font-bold text-gray-800 mb-6">
              {maskedNewEmail}
            </p>
            <div className="bg-blue-50 border border-blue-100 rounded-xl px-5 py-4 text-sm text-blue-700 text-left mb-8">
              <p className="font-semibold mb-1">What happens next:</p>
              <ul className="list-disc list-inside space-y-1 text-blue-600">
                <li>Enter the code sent to your new email</li>
                <li>Your email will be updated immediately</li>
                <li>You will be logged out for security</li>
                <li>Log back in with your new email address</li>
              </ul>
            </div>
            <button
              onClick={handleGoToNewEmailOTP}
              className="w-full bg-primary text-white py-3.5 rounded-xl font-bold hover:opacity-90 transition"
            >
              Enter Verification Code
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── Form ──────────────────────────────────────────────────────────────────
  return (
    <div className="w-full">
      <Link
        to="/security"
        className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-primary transition-colors mb-8"
      >
        <ArrowLeft size={18} />
        Back to Security
      </Link>

      <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8 lg:p-10">
        <div className="max-w-xl">
          <h1 className="text-2xl font-black text-gray-900">
            Enter New Email Address
          </h1>
          <p className="mt-2 text-gray-500 text-sm">
            Your identity has been verified. Enter the email address
            you want to use for your account.
          </p>
        </div>

        {formError && (
          <div role="alert" className="mt-6 max-w-xl rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-8 space-y-5 max-w-xl">
          <div>
            <label className="block mb-2 text-sm font-semibold text-gray-800">
              New Email Address
            </label>
            <FormInput
              icon={Mail}
              type="email"
              name="new_email"
              placeholder="Enter your new email address"
              value={newEmail}
              onChange={handleChange}
              error={fieldErrors.new_email}
            />
          </div>

          <div className="flex items-center gap-4 pt-2">
            <Link
              to="/security"
              className="rounded-xl border border-gray-300 px-6 py-3 font-semibold text-gray-700 hover:bg-gray-50 transition text-sm"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-xl bg-primary px-8 py-3 font-bold text-white hover:opacity-90 transition disabled:opacity-60 disabled:cursor-not-allowed text-sm"
            >
              {isPending ? "SENDING CODE..." : "SEND VERIFICATION CODE"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}