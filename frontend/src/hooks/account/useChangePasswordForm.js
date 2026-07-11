// src/hooks/account/useChangePasswordForm.js

import { useState } from "react";
import { useChangePassword } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

/**
 * useChangePasswordForm
 *
 * Owns all state and logic for the ChangePassword page/section.
 * After success useChangePassword hook's onSuccess calls logout()
 * which clears the token, clears the store and redirects to /login
 * via the existing logout flow — no navigation needed here.
 *
 * Returns onSuccess callback prop so parent component can show
 * a success message before the logout redirect happens if needed.
 */
export function useChangePasswordForm() {
  const { mutate, isPending, isError, isSuccess, error } = useChangePassword();

  const [fields, setFields] = useState({
    current_password: "",
    new_password: "",
    confirm_new_password: "",
  });

  function handleChange(e) {
    const { name, value } = e.target;
    setFields((prev) => ({ ...prev, [name]: value }));
  }

  const normalized = isError ? normalizeError(error) : null;

  const currentPasswordError =
    normalized?.errors?.fields?.current_password?.message ?? null;

  const newPasswordError =
    normalized?.errors?.fields?.new_password?.message ?? null;
  const confirmNewPasswordError =
    normalized?.errors?.fields?.confirm_new_password?.message ?? null;

  // Non-field errors — e.g. "Current password is incorrect."
  const formError =
    normalized?.errors?.non_fields?.message ?? normalized?.message ?? null;

  function handleSubmit(e) {
    e.preventDefault();

    mutate({
      current_password: fields.current_password,
      new_password: fields.new_password,
      confirm_new_password: fields.confirm_new_password,
    });
  }

  return {
    fields,
    handleChange,
    handleSubmit,
    isPending,
    isError,
    isSuccess,
    currentPasswordError,
    newPasswordError,
    confirmNewPasswordError,
    formError,
  };
}
