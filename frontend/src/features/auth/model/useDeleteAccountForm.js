// src/features/auth/model/useDeleteAccountForm.js

import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useDeleteAccount } from "../api/useAuthMutations";
import { useAuthStore } from "@entities/user";
import { normalizeError } from "@shared/api";

/**
 * Delete account confirmation logic.
 *
 * UPDATED:
 *   - No password field — identity proven via OTP gate
 *   - Reads verification_token from router location.state
 *   - If no token → redirect to gate
 *   - On success → logout → navigate to home
 */
export function useDeleteAccountForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);

  const verificationToken = location.state?.verificationToken ?? null;

  const [showConfirm, setShowConfirm] = useState(false);

  const {
    mutate: deleteAccount,
    isPending,
    isError,
    error,
    reset,
  } = useDeleteAccount();

  const normalized = isError ? normalizeError(error) : null;
  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  const handleDeleteClick = () => {
    if (!verificationToken) {
      navigate("/security/verify?purpose=delete_account", { replace: true });
      return;
    }
    setShowConfirm(true);
  };

  const handleCancel = () => {
    setShowConfirm(false);
    reset();
  };

  const handleConfirmedDelete = (e) => {
    e.preventDefault();
    deleteAccount(
      { verification_token: verificationToken },
      {
        onSuccess: () => {
          logout();
          navigate("/", { replace: true });
        },
      },
    );
  };

  return {
    showConfirm,
    verificationToken,
    formError,
    formErrorCode,
    isPending,
    handleDeleteClick,
    handleCancel,
    handleConfirmedDelete,
  };
}
