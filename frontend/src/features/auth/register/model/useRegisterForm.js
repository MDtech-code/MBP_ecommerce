// src/hooks/account/useRegisterForm.js

import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useRegister } from "@features/auth";
import { normalizeError, extractErrors, ErrorCode } from "@shared/api";
import { run, hasErrors, registerSchema } from "@shared/lib/validators";
import useCountdown from "../../../../shared/ui/useCountdown";

export function useRegisterForm() {
  const navigate = useNavigate();
  const { mutate: register, isPending, isError, error } = useRegister();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [submitAttempted, setSubmitAttempted] = useState(false);
  const [clientErrors, setClientErrors] = useState({});

  const normalized = isError ? normalizeError(error) : null;

  const { fieldErrors: serverFieldErrors, formError } =
    extractErrors(normalized);
  const fieldErrors = { ...clientErrors, ...serverFieldErrors };
  const { isActive: isRateLimited, formatted: retryCountdown } = useCountdown(
  normalized?.rateLimit?.resetAt
);

  // ── OnChange Handlers ──────────────────────────────────────────────────────────────

  const handleChange = useCallback(
    (e) => {
      const { name, value } = e.target;

      setForm((prev) => ({ ...prev, [name]: value }));

      if (clientErrors[name]) {
        setClientErrors((prev) => {
          const next = { ...prev };
          delete next[name];
          return next;
        });
      }
    },
    [clientErrors],
  );

  const handleBlur = useCallback(
    (e) => {
      if (!submitAttempted) return;

      const { name } = e.target;

      const schema = registerSchema(form);
      const fieldSchema = { [name]: schema[name] };
      const result = run(fieldSchema, form);

      setClientErrors((prev) => {
        const next = { ...prev };
        if (result[name]) {
          next[name] = result[name];
        } else {
          delete next[name];
        }
        return next;
      });
    },
    [submitAttempted, form],
  );

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      setSubmitAttempted(true);

      const schema = registerSchema(form);
      const result = run(schema, form);

      if (hasErrors(result)) {
        setClientErrors(result);
        return;
      }

      setClientErrors({});

      register(form, {
        onSuccess: () => {
          navigate("/verify-email");
        },
      });
    },
    [form, register, navigate],
  );

  return {
    form,
    fieldErrors,
    // formErrorCode,
    formError,
    isPending,
    ErrorCode,
    isRateLimited,
    retryCountdown,
    handleBlur,
    handleChange,
    handleSubmit,
  };
}
