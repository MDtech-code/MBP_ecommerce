// src/hooks/account/useVerifyEmailPage.js
import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useVerifyEmail, useResendVerification } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

export function useVerifyEmailPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  // Email stored during register — shown in UI and used for resend
  const [email] = useState(
    () => sessionStorage.getItem("pending_verification_email") ?? "",
  );
  const tokenFromUrl = searchParams.get("token");
 
  // Verify mutation
  const {
    mutate: verifyEmail,
    isPending: isVerifying,
    isError: isVerifyError,
    isSuccess: isVerifySuccess,
    error: verifyError,
  } = useVerifyEmail();

  // Resend mutation
  const {
    mutate: resendVerification,
    isPending: isResending,
    isError: isResendError,
    isSuccess: isResendSuccess,
    error: resendError,
  } = useResendVerification();

  // Auto-verify if token comes in URL query param
  // e.g. /verify-email?token=809e9c11-...
  // Backend email link points here with token in URL
  useEffect(() => {
    
    
    if (tokenFromUrl) {
      verifyEmail(
        { token:tokenFromUrl },
        {
          onSuccess: () => {
            sessionStorage.removeItem("pending_verification_email");
            navigate("/login", {
              state: { message: "Email verified. You can now log in." },
            });
          },
        },
      );
    }
  }, []); // runs once on mount

  // Manual resend handler
  const handleResend = () => {
    if (!email || isResending) return;
    resendVerification({ email });
  };

  // Error messages
  const verifyNormalized = isVerifyError ? normalizeError(verifyError) : null;
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

  return {
    email,
    tokenFromUrl, 
    isVerifying, // auto-verifying from URL token
    isResending, // resend button loading
    isVerifySuccess,
    verifyErrorMsg, // error from auto-verify
    resendErrorMsg, // error from resend
    resendSuccessMsg, // success feedback for resend
    handleResend,
  };
}
