// src/features/profile/model/usePhoneVerification.js

import { useState } from "react";
import {
  useSendPhoneOtp,
  useVerifyPhoneOtp,
} from "../api/useProfileMutations";
import { normalizeError, ErrorCode } from "@shared/api";

export function usePhoneVerification({ onVerified }) {
  const [otpVisible, setOtpVisible] = useState(false);
  const [otp, setOtp] = useState("");
  const [pendingPhone, setPendingPhone] = useState("");

  const sendMutation = useSendPhoneOtp();
  const verifyMutation = useVerifyPhoneOtp();

  const sendNormalized = sendMutation.isError
    ? normalizeError(sendMutation.error)
    : null;

  const verifyNormalized = verifyMutation.isError
    ? normalizeError(verifyMutation.error)
    : null;

  // Send errors — field or non-field (phone format rejected by backend)
  const sendFieldError = sendNormalized?.errors?.fields?.phone?.message ?? null;
  const sendError = sendNormalized?.errors?.non_fields?.message ?? null;

  // Verify errors — OTP expired, invalid, wrong phone
  const verifyError = verifyNormalized?.errors?.non_fields?.message ?? null;
  const verifyCode = verifyNormalized?.errors?.non_fields?.code ?? null;

  function handleSendOtp(phone) {
    setPendingPhone(phone);
    sendMutation.reset();
    verifyMutation.reset();
    sendMutation.mutate(phone, {
      onSuccess: () => setOtpVisible(true),
    });
  }

  function handleVerifyOtp() {
    verifyMutation.mutate(
      { phone: pendingPhone, otp },
      {
        onSuccess: () => {
          setOtpVisible(false);
          setOtp("");
          onVerified(pendingPhone);
        },
      },
    );
  }

  function handleCancelOtp() {
    setOtpVisible(false);
    setOtp("");
    sendMutation.reset();
    verifyMutation.reset();
  }

  return {
    otpVisible,
    otp,
    setOtp,
    pendingPhone,
    isSending: sendMutation.isPending,
    isVerifying: verifyMutation.isPending,
    sendFieldError,
    sendError,
    verifyError,
    verifyCode,
    handleSendOtp,
    handleVerifyOtp,
    handleCancelOtp,
    ErrorCode,
  };
}
