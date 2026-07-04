// src/hooks/account/useLoginForm.js
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useLogin } from "./useAuthMutations";
import { normalizeError } from "../../api/transformers";

export function useLoginForm() {
  const navigate = useNavigate();
  const { mutate: login, isPending, isError, error } = useLogin();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const normalized = isError ? normalizeError(error) : null;

  // Login errors come as non_field_errors from backend
  const formError = normalized?.errors?.non_field_errors?.[0] ?? null;

  // Field level errors (email or password individually)
  const fieldErrors = {
    email: normalized?.errors?.email?.[0] ?? null,
    password: normalized?.errors?.password?.[0] ?? null,
  };

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    login(form, {
      onSuccess: () => navigate("/profile"),
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
