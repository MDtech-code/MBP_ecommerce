import { MailCheck } from "lucide-react";

import AuthLayout from "../../components/account/AuthLayout";

export default function VerifyEmail() {
  return (
    <AuthLayout>
      <div className="text-center">
        <h2 className="mt-8 text-2xl font-black text-black-400">
          Verify Your Email
        </h2>
        <div className="mx-auto w-24 h-24 rounded-full bg-gray-100 flex items-center justify-center relative">
          <MailCheck size={45} className="text-gray-700" />
          <span className="absolute bottom-0 right-0 w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center font-bold">
            ✓
          </span>
        </div>

        

        <p className="mt-5 text-gray-600 text-sm">
          We have sent a verification link to
          <br />
          <span className="font-bold text-gray-900">rider@example.com</span>
        </p>

        <p className="mt-5 text-sm text-gray-500">
          Please check your inbox and click on the verification link to activate
          your account.
        </p>

        <button className="mt-8 w-full border border-primary text-primary py-3 rounded-lg font-bold">
          RESEND EMAIL
        </button>

        <p className="mt-8 text-primary font-semibold text-sm">Back to Login</p>
      </div>
    </AuthLayout>
  );
}

// import {
//   MailCheck
// } from "lucide-react";


// import AuthLayout from "../../components/account/AuthLayout";


// export default function VerifyEmail(){


// return (

// <AuthLayout>


// <div className="text-center">


// <div
// className="
// mx-auto
// w-16
// h-16
// rounded-full
// bg-primary/10
// flex
// items-center
// justify-center
// "
// >

// <MailCheck
// size={32}
// className="text-primary"
// />


// </div>




// <h2
// className="
// mt-6
// text-3xl
// font-black
// text-gray-900
// "
// >

// Verify Your Email

// </h2>



// <p
// className="
// mt-3
// text-gray-500
// "
// >

// We have sent a verification link
// to your email address.

// </p>




// <button

// className="
// mt-8
// w-full
// bg-primary
// text-white
// py-3
// rounded-lg
// font-bold
// "

// >

// RESEND EMAIL

// </button>




// <p
// className="
// mt-5
// text-sm
// text-gray-600
// "
// >

// Already verified?

// <span
// className="
// text-primary
// font-bold
// ml-1
// "
// >

// Login

// </span>

// </p>



// </div>


// </AuthLayout>

// )

// }