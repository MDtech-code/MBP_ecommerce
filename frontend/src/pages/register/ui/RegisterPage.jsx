import {  Link} from "react-router-dom"
import { User, Mail,  Lock } from "lucide-react";
import { FormInput } from "@shared/ui"
import { useRegisterForm } from "@features/auth"

export default function Register() {  
  const {form,fieldErrors,formError,isPending,handleChange,handleSubmit,} = useRegisterForm()
  const formFields = [
  { name: "full_name", placeholder: "Full name", icon: User },
  { name: "email", placeholder: "Email address", icon: Mail, type: "email" },
  { name: "password", placeholder: "Password", icon: Lock, type: "password" },
  { name: "confirm_password", placeholder: "Confirm password", icon: Lock, type: "password" },
];

  
  return (
    <>
      <div>
        <h2 className="hidden lg:block text-2xl lg:text-3xl font-black text-gray-900 dark:text-gray-100 tracking-tight">
          Create Account
        </h2>

        <p className="hidden lg:block mt-1 text-sm text-gray-500 dark:text-gray-300">
          Join BikeExpress today
        </p>

         {/* Form level error  */}
        {formError && (
          <div
            role="alert"
            className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2"
          >
            {formError}
            
          </div>
        )}
        <form className="mt-5 space-y-3"  onSubmit={handleSubmit}>
          {formFields.map(({ name, placeholder, icon, type }) => (
  <FormInput
    key={name}
    icon={icon}
    type={type}
    name={name}
    placeholder={placeholder}
    value={form[name]}
    onChange={handleChange}
    error={fieldErrors[name]?.message}
  />
))}

        {/* 
          <FormInput
            icon={User}
            name="full_name"
            placeholder="Full name"
            value={form.full_name}
            onChange={handleChange}
            error={fieldErrors.full_name?.message}
          />

          <FormInput
            icon={Mail}
            type="email"
            name="email"
            placeholder="Email address"
            value={form.email}
            onChange={handleChange}
            error={fieldErrors.email?.message}
          />

          <FormInput
            icon={Lock}
            type="password"
            name="password"
            placeholder="Password"
            value={form.password}
            onChange={handleChange}
            error={fieldErrors.password?.message}
          />

          <FormInput
            icon={Lock}
            type="password"
            name="confirm_password"
            placeholder="Confirm password"
            value={form.confirm_password}
            onChange={handleChange}
            error={fieldErrors.confirm_password?.message}
          />
          */}
          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-primary hover:opacity-90 text-white py-3 rounded-xl font-bold tracking-wide shadow-lg shadow-primary/25 transition-all mt-3 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isPending ? "CREATING ACCOUNT..." : "CREATE ACCOUNT"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
          Already have an account?{" "}
           <Link
            to="/login"
            className="text-primary font-bold ml-1 hover:underline"
          >
            Login
          </Link>
        </p>
      </div>
    </>
  );
}