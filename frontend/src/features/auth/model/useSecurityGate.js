// src/features/auth/model/useSecurityGate.js


import { useNavigate } from "react-router-dom";
import { useSendSecurityOTP } from "../api/useAuthMutations";
import { normalizeError } from "@shared/api";

/**
 * Security Verification Gate logic.
 *
 * This hook manages the identity verification step
 * that happens BEFORE any sensitive action.
 *
 * Flow:
 *   1. User lands on /security/verify?purpose=change_email
 *   2. Chooses "Email Verification" method
 *   3. This hook calls POST /api/accounts/security/send-otp/
 *   4. Backend sends OTP to current email
 *   5. Navigate to OTP entry page with context
 *
 * Purpose is read from URL search params.
 * Passed through to OTP page so it knows which action to complete.
 *
 * @param {string} purpose - SecurityPurpose string from URL
 */
export function useSecurityGate(purpose) {
  const navigate = useNavigate();

  const {
    mutate: sendOTP,
    isPending,
    isError,
    error,
    reset,
  } = useSendSecurityOTP();

  const normalized = isError ? normalizeError(error) : null;
  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;

  // Resend cooldown from backend client_extra
  const secondsRemaining =
    normalized?.errors?.non_fields?.extra?.seconds_remaining ?? null;

  const handleEmailVerification = () => {
    reset();
    sendOTP(
      { purpose },
      {
        onSuccess: (data) => {
          // Navigate to OTP entry page
          // Pass masked_email and purpose as state — no URL exposure
          navigate("/security/verify-otp", {
            state: {
              purpose,
              maskedEmail: data.data.masked_email,
              // Which page to go to after OTP verified
              nextPath: _getNextPath(purpose),
            },
          });
        },
      },
    );
  };

  return {
    isPending,
    formError,
    formErrorCode,
    secondsRemaining,
    handleEmailVerification,
  };
}

// Maps purpose to the page shown after identity is verified
function _getNextPath(purpose) {
  const map = {
    change_password: "/security/change-password",
    change_email: "/security/change-email/new",
    delete_account: "/security/delete-account/confirm",
  };
  return map[purpose] ?? "/security";
}
