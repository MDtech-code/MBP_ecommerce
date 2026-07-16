// src/pages/account/ForgotPassword.jsx

import { Link } from "react-router-dom";
import { Lock, Mail } from "lucide-react";
import AuthLayout from "../../components/account/AuthLayout";
import FormInput from "../../components/common/FormInput";
import { useForgotPasswordForm } from "../../hooks/account/useForgotPasswordForm";

const BRAND_PROPS = {
  title: "FORGOT YOUR",
  highlight: "PASSWORD?",
  description:
    "No worries. Enter your email and we will send you a reset link to get back on the road.",
};

export default function ForgotPassword() {
  const {
    email,
    handleEmailChange,
    handleSubmit,
    isPending,
    emailError,
    formError,
  } = useForgotPasswordForm();

  return (
    <AuthLayout brandProps={BRAND_PROPS}>
      <div>
        <h2 className="mt-8 text-2xl text-center font-black">
          Forgot Password?
        </h2>

        <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
          <Lock size={45} className="text-gray-700" />
          <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
            ?
          </span>
        </div>

        <p className="mt-4 text-center text-sm text-gray-600">
          Enter your email address and we will send you a link to reset
          your password.
        </p>

        {formError && (
          <div className="mt-4 rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600 text-center">
            {formError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-7">
          <FormInput
            icon={Mail}
            type="email"
            name="email"
            placeholder="Enter your email"
            value={email}
            onChange={handleEmailChange}
            error={emailError}
          />

          <button
            type="submit"
            disabled={isPending}
            className="mt-5 w-full bg-primary text-white py-3 rounded-lg font-bold disabled:opacity-60"
          >
            {isPending ? "SENDING..." : "SEND RESET LINK"}
          </button>
        </form>

        <p className="mt-8 text-center text-sm font-semibold">
          <Link to="/login" className="text-primary">
            Back to Login
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
