// src/hooks/account/useLoginForm.js
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin, useResendVerification } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

export function useLoginForm() {
  const navigate = useNavigate();
  const { mutate: login, isPending, isError, error } = useLogin();
  const {
    mutate: resendVerification,
    isPending: isResending,
    isSuccess: isResendSuccess,
  } = useResendVerification();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const normalized = isError ? normalizeError(error) : null;

  // Field level errors (email or password individually)
  const fieldErrors = {
    email: normalized?.errors?.fields?.email?.message ?? null,
    password: normalized?.errors?.fields?.password?.message ?? null,
  };

  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    login(form, {
      onSuccess: () => navigate("/profile"),
    });
  };

  // ── Resend from login page ─────────────────────────────────────────────────
  // Email stored in localStorage after successful registration.
  // If user cleared storage, falls back to what they typed in the form.
  const handleResend = () => {
    const email =
      localStorage.getItem("pending_verification_email") || form.email;
    if (!email || isResending) return;
    resendVerification({ email });
  };

  return {
    form,
    fieldErrors,
    formErrorCode,
    formError,
    isPending,
    isResending,
    isResendSuccess,
    handleChange,
    handleSubmit,
    handleResend,
  };
}
