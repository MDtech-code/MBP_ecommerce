// src/hooks/account/useRegisterForm.js

import { useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useRegister } from "@features/auth";
import { normalizeError, extractErrors, ErrorCode } from "@shared/api";
import { run, hasErrors, registerSchema } from "@shared/lib/validators";
import {useCountdown} from "@shared/ui";

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

  const formRef = useRef(form);
  formRef.current = form;
  const submitAttemptedRef = useRef(submitAttempted);
  submitAttemptedRef.current = submitAttempted;

  const normalized = isError ? normalizeError(error) : null;

  const { fieldErrors: serverFieldErrors, formError } =extractErrors(normalized);
  const fieldErrors = { ...clientErrors, ...serverFieldErrors };
  const { isActive: isRateLimited, formatted: retryCountdown } = useCountdown(normalized?.rateLimit?.resetAt);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;

    setForm((prev) => ({ ...prev, [name]: value }));

    setClientErrors((prev) => {
      if (!prev[name]) return prev;
      const next = { ...prev };
      delete next[name];
      return next;
    });
  }, []);

  const handleBlur = useCallback((e) => {
    if (!submitAttemptedRef.current) return;

    const { name } = e.target;
    const currentForm = formRef.current;
    const schema = registerSchema(currentForm);
    const fieldSchema = { [name]: schema[name] };
    const result = run(fieldSchema, currentForm);

    setClientErrors((prev) => {
      const next = { ...prev };
      if (result[name]) {
        next[name] = result[name];
      } else {
        delete next[name];
      }
      return next;
    });
  }, []);

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      setSubmitAttempted(true);

      const currentForm = formRef.current;
      const schema = registerSchema(currentForm);
      const result = run(schema, currentForm);

      if (hasErrors(result)) {
        setClientErrors(result);
        return;
      }

      setClientErrors({});

      register(currentForm, {
        onSuccess: () => {
          navigate("/verify-email");
        },
      });
    },
    [register, navigate],
  );

  return {
    form,
    fieldErrors,
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
