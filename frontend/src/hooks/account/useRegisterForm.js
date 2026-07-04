// src/hooks/account/useRegisterForm.js

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRegister } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

export function useRegisterForm() {
  const navigate = useNavigate();
  const { mutate: register, isPending, isError, error } = useRegister();

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  });

  const normalized = isError ? normalizeError(error) : null;

  const fieldErrors = {
    full_name: normalized?.errors?.full_name?.[0] ?? null,
    email: normalized?.errors?.email?.[0] ?? null,
    password: normalized?.errors?.password?.[0] ?? null,
    confirm_password: normalized?.errors?.confirm_password?.[0] ?? null,
  };

  const formError = normalized?.errors?.non_field_errors?.[0] ?? null;

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    register(form, {
      onSuccess: () => {
        // Store email for VerifyEmail page to display + use for resend
        localStorage.setItem("pending_verification_email", form.email),
        navigate("/verify-email")
      }
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
