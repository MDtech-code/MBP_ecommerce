// src/hooks/account/useResetPasswordForm.js

import { useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useConfirmPasswordReset } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

/**
 * useResetPasswordForm
 *
 * Owns all state and logic for the ResetPassword page.
 * Reads the reset token from the URL query parameter:
 *   /reset-password?token=uuid-from-email
 *
 * On success navigates to /login with a success message in location.state
 * so the login page can display a "password reset successfully" banner.
 *
 * If the token is missing from the URL the form renders an error state
 * immediately without attempting any API call.
 */
export function useResetPasswordForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const { mutate, isPending, isError, error } = useConfirmPasswordReset();

  const [fields, setFields] = useState({
    password: "",
    confirm_password: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setFields((prev) => ({ ...prev, [name]: value }));
  }

  const normalized = isError ? normalizeError(error) : null;

 const passwordError = normalized?.errors?.fields?.password?.message ?? null;

 
const confirmPasswordError =
  normalized?.errors?.fields?.confirm_password?.message ?? null;
  // Token errors come as non_field_errors from backend
  // e.g. "Invalid or expired token."
 
const formError =
  normalized?.errors?.non_fields?.message ?? normalized?.message ?? null;

  // Token missing from URL — do not even attempt submission
  const tokenMissing = !token;

  function handleSubmit(e) {
    e.preventDefault();

    if (tokenMissing) return;

    mutate(
      {
        token,
        password: fields.password,
        confirm_password: fields.confirm_password,
      },
      {
        onSuccess: () => {
          navigate("/login", {
            state: {
              successMessage:
                "Password reset successfully. You can now log in.",
            },
            replace: true,
          });
        },
      },
    );
  }

  return {
    fields,
    handleChange,
    handleSubmit,
    isPending,
    isError,
    passwordError,
    confirmPasswordError,
    formError,
    tokenMissing,
  };
}
