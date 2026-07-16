// src/pages/account/security/ChangePassword.jsx

import { ArrowLeft } from "lucide-react";
import { useNavigate } from "react-router-dom";

import DashboardLayout from "../../../components/account/DashboardLayout";
import PasswordStrength from "../../../components/account/security/PasswordStrength";
import { useChangePasswordForm } from "../../../hooks/account/useChangePasswordForm";

export default function ChangePassword() {
  const navigate = useNavigate();

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
    <DashboardLayout>
      <div className="max-w-4xl">

        {/* Back Button */}

        <button
          onClick={() => navigate("/security")}
          className="
            mb-8
            flex
            items-center
            gap-2
            text-sm
            font-semibold
            text-gray-500
            hover:text-primary
            transition-colors
          "
        >
          <ArrowLeft size={18} />
          Back to Security
        </button>

        {/* Main Card */}

        <div
          className="
            bg-white
            rounded-3xl
            border
            border-gray-200
            shadow-sm
            p-8
            lg:p-10
          "
        >

          {/* Heading */}

          <h1 className="text-3xl font-black text-gray-900">
            Change Password
          </h1>

          <p className="mt-2 text-gray-500">
            Keep your BikeExpress account secure by updating your
            password regularly.
          </p>

          {/* Form-level error banner */}

          {formError && (
            <div className="mt-6 rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600">
              {formError}
            </div>
          )}

          {/* Form */}

          <form onSubmit={handleSubmit} className="mt-10 space-y-6">

            <div>
              <label className="block mb-2 font-semibold text-gray-800">
                Current Password
              </label>

              <input
                type="password"
                name="current_password"
                placeholder="Enter current password"
                value={fields.current_password}
                onChange={handleChange}
                className={`
                  w-full
                  rounded-xl
                  border
                  px-5
                  py-3.5
                  outline-none
                  focus:border-primary
                  ${currentPasswordError
                    ? "border-red-400"
                    : "border-gray-300"}
                `}
              />

              {currentPasswordError && (
                <p className="mt-1 text-xs text-red-500">
                  {currentPasswordError}
                </p>
              )}
            </div>

            <div>
              <label className="block mb-2 font-semibold text-gray-800">
                New Password
              </label>

              <input
                type="password"
                name="new_password"
                placeholder="Enter new password"
                value={fields.new_password}
                onChange={handleChange}
                className={`
                  w-full
                  rounded-xl
                  border
                  px-5
                  py-3.5
                  outline-none
                  focus:border-primary
                  ${newPasswordError
                    ? "border-red-400"
                    : "border-gray-300"}
                `}
              />

              {newPasswordError && (
                <p className="mt-1 text-xs text-red-500">
                  {newPasswordError}
                </p>
              )}
            </div>

            <div>
              <label className="block mb-2 font-semibold text-gray-800">
                Confirm Password
              </label>

              <input
                type="password"
                name="confirm_new_password"
                placeholder="Confirm new password"
                value={fields.confirm_new_password}
                onChange={handleChange}
                className={`
                  w-full
                  rounded-xl
                  border
                  px-5
                  py-3.5
                  outline-none
                  focus:border-primary
                  ${confirmNewPasswordError
                    ? "border-red-400"
                    : "border-gray-300"}
                `}
              />

              {confirmNewPasswordError && (
                <p className="mt-1 text-xs text-red-500">
                  {confirmNewPasswordError}
                </p>
              )}
            </div>

            {/* Password Strength — reacts to new_password field live */}

            <div className="my-10">
              <PasswordStrength password={fields.new_password} />
            </div>

            {/* Actions */}

            <div className="flex justify-end gap-4">

              <button
                type="button"
                onClick={() => navigate("/security")}
                className="
                  rounded-xl
                  border
                  border-gray-300
                  px-6
                  py-3
                  font-semibold
                  hover:bg-gray-50
                  transition
                "
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={isPending}
                className="
                  rounded-xl
                  bg-primary
                  px-6
                  py-3
                  font-semibold
                  text-white
                  hover:opacity-90
                  transition
                  disabled:opacity-60
                "
              >
                {isPending ? "Updating..." : "Update Password"}
              </button>

            </div>

          </form>

        </div>

      </div>
    </DashboardLayout>
  );
}
