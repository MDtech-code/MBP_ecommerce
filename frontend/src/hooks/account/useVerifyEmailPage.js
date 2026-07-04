// src/hooks/account/useVerifyEmailPage.js
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useVerifyEmail, useResendVerification } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

// MODULE-LEVEL CACHE: Survives React 18 Strict Mode double-mounting!
let activeToken = null;
let activePromise = null;
let cachedStatus = "idle"; // 'idle' | 'verifying' | 'success' | 'error'
let cachedError = null;

export function useVerifyEmailPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Check BOTH storages in case the user registered in a different tab or used localStorage
  const [email] = useState(
    () =>
      
      localStorage.getItem("pending_verification_email") ??
      "",
  );
  const tokenFromUrl = searchParams.get("token");

  const [autoStatus, setAutoStatus] = useState(() =>
    activeToken === tokenFromUrl ? cachedStatus : "idle",
  );
  const [autoError, setAutoError] = useState(() =>
    activeToken === tokenFromUrl ? cachedError : null,
  );

  const {
    mutateAsync: verifyEmailAsync,
    mutate: verifyEmail,
    isPending: isVerifyingMutation,
    isError: isVerifyError,
    isSuccess: isVerifySuccess,
    error: verifyError,
  } = useVerifyEmail();

  const {
    mutate: resendVerification,
    isPending: isResending,
    isError: isResendError,
    isSuccess: isResendSuccess,
    error: resendError,
  } = useResendVerification();

  

  // AUTO-VERIFY EFFECT
  useEffect(() => {
    if (!tokenFromUrl) return;

    // 1. If this exact token hasn't started verifying yet, start now!
    if (activeToken !== tokenFromUrl) {
      activeToken = tokenFromUrl;
      cachedStatus = "verifying";
      cachedError = null;

      // FIX FOR REACT WARNING: Defer the React state update asynchronously by 0ms.
      // This allows React to finish rendering without triggering a synchronous cascading render!
      setTimeout(() => {
        setAutoStatus("verifying");
      }, 0);

      if (verifyEmailAsync) {
        activePromise = verifyEmailAsync({ token: tokenFromUrl });
      } else {
        activePromise = new Promise((resolve, reject) => {
          verifyEmail(
            { token: tokenFromUrl },
            { onSuccess: resolve, onError: reject },
          );
        });
      }
    }

    // 2. Attach BOTH Mount 1 and Mount 2 to the exact same verification promise!
    if (activePromise) {
      activePromise
        .then(() => {
          cachedStatus = "success";
          setAutoStatus("success");

          // BULLETPROOF STORAGE CLEARING: Wipes from both session and local storage
          localStorage.removeItem("pending_verification_email");

          navigate("/login", {
            state: { message: "Email verified. You can now log in." },
          });
        })
        .catch((err) => {
          cachedStatus = "error";
          cachedError = err;
          setAutoStatus("error");
          setAutoError(err);
        });
    }
  }, [tokenFromUrl, verifyEmailAsync, verifyEmail, navigate]);

  // Manual resend handler
  const handleResend = () => {
    if (!email || isResending) return;
    resendVerification({ email });
  };

  const effectiveVerifyError = isVerifyError ? verifyError : autoError;
  const verifyNormalized = effectiveVerifyError
    ? normalizeError(effectiveVerifyError)
    : null;
  const resendNormalized = isResendError ? normalizeError(resendError) : null;

  const verifyErrorMsg =
    verifyNormalized?.errors?.non_field_errors?.[0] ??
    verifyNormalized?.message ??
    null;

  const resendErrorMsg =
    resendNormalized?.errors?.non_field_errors?.[0] ??
    resendNormalized?.message ??
    null;

  const resendSuccessMsg = isResendSuccess
    ? "Verification email sent. Please check your inbox."
    : null;

  const isVerifying = autoStatus === "verifying" || isVerifyingMutation;
  const isSuccess = autoStatus === "success" || isVerifySuccess;

  return {
    email,
    tokenFromUrl,
    isVerifying,
    isResending,
    isVerifySuccess: isSuccess,
    verifyErrorMsg,
    resendErrorMsg,
    resendSuccessMsg,
    handleResend,
  };
}
// // src/hooks/account/useVerifyEmailPage.js
// import { useState, useEffect } from "react";
// import { useNavigate, useSearchParams } from "react-router-dom";
// import { useVerifyEmail, useResendVerification } from "./useAuthMutations";
// import { normalizeError } from "../../api/transformers";

// export function useVerifyEmailPage() {
//   const navigate = useNavigate();
//   const [searchParams] = useSearchParams();

//   // Email stored during register — shown in UI and used for resend
//   const [email] = useState(
//     () => sessionStorage.getItem("pending_verification_email") ?? "",
//   );
//   const tokenFromUrl = searchParams.get("token");

//   // Verify mutation
//   const {
//     mutate: verifyEmail,
//     isPending: isVerifying,
//     isError: isVerifyError,
//     isSuccess: isVerifySuccess,
//     error: verifyError,
//   } = useVerifyEmail();

//   // Resend mutation
//   const {
//     mutate: resendVerification,
//     isPending: isResending,
//     isError: isResendError,
//     isSuccess: isResendSuccess,
//     error: resendError,
//   } = useResendVerification();

//   // Auto-verify if token comes in URL query param
//   // e.g. /verify-email?token=809e9c11-...
//   // Backend email link points here with token in URL
//   useEffect(() => {

//     if (tokenFromUrl) {
//       verifyEmail(
//         { token:tokenFromUrl },
//         {
//           onSuccess: () => {
//             sessionStorage.removeItem("pending_verification_email");
//             navigate("/login", {
//               state: { message: "Email verified. You can now log in." },
//             });
//           },
//         },
//       );
//     }
//   }, []); // runs once on mount

//   // Manual resend handler
//   const handleResend = () => {
//     if (!email || isResending) return;
//     resendVerification({ email });
//   };

//   // Error messages
//   const verifyNormalized = isVerifyError ? normalizeError(verifyError) : null;
//   const resendNormalized = isResendError ? normalizeError(resendError) : null;

//   const verifyErrorMsg =
//     verifyNormalized?.errors?.non_field_errors?.[0] ??
//     verifyNormalized?.message ??
//     null;

//   const resendErrorMsg =
//     resendNormalized?.errors?.non_field_errors?.[0] ??
//     resendNormalized?.message ??
//     null;

//   const resendSuccessMsg = isResendSuccess
//     ? "Verification email sent. Please check your inbox."
//     : null;

//   return {
//     email,
//     tokenFromUrl,
//     isVerifying, // auto-verifying from URL token
//     isResending, // resend button loading
//     isVerifySuccess,
//     verifyErrorMsg, // error from auto-verify
//     resendErrorMsg, // error from resend
//     resendSuccessMsg, // success feedback for resend
//     handleResend,
//   };
// }
