// // src/pages/security/ui/ChangeEmailPage.jsx

// import { Mail, Lock, ArrowLeft, CheckCircle } from "lucide-react";
// import { Link }      from "react-router-dom";
// import { FormInput } from "@shared/ui";
// import { useChangeEmailForm } from "@features/auth";

// export default function ChangeEmailPage() {
//   const {
//     form,
//     fieldErrors,
//     formError,
//     isPending,
//     isSuccess,
//     handleChange,
//     handleSubmit,
//   } = useChangeEmailForm();

//   // ── Success state — email sent, user still logged in ──────────────────────
//   if (isSuccess) {
//     const pendingEmail = sessionStorage.getItem("pending_new_email") ?? form.new_email;

//     return (
//       <div className="w-full">
//         <Link
//           to="/security"
//           className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-primary transition-colors mb-8"
//         >
//           <ArrowLeft size={18} />
//           Back to Security
//         </Link>

//         <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-10">
//           <div className="max-w-md mx-auto text-center">

//             <CheckCircle size={56} className="text-green-500 mx-auto mb-4" />

//             <h2 className="text-2xl font-black text-gray-900 mb-2">
//               Verification Email Sent
//             </h2>

//             <p className="text-sm text-gray-500 mb-1">
//               We sent a verification link to:
//             </p>

//             <p className="text-base font-bold text-gray-800 mb-6">
//               {pendingEmail}
//             </p>

//             <div className="bg-blue-50 border border-blue-100 rounded-xl px-5 py-4 text-sm text-blue-700 text-left space-y-2 mb-8">
//               <p className="font-semibold">What happens next:</p>
//               <ul className="space-y-1 list-disc list-inside text-blue-600">
//                 <li>Click the link in the email to confirm your new address</li>
//                 <li>You will be logged out automatically after confirming</li>
//                 <li>Log back in with your new email address</li>
//                 <li>The link expires in 24 hours</li>
//                 <li>Your current email remains active until you confirm</li>
//               </ul>
//             </div>

//             <Link
//               to="/security"
//               className="inline-flex items-center gap-2 text-sm font-semibold text-primary hover:underline"
//             >
//               <ArrowLeft size={16} />
//               Back to Security Settings
//             </Link>

//           </div>
//         </div>
//       </div>
//     );
//   }

//   // ── Form state ─────────────────────────────────────────────────────────────
//   return (
//     <div className="w-full">
//       <Link
//         to="/security"
//         className="inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-primary transition-colors mb-8"
//       >
//         <ArrowLeft size={18} />
//         Back to Security
//       </Link>

//       <div className="bg-white rounded-3xl border border-gray-200 shadow-sm p-8 lg:p-10">

//         <div className="max-w-xl">
//           <h1 className="text-3xl font-black text-gray-900">
//             Change Email Address
//           </h1>
//           <p className="mt-2 text-gray-500">
//             Enter your new email and confirm your current password.
//             We will send a verification link — your current session
//             stays active until you click the link.
//           </p>
//         </div>

//         {formError && (
//           <div
//             role="alert"
//             className="mt-6 max-w-xl rounded-xl bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-600"
//           >
//             {formError}
//           </div>
//         )}

//         <form onSubmit={handleSubmit} className="mt-8 space-y-5 max-w-xl">

//           <div>
//             <label className="block mb-2 text-sm font-semibold text-gray-800">
//               New Email Address
//             </label>
//             <FormInput
//               icon={Mail}
//               type="email"
//               name="new_email"
//               placeholder="Enter your new email address"
//               value={form.new_email}
//               onChange={handleChange}
//               error={fieldErrors.new_email}
//             />
//           </div>

//           <div>
//             <label className="block mb-2 text-sm font-semibold text-gray-800">
//               Current Password
//             </label>
//             <FormInput
//               icon={Lock}
//               type="password"
//               name="password"
//               placeholder="Enter your current password to confirm"
//               value={form.password}
//               onChange={handleChange}
//               error={fieldErrors.password}
//             />
//           </div>

//           <div className="flex items-center gap-4 pt-2">
//             <Link
//               to="/security"
//               className="rounded-xl border border-gray-300 px-6 py-3 font-semibold text-gray-700 hover:bg-gray-50 transition text-sm"
//             >
//               Cancel
//             </Link>
//             <button
//               type="submit"
//               disabled={isPending}
//               className="rounded-xl bg-primary px-8 py-3 font-bold text-white hover:opacity-90 transition disabled:opacity-60 disabled:cursor-not-allowed text-sm"
//             >
//               {isPending ? "SENDING..." : "SEND VERIFICATION EMAIL"}
//             </button>
//           </div>

//         </form>
//       </div>
//     </div>
//   );
// }