// src/features/auth/model/useOTPEntryForm.js

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import {
  useVerifySecurityOTP,
  useSendSecurityOTP,
} from "../api/useAuthMutations";
import { normalizeError } from "@shared/api";

const COOLDOWN_SECONDS = 60;

// ── localStorage helpers ───────────────────────────────────────────────────
function getStorageKey(purpose) {
  return `otp_sent_at_${purpose}`;
}

function saveOtpSentAt(purpose) {
  localStorage.setItem(getStorageKey(purpose), Date.now().toString());
}

function getSecondsRemaining(purpose) {
  const raw = localStorage.getItem(getStorageKey(purpose));
  if (!raw) return 0;
  const elapsed = Math.floor((Date.now() - parseInt(raw, 10)) / 1000);
  const remaining = COOLDOWN_SECONDS - elapsed;
  return remaining > 0 ? remaining : 0;
}

function clearOtpSentAt(purpose) {
  localStorage.removeItem(getStorageKey(purpose));
}

export function useOTPEntryForm() {
  const navigate = useNavigate();
  const location = useLocation();

  const { purpose, maskedEmail, nextPath } = location.state ?? {};

  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const inputRefs = useRef([]);
  const timerRef = useRef(null);

  // ── Initialize from localStorage — survives refresh ───────────────────────
  const [resendSeconds, setSeconds] = useState(() =>
    purpose ? getSecondsRemaining(purpose) : 0,
  );

  const {
    mutate: verifyOTP,
    isPending: isVerifying,
    isError: isVerifyError,
    error: verifyError,
    reset: resetVerify,
  } = useVerifySecurityOTP();

  const { mutate: resendOTP, isPending: isResending } = useSendSecurityOTP();

  const normalized = isVerifyError ? normalizeError(verifyError) : null;
  const formError = normalized?.errors?.non_fields?.message ?? null;
  const formErrorCode = normalized?.errors?.non_fields?.code ?? null;
  const attemptsLeft =
    normalized?.errors?.non_fields?.extra?.attempts_left ?? null;

  // ── Countdown tick ─────────────────────────────────────────────────────────
  const startCountdown = useCallback(
    (seconds) => {
      setSeconds(seconds);
      clearInterval(timerRef.current);

      if (seconds <= 0) return;

      timerRef.current = setInterval(() => {
        const remaining = getSecondsRemaining(purpose);
        setSeconds(remaining);
        if (remaining <= 0) {
          clearInterval(timerRef.current);
        }
      }, 1000);
    },
    [purpose],
  );

  // ── On mount: resume existing countdown or start fresh ────────────────────
  useEffect(() => {
    if (!purpose) return;

    const remaining = getSecondsRemaining(purpose);

    if (remaining > 0) {
      // OTP was already sent (possibly before refresh) — resume countdown
      startCountdown(remaining);
    } else {
      // First visit — OTP sent by gate page, stamp now
      saveOtpSentAt(purpose);
      startCountdown(COOLDOWN_SECONDS);
    }

    return () => clearInterval(timerRef.current);
  }, [purpose]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── OTP input handlers ─────────────────────────────────────────────────────
  const handleOtpChange = (index, value) => {
    if (!/^\d?$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);
    if (isVerifyError) resetVerify();
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

  // ── Submit ─────────────────────────────────────────────────────────────────
  const handleSubmit = (e) => {
    e.preventDefault();
    const otpCode = otp.join("");
    if (otpCode.length !== 6) return;

    verifyOTP(
      { purpose, otp_code: otpCode },
      {
        onSuccess: (data) => {
          clearOtpSentAt(purpose); // ← clean up on success
          const verificationToken = data.data.verification_token;
          navigate(nextPath, {
            replace: true,
            state: { verificationToken, purpose },
          });
        },
      },
    );
  };

  // ── Resend ─────────────────────────────────────────────────────────────────
  const handleResend = () => {
    if (resendSeconds > 0 || isResending) return;

    resendOTP(
      { purpose },
      {
        onSuccess: () => {
          setOtp(["", "", "", "", "", ""]);
          resetVerify();
          saveOtpSentAt(purpose); // ← stamp fresh timestamp
          startCountdown(COOLDOWN_SECONDS);
          inputRefs.current[0]?.focus();
        },
        onError: (err) => {
          const n = normalizeError(err);
          const extra = n?.errors?.non_fields?.extra;
          if (extra?.seconds_remaining) {
            // Backend says cooldown still active — sync localStorage
            const correctedAt =
              Date.now() - (COOLDOWN_SECONDS - extra.seconds_remaining) * 1000;
            localStorage.setItem(
              getStorageKey(purpose),
              correctedAt.toString(),
            );
            startCountdown(extra.seconds_remaining);
          }
        },
      },
    );
  };

  const otpCode = otp.join("");
  const isComplete = otpCode.length === 6;

  return {
    otp,
    inputRefs,
    purpose,
    maskedEmail,
    formError,
    formErrorCode,
    attemptsLeft,
    isVerifying,
    isResending,
    isComplete,
    resendSeconds,
    handleOtpChange,
    handleKeyDown,
    handlePaste,
    handleSubmit,
    handleResend,
  };
}
// // src/features/auth/model/useOTPEntryForm.js

// import { useState, useEffect, useRef, useCallback } from "react";
// import { useNavigate, useLocation } from "react-router-dom";
// import {
//   useVerifySecurityOTP,
//   useSendSecurityOTP,
// } from "../api/useAuthMutations";
// import { normalizeError } from "@shared/api";

// /**
//  * OTP entry form logic.
//  *
//  * Handles:
//  *   - 6-box OTP input state
//  *   - Auto-advance on digit entry
//  *   - Backspace to previous box
//  *   - Paste support (paste 6 digits fills all boxes)
//  *   - Submit OTP to backend
//  *   - Resend with 60-second cooldown timer
//  *   - Navigate to next page on success with verification_token
//  *   - Show attempts remaining from backend client_extra
//  *
//  * Reads from router location.state:
//  *   purpose     → which sensitive action
//  *   maskedEmail → display in UI
//  *   nextPath    → where to navigate after verification
//  */
// const COOLDOWN_SECONDS = 60;

// // ── localStorage helpers ───────────────────────────────────────────────────
// function getStorageKey(purpose) {
//   return `otp_sent_at_${purpose}`;
// }

// function saveOtpSentAt(purpose) {
//   localStorage.setItem(getStorageKey(purpose), Date.now().toString());
// }

// function getSecondsRemaining(purpose) {
//   const raw = localStorage.getItem(getStorageKey(purpose));
//   if (!raw) return 0;
//   const elapsed = Math.floor((Date.now() - parseInt(raw, 10)) / 1000);
//   const remaining = COOLDOWN_SECONDS - elapsed;
//   return remaining > 0 ? remaining : 0;
// }

// function clearOtpSentAt(purpose) {
//   localStorage.removeItem(getStorageKey(purpose));
// }
// export function useOTPEntryForm() {
//   const navigate = useNavigate();
//   const location = useLocation();

//   const { purpose, maskedEmail, nextPath } = location.state ?? {};

//   // ── OTP box state — 6 individual values ───────────────────────────────────
//   const [otp, setOtp] = useState(["", "", "", "", "", ""]);

//   const inputRefs = useRef([]);
//   const timerRef = useRef(null);
//   // ── Initialize from localStorage — survives refresh ───────────────────────
//   const [resendSeconds, setSeconds] = useState(() =>
//     purpose ? getSecondsRemaining(purpose) : 0,
//   );

//   const {
//     mutate: verifyOTP,
//     isPending: isVerifying,
//     isError: isVerifyError,
//     error: verifyError,
//     reset: resetVerify,
//   } = useVerifySecurityOTP();

//   const { mutate: resendOTP, isPending: isResending } = useSendSecurityOTP();

//   const normalized = isVerifyError ? normalizeError(verifyError) : null;
//   const formError = normalized?.errors?.non_fields?.message ?? null;
//   const formErrorCode = normalized?.errors?.non_fields?.code ?? null;
//   const attemptsLeft =
//     normalized?.errors?.non_fields?.extra?.attempts_left ?? null;

//   // ── Countdown tick ─────────────────────────────────────────────────────────
//   const startCountdown = useCallback(
//     (seconds) => {
//       setSeconds(seconds);
//       clearInterval(timerRef.current);

//       if (seconds <= 0) return;

//       timerRef.current = setInterval(() => {
//         const remaining = getSecondsRemaining(purpose);
//         setSeconds(remaining);
//         if (remaining <= 0) {
//           clearInterval(timerRef.current);
//         }
//       }, 1000);
//     },
//     [purpose],
//   );

//   // ── On mount: resume existing countdown or start fresh ────────────────────
//   useEffect(() => {
//     if (!purpose) return;

//     const remaining = getSecondsRemaining(purpose);

//     if (remaining > 0) {
//       // OTP was already sent (possibly before refresh) — resume countdown
//       startCountdown(remaining);
//     } else {
//       // First visit — OTP sent by gate page, stamp now
//       saveOtpSentAt(purpose);
//       startCountdown(COOLDOWN_SECONDS);
//     }

//     return () => clearInterval(timerRef.current);
//   }, [purpose]);

//   // ── OTP input handlers ─────────────────────────────────────────────────────

//   const handleOtpChange = (index, value) => {
//     // Only accept single digit
//     if (!/^\d?$/.test(value)) return;

//     const newOtp = [...otp];
//     newOtp[index] = value;
//     setOtp(newOtp);

//     if (isVerifyError) resetVerify();

//     // Auto-advance to next box
//     if (value && index < 5) {
//       inputRefs.current[index + 1]?.focus();
//     }
//   };

//   const handleKeyDown = (index, e) => {
//     // Backspace on empty box → go to previous
//     if (e.key === "Backspace" && !otp[index] && index > 0) {
//       inputRefs.current[index - 1]?.focus();
//     }
//   };

//   const handlePaste = (e) => {
//     e.preventDefault();
//     const pasted = e.clipboardData
//       .getData("text")
//       .replace(/\D/g, "")
//       .slice(0, 6);
//     if (!pasted) return;

//     const newOtp = [...otp];
//     pasted.split("").forEach((digit, i) => {
//       newOtp[i] = digit;
//     });
//     setOtp(newOtp);

//     // Focus last filled box
//     const lastIndex = Math.min(pasted.length - 1, 5);
//     inputRefs.current[lastIndex]?.focus();
//   };

//   // ── Submit ─────────────────────────────────────────────────────────────────

//   const handleSubmit = (e) => {
//     e.preventDefault();
//     const otpCode = otp.join("");
//     if (otpCode.length !== 6) return;

//     verifyOTP(
//       { purpose, otp_code: otpCode },
//       {
//         onSuccess: (data) => {
//           clearOtpSentAt(purpose);
//           const verificationToken = data.data.verification_token;
//           // Navigate to next page with token in state
//           navigate(nextPath, {
//             replace: true,
//             state: {
//               verificationToken,
//               purpose,
//             },
//           });
//         },
//       },
//     );
//   };

//   // ── Resend ─────────────────────────────────────────────────────────────────

//   const handleResend = () => {
//     if (resendSeconds > 0 || isResending) return;

//     resendOTP(
//       { purpose },
//       {
//         onSuccess: () => {
//           setOtp(["", "", "", "", "", ""]);
//           resetVerify();
//           saveOtpSentAt(purpose);
//           startCountdown(COOLDOWN_SECONDS);
//           inputRefs.current[0]?.focus();
//         },
//         onError: (err) => {
//           const n = normalizeError(err);
//           const extra = n?.errors?.non_fields?.extra;
//           if (extra?.seconds_remaining) {
//             // Backend says cooldown still active — sync localStorage
//             const correctedAt =
//               Date.now() - (COOLDOWN_SECONDS - extra.seconds_remaining) * 1000;
//             localStorage.setItem(
//               getStorageKey(purpose),
//               correctedAt.toString(),
//             );
//             startCountdown(extra.seconds_remaining);
//           }
//         },
//       },
//     );
//   };

//   const otpCode = otp.join("");
//   const isComplete = otpCode.length === 6;

//   return {
//     otp,
//     inputRefs,
//     purpose,
//     maskedEmail,
//     formError,
//     formErrorCode,
//     attemptsLeft,
//     isVerifying,
//     isResending,
//     isComplete,
//     resendSeconds,
//     handleOtpChange,
//     handleKeyDown,
//     handlePaste,
//     handleSubmit,
//     handleResend,
//   };
// }
