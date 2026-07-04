// src/pages/account/Login.jsx
import { Mail, Lock } from "lucide-react"
import { Link } from "react-router-dom"
import AuthLayout from "../../components/account/AuthLayout"
import FormInput from "../../components/common/FormInput"
import SocialLogin from "../../components/account/SocialLogin"
import { useLoginForm } from "../../hooks/account/useLoginForm"

export default function Login() {
  const {
    form,
    fieldErrors,
    formError,
    isPending,
    handleChange,
    handleSubmit,
  } = useLoginForm()

  return (
    <AuthLayout
      brandProps={{
        title: "WELCOME BACK",
        highlight: "RIDER!",
        description:
          "Login to your account and continue your journey with BikeExpress.",
      }}
    >
      <div>
        <h2 className="text-3xl font-black text-gray-900">Welcome Back</h2>

        <p className="mt-2 text-gray-500">Login to manage your account</p>

        {/* Form level error — wrong credentials */}
        {formError && (
          <div
            role="alert"
            className="mt-4 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-2"
          >
            {formError}
          </div>
        )}

        <form className="mt-8 space-y-5" onSubmit={handleSubmit}>

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

          <div className="flex items-center justify-between">
            <label className="flex items-center space-x-2 text-sm">
              <input type="checkbox" className="form-checkbox text-primary" />
              <span>Remember me</span>
            </label>

            <Link
              to="/forgot-password"
              className="text-sm text-primary font-semibold hover:underline"
            >
              Forgot Password?
            </Link>
          </div>

          <SocialLogin />

          <button
            type="submit"
            disabled={isPending}
            className="w-full bg-primary text-white py-3 rounded-lg font-bold disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isPending ? "LOGGING IN..." : "LOGIN"}
          </button>

        </form>

        <p className="mt-6 text-center text-sm text-gray-600">
          Don't have an account?{" "}
          <Link
            to="/register"
            className="text-primary font-bold ml-1 hover:underline"
          >
            Create Account
          </Link>
        </p>

      </div>
    </AuthLayout>
  )
}
// import { Mail, Lock } from "lucide-react";
// import SocialLogin from "../../components/account/SocialLogin";
// import FormInput from "../../components/common/FormInput";
// import AuthLayout from "../../components/account/AuthLayout";

// export default function Login() {
//   return (
//     <AuthLayout   brandProps={{
//         title: "WELCOME BACK",
//         highlight: "RIDER!",
//         description:
//           "Login to your account and continue your journey with BikeExpress."
//       }}>
//       <div>
//         <h2 className="text-3xl font-black text-gray-900">Welcome Back</h2>

//         <p className="mt-2 text-gray-500">Login to manage your account</p>

//         <form className="mt-8 space-y-5">
//           <FormInput icon={Mail} type="email" placeholder="Email address" />

//           <FormInput icon={Lock} type="password" placeholder="Password" />

//           <div className="flex items-center justify-between">
//   {/* Remember Me */}
//   <label className="flex items-center space-x-2 text-sm">
//     <input
//       type="checkbox"
//       className="form-checkbox text-primary"
//     />
//     <span>Remember me</span>
//   </label>

//   {/* Forgot Password */}
//   <button
//     type="button"
//     className="text-sm text-primary font-semibold"
//   >
//     Forgot Password?
//   </button>
// </div>


       
//           <SocialLogin />

//           <button className="w-full bg-primary text-white py-3 rounded-lg font-bold">
//             LOGIN
//           </button>
//         </form>

//         <p className="mt-6 text-center text-sm text-gray-600">
//           Don't have an account?
//           <span className="text-primary font-bold ml-1">Create Account</span>
//         </p>
//       </div>
//     </AuthLayout>
//   );
// }



