// src/hooks/account/useForgotPasswordForm.js

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRequestPasswordReset } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

/**
 * useForgotPasswordForm
 *
 * Owns all state and logic for the ForgotPassword page.
 * After a successful submission navigates to /forgot-password/sent
 * so user sees a confirmation screen without a separate route entry —
 * we pass the submitted email via location.state so the confirmation
 * message can display it.
 *
 * Backend always returns the same success message regardless of whether
 * the email is registered — this is intentional security behavior to
 * prevent email enumeration. We never tell the user the email was not found.
 */
export function useForgotPasswordForm() {
  const navigate = useNavigate();
  const { mutate, isPending, isError, isSuccess, error } =
    useRequestPasswordReset();

  const [email, setEmail] = useState("");

  const emailError = isError
    ? (normalizeError(error).errors?.email?.[0] ?? null)
    : null;

  // Non-field errors from backend (rate limit message, etc.)
  const formError = isError
    ? (normalizeError(error).errors?.non_field_errors?.[0] ??
      normalizeError(error).message ??
      null)
    : null;

  function handleEmailChange(e) {
    setEmail(e.target.value);
  }

  function handleSubmit(e) {
    e.preventDefault();

    mutate(
      { email },
      {
        onSuccess: () => {
          // Pass email in state so sent-confirmation screen can display it
          navigate("/forgot-password/sent", {
            state: { email },
            replace: true,
          });
        },
      },
    );
  }

  return {
    email,
    handleEmailChange,
    handleSubmit,
    isPending,
    isError,
    isSuccess,
    emailError,
    formError,
  };
}
