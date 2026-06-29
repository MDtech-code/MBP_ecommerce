import { User, Mail, Phone, Lock } from "lucide-react";
import AuthLayout from "../../components/account/AuthLayout";
import FormInput from "../../components/common/FormInput";

export default function Register() {
  return (
    <AuthLayout
      brandProps={{
        title: "JOIN THE",
        highlight: "BIKEXPRESS FAMILY!",
        description:
          "Create your account and get access to exclusive offers, fast checkout and more.",
      }}
    >
      <div>
        <h2 className="text-2xl lg:text-3xl font-black text-gray-900 tracking-tight">
          Create Account
        </h2>

        <p className="mt-1 text-sm text-gray-500">
          Join BikeExpress today
        </p>

        {/* DIET CHANGE 1: Reduced top margin from mt-8 (32px) to mt-5 (20px) */}
        {/* DIET CHANGE 2: Reduced input gaps from space-y-4 (16px) to space-y-3 (12px) */}
        <form className="mt-5 space-y-3">
          <FormInput icon={User} placeholder="Full name" />
          <FormInput icon={Mail} type="email" placeholder="Email address" />
          <FormInput icon={Phone} type="tel" placeholder="Phone number" />
          <FormInput icon={Lock} type="password" placeholder="Password" />
          <FormInput icon={Lock} type="password" placeholder="Confirm password" />

          {/* DIET CHANGE 3: Reduced button margin from mt-4 to mt-3, slightly leaner padding */}
          <button
            type="submit"
            className="w-full bg-primary hover:opacity-90 text-white py-3 rounded-xl font-bold tracking-wide shadow-lg shadow-primary/25 transition-all mt-3"
          >
            CREATE ACCOUNT
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-600">
          Already have an account?
          <span className="text-primary font-bold ml-1 cursor-pointer hover:underline">
            Login
          </span>
        </p>
      </div>
    </AuthLayout>
  );
}