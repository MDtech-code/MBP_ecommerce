// src/features/auth/model/useNewEmailOTPForm.js

import { useState,  useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useConfirmEmailChange } from "../api/useAuthMutations";
import { useAuthStore } from "@entities/user";
import { normalizeError } from "@shared/api";

/**
 * New email OTP entry form logic.
 *
 * Phase 3 of email change — user enters OTP sent to NEW address.
 *
 * Differences from useOTPEntryForm:
 *   - No "use another way" option
 *   - On success → logout → login page
 *   - Calls confirmEmailChange not verifySecurityOTP
 *   - No resend (user must restart flow to resend)
 *
 * Reads from location.state:
 *   maskedNewEmail → display in UI
 */
export function useNewEmailOTPForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  console.log(location.state)
  const { maskedNewEmail } = location.state ?? {};

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const inputRefs = useRef([]);

  const {
    mutate: confirmChange,
    isPending,
    isError,
    error,
    reset,
  } = useConfirmEmailChange();

  const normalized = isError ? normalizeError(error) : null;
  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;
  const attemptsLeft =
    normalized?.errors?.non_fields?.extra?.attempts_left ?? null;

  const handleOtpChange = (index, value) => {
    if (!/^\d?$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    if (isError) reset();
    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index, e) => {
    if (e.key === "Backspace" && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e) => {
    e.preventDefault();
    const pasted = e.clipboardData
      .getData("text")
      .replace(/\D/g, "")
      .slice(0, 6);
    if (!pasted) return;
    const newOtp = [...otp];
    pasted.split("").forEach((digit, i) => {
      newOtp[i] = digit;
    });
    setOtp(newOtp);
    inputRefs.current[Math.min(pasted.length - 1, 5)]?.focus();
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    const otpCode = otp.join("");
    if (otpCode.length !== 6) return;

    confirmChange(
      { otp_code: otpCode },
      {
        onSuccess: () => {
          logout();
          navigate("/login", {
            replace: true,
            state: {
              message:
                "Email updated successfully. Please log in with your new email address.",
            },
          });
        },
      },
    );
  };

  const isComplete = otp.join("").length === 6;

  return {
    otp,
    inputRefs,
    maskedNewEmail,
    formError,
    formErrorCode,
    attemptsLeft,
    isPending,
    isComplete,
    handleOtpChange,
    handleKeyDown,
    handlePaste,
    handleSubmit,
  };
}
