// src/hooks/account/useRegisterForm.js

import { useState,useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useRegister } from "../api/useAuthMutations";
import { normalizeError,extractErrors, ErrorCode } from "@shared/api";
import { run, hasErrors, registerSchema } from "@shared/lib/validators";

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
  // const { fieldErrors, formError, formErrorCode } = extractErrors(normalized);
  const { fieldErrors: serverFieldErrors, formError, formErrorCode } = extractErrors(normalized);
  const fieldErrors = { ...clientErrors, ...serverFieldErrors };
/*
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
   const formError = normalized?.errors?.non_fields?.message ?? null;
   const formErrorCode = normalized?.errors?.non_fields?.code ?? null;
   */
  



  
  // const handleChange = (e) => {
  //   setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  // };

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
    [clientErrors]
  );


  // const handleSubmit = (e) => {
  //   e.preventDefault();
  //   register(form, {
  //     onSuccess: () => {
  //       // localStorage.setItem("pending_verification_email", form.email);
  //       // sessionStorage.setItem("pending_verification_email", form.email);
  //       navigate("/verify-email");
  //     }
  //   });
  // };
  const handleBlur = useCallback(
    (e) => {
      // Only validate on blur after first submit attempt.
      // Before that, showing errors while user hasn't even tried to submit
      // is aggressive UX — they might not have finished typing yet.
      if (!submitAttempted) return;

      const { name } = e.target;

      // Build schema with current form state (needed for matchesField).
      // Run ONLY for this field to avoid showing all errors on single blur.
      const schema = registerSchema(form);
      const fieldSchema = { [name]: schema[name] };
      const result = run(fieldSchema, form);

      setClientErrors((prev) => {
        const next = { ...prev };
        if (result[name]) {
          next[name] = result[name];
        } else {
          delete next[name]; // field is now valid — remove its error
        }
        return next;
      });
    },
    [submitAttempted, form]
  );

  const handleSubmit = useCallback(
    (e) => {
      e.preventDefault();
      setSubmitAttempted(true);

      // Run full schema validation before touching the network.
      const schema = registerSchema(form);
      const result = run(schema, form);

      if (hasErrors(result)) {
        // Show all client errors at once on submit attempt.
        setClientErrors(result);
        return; // ← Block HTTP call entirely.
      }

      // All client rules pass — clear any stale client errors and go.
      setClientErrors({});

      register(form, {
        onSuccess: () => {
          navigate("/verify-email");
        },
        // onError is handled by isError + error from useRegister —
        // normalizeError picks it up automatically, no extra handling needed.
      });
    },
    [form, register, navigate]
  );


  return {
    form,
    fieldErrors,
    formErrorCode,
    formError,
    isPending,
    ErrorCode,
    handleBlur,
    handleChange,
    handleSubmit,
  };
}
