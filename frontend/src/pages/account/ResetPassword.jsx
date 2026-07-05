// src/pages/account/ResetPassword.jsx

import { Link } from "react-router-dom";
import { Lock } from "lucide-react";
import AuthLayout from "../../components/account/AuthLayout";
import FormInput from "../../components/common/FormInput";
import { useResetPasswordForm } from "../../hooks/account/useResetPasswordForm";

const BRAND_PROPS = {
  title: "RESET YOUR",
  highlight: "PASSWORD!",
  description:
    "Create a strong new password to keep your BikeExpress account secure.",
};

export default function ResetPassword() {
  const {
    fields,
    handleChange,
    handleSubmit,
    isPending,
    passwordError,
    confirmPasswordError,
    formError,
    tokenMissing,
  } = useResetPasswordForm();

  // Token was not in the URL — link is invalid or already used
  if (tokenMissing) {
    return (
      <AuthLayout brandProps={BRAND_PROPS}>
        <div>
          <h2 className="mt-8 text-center text-2xl font-black">
            Reset Password
          </h2>

          <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
            <Lock size={45} className="text-gray-700" />
            <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
              ✕
            </span>
          </div>

          <div className="mt-6 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 text-center">
            This reset link is invalid or has expired. Please request a
            new one.
          </div>

          <div className="mt-6">
            <Link
              to="/forgot-password"
              className="block w-full bg-primary text-white py-3 rounded-lg font-bold text-center"
            >
              REQUEST NEW LINK
            </Link>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout brandProps={BRAND_PROPS}>
      <div>
        <h2 className="mt-8 text-center text-2xl font-black">
          Reset Password
        </h2>

        <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
          <Lock size={45} className="text-gray-700" />
          <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
            ↻
          </span>
        </div>

        <p className="mt-4 text-center text-sm text-gray-600">
          Create a new password for your account.
        </p>

        {formError && (
          <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 text-center">
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
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

          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-primary text-white py-3 rounded-lg font-bold disabled:opacity-60"
          >
            {isPending ? "RESETTING..." : "RESET PASSWORD"}
          </button>
        </form>
      </div>
    </AuthLayout>
  );
}
// import { Lock } from "lucide-react";

// import AuthLayout from "../../components/account/AuthLayout";
// import FormInput from "../../components/common/FormInput";

// export default function ResetPassword() {
//   return (
//     <AuthLayout>
//       <div>
//         <h2 className="mt-8 text-center text-2xl font-black">Reset Password</h2>
//         <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
//           <Lock size={45} className="text-gray-700" />
//           <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
//             ↻
//           </span>
//         </div>


//         <p className="mt-4 text-center text-sm text-gray-600">
//           Create a new password for
//           <br />
//           <span className="font-bold text-gray-900">rider@example.com</span>
//         </p>

//         <div className="mt-7 space-y-4">
//           <FormInput icon={Lock} type="password" placeholder="Enter new password" />

//           <FormInput icon={Lock} type="password" placeholder="Confirm new password" />

//           <button className="w-full bg-primary text-white py-3 rounded-lg font-bold">
//             RESET PASSWORD
//           </button>
//         </div>
//       </div>
//     </AuthLayout>
//   );
// }
