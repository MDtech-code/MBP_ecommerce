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
    address_line1: user?.profile?.address_line1 || "",
    address_line2: user?.profile?.address_line2 || "",
    city: user?.profile?.city || "",
    province: user?.profile?.province || "",
    postal_code: user?.profile?.postal_code || "",
    country: user?.profile?.country || "Pakistan",
  });

  const normalized = isError ? normalizeError(error) : null;

  const fieldErrors = {
    phone: normalized?.errors?.phone?.[0] ?? null,
    date_of_birth: normalized?.errors?.date_of_birth?.[0] ?? null,
    gender: normalized?.errors?.gender?.[0] ?? null,
    address_line1: normalized?.errors?.address_line1?.[0] ?? null,
    address_line2: normalized?.errors?.address_line2?.[0] ?? null,
    city: normalized?.errors?.city?.[0] ?? null,
    province: normalized?.errors?.province?.[0] ?? null,
    postal_code: normalized?.errors?.postal_code?.[0] ?? null,
    country: normalized?.errors?.country?.[0] ?? null,
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
