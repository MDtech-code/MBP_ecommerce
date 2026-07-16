// src/hooks/account/useProfileForm.js
import { useState } from "react";
import { useUpdateProfile } from "../api/useProfileMutations";
import { useAuthStore } from "../../../entities/user/model/authStore";
import { normalizeError } from "../../../shared/api/transformers";

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
    phone: normalized?.errors?.fields?.phone?.message ?? null,
    date_of_birth: normalized?.errors?.fields?.date_of_birth?.message ?? null,
    gender: normalized?.errors?.fields?.gender?.message ?? null,
  };

  
  const formError = normalized?.errors?.non_fields?.message ?? null;

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
