// src/pages/account/security/ChangePassword.jsx

import { ArrowLeft, Lock } from "lucide-react";
import { Link }            from "react-router-dom";
import { FormInput }       from "@shared/ui";
import { PasswordStrength } from "@features/auth";
import { useChangePasswordForm } from "@features/auth";

export default function ChangePassword() {
  const {
    fields,
    handleChange,
    handleSubmit,
    isPending,
    currentPasswordError,
    newPasswordError,
    confirmNewPasswordError,
    formError,
  } = useChangePasswordForm();

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
        <div className="max-w-xl">
          <h1 className="text-3xl font-black text-gray-900">
            Change Password
          </h1>
          <p className="mt-2 text-gray-500">
            Keep your BikeExpress account secure by updating your
            password regularly.
          </p>
        </div>

        {/* Form error */}
        {formError && (
          <div
            role="alert"
            className="mt-6 max-w-xl rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600"
          >
            {formError}
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-8 space-y-5 max-w-xl">

          <div>
            <label className="block mb-2 text-sm font-semibold text-gray-800">
              Current Password
            </label>
            <FormInput
              icon={Lock}
              type="password"
              name="current_password"
              placeholder="Enter your current password"
              value={fields.current_password}
              onChange={handleChange}
              error={currentPasswordError}
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-semibold text-gray-800">
              New Password
            </label>
            <FormInput
              icon={Lock}
              type="password"
              name="new_password"
              placeholder="Enter your new password"
              value={fields.new_password}
              onChange={handleChange}
              error={newPasswordError}
            />
          </div>

          <div>
            <label className="block mb-2 text-sm font-semibold text-gray-800">
              Confirm New Password
            </label>
            <FormInput
              icon={Lock}
              type="password"
              name="confirm_new_password"
              placeholder="Confirm your new password"
              value={fields.confirm_new_password}
              onChange={handleChange}
              error={confirmNewPasswordError}
            />
          </div>

          {/* Password strength indicator */}
          <div className="pt-1">
            <PasswordStrength password={fields.new_password} />
          </div>

          {/* Actions */}
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
              {isPending ? "UPDATING..." : "UPDATE PASSWORD"}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}
