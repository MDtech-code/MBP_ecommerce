import { useMutation } from "@tanstack/react-query";
import { accountService } from "@shared/api";
import { useAuthStore } from "@entities/user";

export function useRegister() {
  return useMutation({
    mutationFn: accountService.register,
    // No onSuccess business logic yet
    // Register → backend sends verification email
    // Component handles navigation to verify-email page
  });
}

/**
 * Universal social login mutation.
 * Used by both Google and Facebook buttons.
 * Provider is passed as part of the payload at call time.
 */
export function useSocialLogin() {
  return useMutation({
    mutationFn: accountService.socialLogin,
  });
}

// ── NEW ──────────────────────────────────────────────────────────────────────

/**
 * useVerifyEmail
 * POST /api/accounts/verify-email/
 * On success: clean up sessionStorage, navigate to login
 */
export function useVerifyEmail() {
  return useMutation({
    mutationFn: accountService.verifyEmail,
  });
}

/**
 * useResendVerification
 * POST /api/accounts/resend-verification/
 */
export function useResendVerification() {
  return useMutation({
    mutationFn: accountService.resendVerification,
  });
}

// ── NEW ───────────────────────────────────────────────────────────────────────

/**
 * useLogin
 * On success: stores token + user in authStore
 * Navigation handled in useLoginForm.js
 */
export function useLogin() {
  const login = useAuthStore((state) => state.login);

  return useMutation({
    mutationFn: accountService.login,
    onSuccess: ({ data }) => {
      // data.access → access token
      // data.user   → full user object
      login(data);
    },
  });
}

/**
 * useLogout
 * On success AND error: always clear client state
 * Server call failing must never leave user stuck in auth limbo
 */
export function useLogout() {
  const logout = useAuthStore((state) => state.logout);

  return useMutation({
    mutationFn: accountService.logout,
    onSuccess: () => {
      logout();
    },
    onError: () => {
      // Force logout on client even if server call fails
      logout();
    },
  });
}

/**
 * useRequestPasswordReset
 * POST /api/accounts/password-reset/
 * No onSuccess business logic needed — backend always returns generic success
 * message regardless of whether email exists (prevents email enumeration)
 * Navigation to confirmation screen handled in useForgotPasswordForm.js
 */
export function useRequestPasswordReset() {
  return useMutation({
    mutationFn: accountService.requestPasswordReset,
  });
}

/**
 * useConfirmPasswordReset
 * POST /api/accounts/password-reset/confirm/
 * Token comes from URL query param — passed in by useResetPasswordForm.js
 * Navigation to login handled in useResetPasswordForm.js after success
 */
export function useConfirmPasswordReset() {
  return useMutation({
    mutationFn: accountService.confirmPasswordReset,
  });
}



export function useSendSecurityOTP() {
  return useMutation({ mutationFn: accountService.sendSecurityOTP });
}

export function useVerifySecurityOTP() {
  return useMutation({ mutationFn: accountService.verifySecurityOTP });
}

export function useChangePassword() {
  return useMutation({ mutationFn: accountService.changePassword });
}

export function useRequestEmailChange() {
  return useMutation({ mutationFn: accountService.requestEmailChange });
}

export function useConfirmEmailChange() {
  return useMutation({ mutationFn: accountService.confirmEmailChange });
}

export function useDeleteAccount() {
  return useMutation({ mutationFn: accountService.deleteAccount });
}
// /**
//  * useChangePassword
//  * POST /api/accounts/change-password/
//  * Backend invalidates all sessions after success — we must also clear
//  * client auth state so user is forced to log in again with new password
//  * Navigation to login handled in useChangePasswordForm.js after success
//  */
// export function useChangePassword() {
//   const logout = useAuthStore((state) => state.logout);

//   return useMutation({
//     mutationFn: accountService.changePassword,
//     onSuccess: () => {
//       // Backend has already invalidated all server sessions
//       // Clear client state to match — user must re-authenticate
//       logout();
//     },
//   });
// }

// export function useRequestEmailChange() {
//   return useMutation({
//     mutationFn: accountService.requestEmailChange,
//   });
// }

// export function useConfirmEmailChange() {
//   return useMutation({
//     mutationFn: accountService.confirmEmailChange,
//   });
// }

// export function useDeleteAccount() {
//   return useMutation({
//     mutationFn: accountService.deleteAccount,
//   });
// }