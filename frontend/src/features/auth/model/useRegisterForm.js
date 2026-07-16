// src/hooks/account/useRegisterForm.js

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useRegister } from "../api/useAuthMutations";
import { normalizeError, ErrorCode } from "../../../shared/api/transformers";

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
     full_name: normalized?.errors?.fields?.full_name?.message ?? null,
     email: normalized?.errors?.fields?.email?.message ?? null,
     password: normalized?.errors?.fields?.password?.message ?? null,
     confirm_password:
       normalized?.errors?.fields?.confirm_password?.message ?? null,
   };

  const fieldCodes = {
     full_name: normalized?.errors?.fields?.full_name?.code ?? null,
     email: normalized?.errors?.fields?.email?.code ?? null,
     password: normalized?.errors?.fields?.password?.code ?? null,
     confirm_password:
       normalized?.errors?.fields?.confirm_password?.code ?? null,
   };

  const formError = normalized?.errors?.non_field_errors?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  const handleChange = (e) => {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    register(form, {
      onSuccess: () => {
        // Store email for VerifyEmail page to display + use for resend
        localStorage.setItem("pending_verification_email", form.email);
        navigate("/verify-email");
      }
    });
  };

  return {
    form,
    fieldErrors,
    fieldCodes,
    formErrorCode,
    formError,
    isPending,
    ErrorCode,
    handleChange,
    handleSubmit,
  };
}
