import { Lock, Mail } from "lucide-react";

import AuthLayout from "../../components/account/AuthLayout";
import FormInput from "../../components/common/FormInput";

export default function ForgotPassword() {
  return (
    <AuthLayout>
      <div>
        <h2 className="mt-8 text-2xl text-center font-black">Forgot Password?</h2>
        <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
          <Lock size={45} className="text-gray-700" />
          <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
            ?
          </span>
        </div>

        

        <p className="mt-4 text-center text-sm text-gray-600">
          Enter your email address and we will send you a link to reset your password.
        </p>

        <div className="mt-7">
          <FormInput icon={Mail} placeholder="Enter your email" />

          <button className="mt-5 w-full bg-primary text-white py-3 rounded-lg font-bold">
            SEND RESET LINK
          </button>
        </div>

        <p className="mt-8 text-center text-primary text-sm font-semibold">
          Back to Login
        </p>
      </div>
    </AuthLayout>
  );
}
