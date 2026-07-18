// src/hooks/account/useVerifyEmailPage.js
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useVerifyEmail, useResendVerification } from "../api/useAuthMutations";
import { normalizeError } from "@shared/api"

// MODULE-LEVEL CACHE: Survives React 18 Strict Mode double-mounting!
let activeToken = null;
let activePromise = null;
let cachedStatus = "idle"; // 'idle' | 'verifying' | 'success' | 'error'
let cachedError = null;

export function useVerifyEmailPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Check localstorgae
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
    console.log(tokenFromUrl)
    if (!tokenFromUrl) return;

    // 1. If this exact token hasn't started verifying yet, start now!
    if (activeToken !== tokenFromUrl) {
      activeToken = tokenFromUrl;
      cachedStatus = "verifying";
      cachedError = null;

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
    resendVerification({ email});
  };

  const effectiveVerifyError = isVerifyError ? verifyError : autoError;
  const verifyNormalized = effectiveVerifyError
    ? normalizeError(effectiveVerifyError)
    : null;
  const resendNormalized = isResendError ? normalizeError(resendError) : null;

  const verifyErrorMsg =
    verifyNormalized?.errors?.non_field_errors?.message ??
    verifyNormalized?.message ??
    null;

  const resendErrorMsg =
    resendNormalized?.errors?.non_field_errors?.message ??
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
