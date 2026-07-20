// src/features/auth/model/useChangePasswordForm.js

import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useChangePassword } from "../api/useAuthMutations";
import { useAuthStore } from "@entities/user";
import { normalizeError } from "@shared/api";

/**
 * Change password form logic.
 *
 * UPDATED:
 *   - No current_password field — identity proven via OTP gate
 *   - Reads verification_token from router location.state
 *   - If no token in state → redirect to gate
 *   - On success → logout → navigate to login
 *
 * Flow:
 *   Gate page → OTP page → this page (with token in state)
 *   User enters new password → submit → success → logout
 */
export function useChangePasswordForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);

  const verificationToken = location.state?.verificationToken ?? null;

  const [fields, setFields] = useState({
    new_password: "",
    confirm_new_password: "",
  });

  const {
    mutate: changePassword,
    isPending,
    isError,
    error,
    reset,
  } = useChangePassword();

  const normalized = isError ? normalizeError(error) : null;

  const newPasswordError =
    normalized?.errors?.fields?.new_password?.message ?? null;
  const confirmNewPasswordError =
    normalized?.errors?.fields?.confirm_new_password?.message ?? null;
  const formError = normalized?.errors?.non_fields?.message ?? null;

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFields((prev) => ({ ...prev, [name]: value }));
    if (isError) reset();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!verificationToken) {
      navigate("/security/verify?purpose=change_password", { replace: true });
      return;
    }

    changePassword(
      {
        new_password: fields.new_password,
        confirm_new_password: fields.confirm_new_password,
        verification_token: verificationToken,
      },
      {
        onSuccess: () => {
          logout();
          navigate("/login", {
            replace: true,
            state: {
              message:
                "Password changed successfully. Please log in with your new password.",
            },
          });
        },
      },
    );
  };

  return {
    fields,
    verificationToken,
    handleChange,
    handleSubmit,
    isPending,
    isError,
    newPasswordError,
    confirmNewPasswordError,
    formError,
  };
}
