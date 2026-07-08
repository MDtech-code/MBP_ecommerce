// src/hooks/account/useProfileForm.js
import { useState } from "react";
import { useUpdateProfile } from "./useAuthMutations";
import { useAuthStore } from "../../stores/authStore";
import { normalizeError } from "../../api/transformers";

export function useProfileForm(onSaveSuccess) {
  const user = useAuthStore((state) => state.user);
  const {
    mutate: updateProfile,
    isPending,
    isError,
    error,
  } = useUpdateProfile();

  const [form, setForm] = useState({
    phone: user?.profile?.phone || "",
    date_of_birth: user?.profile?.date_of_birth || "",
    gender: user?.profile?.gender || "",
  });

  const normalized = isError ? normalizeError(error) : null;

  const fieldErrors = {
    phone: normalized?.errors?.phone?.[0] ?? null,
    date_of_birth: normalized?.errors?.date_of_birth?.[0] ?? null,
    gender: normalized?.errors?.gender?.[0] ?? null,
  };

  const formError = normalized?.errors?.non_field_errors?.[0] ?? null;

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    updateProfile(form, {
      onSuccess: () => onSaveSuccess?.(),
    });
  };

  return {
    form,
    fieldErrors,
    formError,
    isPending,
    handleChange,
    handleSubmit,
  };
}
