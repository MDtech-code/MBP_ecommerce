// src/hooks/account/useRegisterForm.js

import { useState, useCallback,useRef,useLayoutEffect } from "react";
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
  // A synchronous guard also covers two submits before React rerenders.
  const submittingRef = useRef(false);
  const formRef = useRef(form);
  const submitAttemptedRef = useRef(submitAttempted);

  useLayoutEffect(() => {
    formRef.current = form;
    submitAttemptedRef.current = submitAttempted;
  }, [form, submitAttempted]);


  const normalized = isError ? normalizeError(error) : null;

  const { fieldErrors: serverFieldErrors, formError } =extractErrors(normalized);
  const fieldErrors = { ...clientErrors, ...serverFieldErrors };
  const { isActive: isRateLimited, formatted: retryCountdown } = useCountdown(normalized?.rateLimit?.resetAt);



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
    },
    [],
  );

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      if (submittingRef.current || isPending || isRateLimited) return;
      setSubmitAttempted(true);
      const currentForm = formRef.current;
      const schema = registerSchema(currentForm);
      const result = run(schema,currentForm);

      if (hasErrors(result)) {
        setClientErrors(result);
        return;
      }

      setClientErrors({});

      submittingRef.current = true;
      register(currentForm, {
        onSettled: () => {
          submittingRef.current = false;
        },
        onSuccess: () => {
          navigate("/verify-email");
        },
      });
    },
    [register, navigate, isPending, isRateLimited],
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
