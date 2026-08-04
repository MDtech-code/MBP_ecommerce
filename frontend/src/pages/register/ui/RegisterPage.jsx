// src/pages/register/RegisterPage.jsx

import { Link } from "react-router-dom"
import { User, Mail, Lock } from "lucide-react"

import { FormInput } from "@shared/ui"
import { AlertBanner } from "@shared/ui"
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
      {/* Desktop heading — hidden on mobile/tablet, AuthBrand handles those */}
      {/* ── OLD ──────────────────────────────────────────────────────
      <h2 className="hidden lg:block text-2xl lg:text-3xl font-black
                     text-gray-900 dark:text-gray-100 tracking-tight">
        Create Account
      </h2>
      <p className="hidden lg:block mt-1 text-sm text-gray-500 dark:text-gray-300">
        Join BikeExpress today
      </p>
      ──────────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          Wrapped in a single div like Login — cleaner DOM grouping.
          text-2xl lg:text-3xl → text-3xl unified, same as Login h2.
          tracking-tight removed — Login h2 has none, now consistent.
      ─────────────────────────────────────────────────────────────── */}
      <div className="hidden lg:block">
        <h2 className="text-3xl font-black text-gray-900 dark:text-gray-100">
          Create Account
        </h2>
        <p className="mt-2 text-gray-500 dark:text-gray-300">
          Join BikeExpress today
        </p>
      </div>

      {/* ── OLD ──────────────────────────────────────────────────────
          Hand-rolled error banner, missing dark mode variants.

          {formError && (
            <div role="alert" className="mt-3 text-sm text-red-600
              bg-red-50 border border-red-200 rounded-lg px-4 py-2">
              {formError}
            </div>
          )}
          ──────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          AlertBanner adds missing dark mode variants automatically.
          mt-4 consistent with Login.
      ─────────────────────────────────────────────────────────────── */}
      {formError && (
        <AlertBanner type="error" className="mt-4">
          {formError}
        </AlertBanner>
      )}

      {/* ── OLD ──────────────────────────────────────────────────────
      <form className="mt-5 space-y-3" onSubmit={handleSubmit}>
      ──────────────────────────────────────────────────────────────── */}

      {/* ── NEW ──────────────────────────────────────────────────────
          mt-6 and space-y-4 unified with Login.
      ─────────────────────────────────────────────────────────────── */}
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

        {/* ── OLD ──────────────────────────────────────────────────
            Entire commented explicit FormInput block removed —
            was the pre-map implementation, fully replaced, pure noise.

            mt-3 removed from button — space-y-4 on form already
            applies margin-top to every child including the button.
            Adding mt-3 on top of space-y-4 created double spacing
            above the button only, breaking rhythm.

            rounded-xl → rounded-lg unified with Login.
            hover:opacity-90 transition-all → transition-opacity,
            matches the specific property being transitioned.
            tracking-wide removed — Login button has none.

        <button ... className="... mt-3 rounded-xl hover:opacity-90
                               transition-all tracking-wide ...">
        ─────────────────────────────────────────────────────────── */}

        {/* ── NEW ─────────────────────────────────────────────────── */}
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
  )
}
// import {  Link} from "react-router-dom"
// import { User, Mail,  Lock } from "lucide-react";
// import { FormInput } from "@shared/ui"
// import { useRegisterForm } from "@features/auth"

// export default function RegisterPage() {  

//   const {form,fieldErrors,formError,isPending,handleBlur,handleChange,handleSubmit,} = useRegisterForm()

//   const formFields = [
//   { name: "full_name", placeholder: "Full name", icon: User },
//   { name: "email", placeholder: "Email address", icon: Mail, type: "email" },
//   { name: "password", placeholder: "Password", icon: Lock, type: "password" },
//   { name: "confirm_password", placeholder: "Confirm password", icon: Lock, type: "password" },
// ];

  
//   return (
//     <>
//       <div>
//         <h2 className="hidden lg:block text-2xl lg:text-3xl font-black text-gray-900 dark:text-gray-100 tracking-tight">
//           Create Account
//         </h2>

//         <p className="hidden lg:block mt-1 text-sm text-gray-500 dark:text-gray-300">
//           Join BikeExpress today
//         </p>

//          {/* Form level error  */}
//         {formError && (
//           <div
//             role="alert"
//             className="mt-3 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2"
//           >
//             {formError}
            
//           </div>
//         )}
//         <form className="mt-5 space-y-3"  onSubmit={handleSubmit}>
//           {formFields.map(({ name, placeholder, icon, type }) => (
//   <FormInput
//     key={name}
//     icon={icon}
//     type={type}
//     name={name}
//     placeholder={placeholder}
//     value={form[name]}
//     onChange={handleChange}
//     onBlur={handleBlur}
//     error={fieldErrors[name]?.message}
//   />
// ))}

        
//           <button
//             type="submit"
//             disabled={isPending}
//             className="w-full bg-primary hover:opacity-90 text-white py-3 rounded-xl font-bold tracking-wide shadow-lg shadow-primary/25 transition-all mt-3 disabled:opacity-60 disabled:cursor-not-allowed"
//           >
//             {isPending ? "CREATING ACCOUNT..." : "CREATE ACCOUNT"}
//           </button>
//         </form>

//         <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
//           Already have an account?{" "}
//            <Link
//             to="/login"
//             className="text-primary font-bold ml-1 hover:underline"
//           >
//             Login
//           </Link>
//         </p>
//       </div>
//     </>
//   );
// }