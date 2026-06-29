import { Lock } from "lucide-react";

import AuthLayout from "../../components/account/AuthLayout";
import FormInput from "../../components/common/FormInput";

export default function ResetPassword() {
  return (
    <AuthLayout>
      <div>
        <h2 className="mt-8 text-center text-2xl font-black">Reset Password</h2>
        <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
          <Lock size={45} className="text-gray-700" />
          <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
            ↻
          </span>
        </div>


        <p className="mt-4 text-center text-sm text-gray-600">
          Create a new password for
          <br />
          <span className="font-bold text-gray-900">rider@example.com</span>
        </p>

        <div className="mt-7 space-y-4">
          <FormInput icon={Lock} type="password" placeholder="Enter new password" />

          <FormInput icon={Lock} type="password" placeholder="Confirm new password" />

          <button className="w-full bg-primary text-white py-3 rounded-lg font-bold">
            RESET PASSWORD
          </button>
        </div>
      </div>
    </AuthLayout>
  );
}
