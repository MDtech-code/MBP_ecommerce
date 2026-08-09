// src/pages/register/RegisterPage.jsx

import { Link } from "react-router-dom"
import { User, Mail, Lock } from "lucide-react"
import {AuthPageHeader} from "@widgets/auth"
import { FormInput,Toast } from "@shared/ui"
import { useRegisterForm } from "@features/auth"


export default function RegisterPage() {
  const {
    form,
    fieldErrors,
    formError,
    isPending,
    handleBlur,
    handleChange,
    handleSubmit,
  } = useRegisterForm()

  const formFields = [
    { name: "full_name",        placeholder: "Full name",         icon: User                  },
    { name: "email",            placeholder: "Email address",     icon: Mail, type: "email"   },
    { name: "password",         placeholder: "Password",          icon: Lock, type: "password"},
    { name: "confirm_password", placeholder: "Confirm password",  icon: Lock, type: "password"},
  ]
  

  return (
    <div>
      {/*  heading */}
      <AuthPageHeader title="Create Account"subtitle="Join BikeExpress today"/>

      {/* Toast for non-fields error  */}
      {formError && (
        <Toast type="error" >
          {formError}
        </Toast>
      )}

      

      {/* registration form  */}
      <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
        {formFields.map(({ name, placeholder, icon, type }) => (
          <FormInput
            key={name}
            icon={icon}
            type={type}
            name={name}
            placeholder={placeholder}
            value={form[name]}
            onChange={handleChange}
            onBlur={handleBlur}
            error={fieldErrors[name]?.message}
          />
        ))}

        <button
          type="submit"
          disabled={isPending}
          className="w-full bg-primary text-white py-3 rounded-lg font-bold
                     hover:opacity-90 transition-opacity
                     disabled:opacity-60 disabled:cursor-not-allowed
                     shadow-lg shadow-primary/25 touch-manipulation"
        >
          {isPending ? "CREATING ACCOUNT..." : "CREATE ACCOUNT"}
        </button>
      </form>

      <p className="mt-4 text-center text-sm text-muted">
        Already have an account?{" "}
        <Link
          to="/login"
          className="text-primary font-bold ml-1 hover:underline"
        >
          Login
        </Link>
      </p>
    </div>
  )
}
