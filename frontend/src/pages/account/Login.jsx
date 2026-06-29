import { Mail, Lock } from "lucide-react";
import SocialLogin from "../../components/account/SocialLogin";
import FormInput from "../../components/common/FormInput";
import AuthLayout from "../../components/account/AuthLayout";

export default function Login() {
  return (
    <AuthLayout   brandProps={{
        title: "WELCOME BACK",
        highlight: "RIDER!",
        description:
          "Login to your account and continue your journey with BikeExpress."
      }}>
      <div>
        <h2 className="text-3xl font-black text-gray-900">Welcome Back</h2>

        <p className="mt-2 text-gray-500">Login to manage your account</p>

        <form className="mt-8 space-y-5">
          <FormInput icon={Mail} type="email" placeholder="Email address" />

          <FormInput icon={Lock} type="password" placeholder="Password" />

          <div className="flex items-center justify-between">
  {/* Remember Me */}
  <label className="flex items-center space-x-2 text-sm">
    <input
      type="checkbox"
      className="form-checkbox text-primary"
    />
    <span>Remember me</span>
  </label>

  {/* Forgot Password */}
  <button
    type="button"
    className="text-sm text-primary font-semibold"
  >
    Forgot Password?
  </button>
</div>


       
          <SocialLogin />

          <button className="w-full bg-primary text-white py-3 rounded-lg font-bold">
            LOGIN
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Don't have an account?
          <span className="text-primary font-bold ml-1">Create Account</span>
        </p>
      </div>
    </AuthLayout>
  );
}



          {/* <div className="flex items-center gap-3 border rounded-lg px-4 py-3">
            <Mail size={20} className="text-gray-400" />
            <input
              type="email"
              placeholder="Email address"
              className="w-full outline-none"
            />
          </div>

          <div className="flex items-center gap-3 border rounded-lg px-4 py-3">
            <Lock size={20} className="text-gray-400" />
            <input
              type="password"
              placeholder="Password"
              className="w-full outline-none"
            />
          </div> */}