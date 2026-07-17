
import {  Link } from "react-router-dom"
import { User, Mail,  Lock } from "lucide-react";
import { AuthLayout } from "@widgets/auth-layout"
import { FormInput } from "@shared/ui"
import { useRegisterForm } from "@features/auth"

export default function Register() {

  
  const {
    form,
    fieldErrors,
   
    formError,
    isPending,
    handleChange,
    handleSubmit,
  } = useRegisterForm()
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
         {/* Form level error banner */}
        {formError && (
          <div
            role="alert"
            className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2"
          >
            {formError}
            
          </div>
        )}
        <form className="mt-5 space-y-3"  onSubmit={handleSubmit}>
          {/* <FormInput icon={User} placeholder="Full name" />
          <FormInput icon={Mail} type="email" placeholder="Email address" />
          {/* <FormInput icon={Phone} type="tel" placeholder="Phone number" /> 
          <FormInput icon={Lock} type="password" placeholder="Password" />
          <FormInput icon={Lock} type="password" placeholder="Confirm password" /> */}
          <FormInput
            icon={User}
            name="full_name"
            placeholder="Full name"
            value={form.full_name}
            onChange={handleChange}
            error={fieldErrors.full_name}
          />

          <FormInput
            icon={Mail}
            type="email"
            name="email"
            placeholder="Email address"
            value={form.email}
            onChange={handleChange}
            error={fieldErrors.email}
          />

          <FormInput
            icon={Lock}
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            error={fieldErrors.password}
          />

          <FormInput
            icon={Lock}
            type="password"
            name="confirm_password"
            placeholder="Confirm password"
            value={form.confirm_password}
            onChange={handleChange}
            error={fieldErrors.confirm_password}
          />

          {/* DIET CHANGE 3: Reduced button margin from mt-4 to mt-3, slightly leaner padding */}
          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-primary hover:opacity-90 text-white py-3 rounded-xl font-bold tracking-wide shadow-lg shadow-primary/25 transition-all mt-3 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isPending ? "CREATING ACCOUNT..." : "CREATE ACCOUNT"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-600">
          Already have an account?{" "}
           <Link
            to="/login"
            className="text-primary font-bold ml-1 hover:underline"
          >
            Login
          </Link>
          {/* <span className="text-primary font-bold ml-1 cursor-pointer hover:underline">
            Login
          </span> */}

        </p>
      </div>
    </AuthLayout>
  );
}