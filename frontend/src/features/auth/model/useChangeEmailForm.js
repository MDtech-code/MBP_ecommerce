// src/features/auth/model/useChangeEmailForm.js

import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useRequestEmailChange } from "../api/useAuthMutations";
import { normalizeError } from "@shared/api";

/**
 * Change email form logic (Phase 2 — actual new email input).
 *
 * UPDATED:
 *   - No password field — identity proven via OTP gate
 *   - Reads verification_token from router location.state
 *   - If no token in state → redirect to gate
 *   - On success → show "check new inbox" screen
 *   - User stays logged in until new email OTP confirmed
 *
 * Flow:
 *   Gate → OTP → this page → success screen → new email OTP page
 */
export function useChangeEmailForm() {
  const navigate = useNavigate();
  const location = useLocation();

  const verificationToken = location.state?.verificationToken ?? null;

  const [newEmail, setNewEmail] = useState("");

  const {
    mutate: requestChange,
    isPending,
    isError,
    error,
    isSuccess,
    data: successData,
    reset,
  } = useRequestEmailChange();

  const normalized = isError ? normalizeError(error) : null;

  const fieldErrors = {
    new_email: normalized?.errors?.fields?.new_email?.message ?? null,
  };

  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  // Masked new email returned by backend for display
  const maskedNewEmail = successData?.data?.masked_new_email ?? null;

  const handleChange = (e) => {
    setNewEmail(e.target.value);
    if (isError) reset();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!verificationToken) {
      navigate("/security/verify?purpose=change_email", { replace: true });
      return;
    }

    requestChange({
      new_email: newEmail,
      verification_token: verificationToken,
    });
  };

  // After success — navigate to new email OTP entry
  const handleGoToNewEmailOTP = () => {
    navigate("/security/verify-new-email-otp", {
      state: {
        maskedNewEmail,
        purpose: "verify_new_email",
      },
    });
  };

  return {
    newEmail,
    verificationToken,
    fieldErrors,
    formError,
    formErrorCode,
    isPending,
    isSuccess,
    maskedNewEmail,
    handleChange,
    handleSubmit,
    handleGoToNewEmailOTP,
  };
}
