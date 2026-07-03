// src/hooks/account/useAuth.js

import { useMutation } from "@tanstack/react-query";
import { accountService } from "../../services/accountService";

export function useRegister() {
  return useMutation({
    mutationFn: accountService.register,
    // No onSuccess business logic yet
    // Register → backend sends verification email
    // Component handles navigation to verify-email page
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
  })
}

/**
 * useResendVerification
 * POST /api/accounts/resend-verification/
 */
export function useResendVerification() {
  return useMutation({
    mutationFn: accountService.resendVerification,
  })
}
// // src/hooks/account/useAuth.js

// import { useMutation } from "@tanstack/react-query";
// import { accountService } from "../../services/accountService";
// import {
//   setAuthToken,
//   clearAuth,
//   broadcastLogin,
//   broadcastLogout,
// } from "../../api/auth";
// import { queryClient } from "../../lib/queryClient";

// /**
//  * useRegister
//  *
//  * Wraps POST /api/accounts/register/
//  *
//  * Usage in component:
//  *   const { mutate: register, isPending, isError, error } = useRegister()
//  *   register({ full_name, email, password, confirm_password })
//  *
//  * Component is responsible for:
//  *   - Calling normalizeError(error) to get clean error shape
//  *   - Navigating after success (via onSuccess callback)
//  *   - Showing field errors from getFieldErrors()
//  */
// export function useRegister() {
//   return useMutation({
//     mutationFn: accountService.register,
//     // No onSuccess here — register likely redirects to verify email
//     // Component handles navigation in its own onSuccess callback
//   });
// }

// /**
//  * useLogin
//  *
//  * Wraps POST /api/accounts/login/
//  *
//  * On success:
//  *   - Sets access token in memory + axios headers
//  *   - Broadcasts login to other tabs
//  *   - Clears stale cache from any previous session
//  *
//  * Usage in component:
//  *   const { mutate: login, isPending, isError, error } = useLogin()
//  *   login(
//  *     { email, password },
//  *     { onSuccess: () => navigate('/') }  ← component handles redirect
//  *   )
//  */
// export function useLogin() {
//   return useMutation({
//     mutationFn: accountService.login,

//     onSuccess: ({ data }) => {
//       // Set access token in memory — this updates axios headers automatically
//       setAuthToken(data.access);

//       // Tell other browser tabs this tab logged in
//       broadcastLogin();

//       // Wipe any cache from previous user session
//       queryClient.clear();
//     },

//     // onError: we do NOT normalize here
//     // Normalization happens in the component
//     // Hook stays clean — no UI concerns
//   });
// }

// /**
//  * useLogout
//  *
//  * Wraps POST /api/accounts/logout/
//  *
//  * Always clears client auth regardless of server response.
//  * If server call fails — we still log the user out on client.
//  *
//  * Usage:
//  *   const { mutate: logout } = useLogout()
//  *   logout()
//  */
// export function useLogout() {
//   return useMutation({
//     mutationFn: accountService.logout,

//     onSuccess: () => {
//       clearAuth();
//       broadcastLogout();
//       queryClient.clear();
//     },

//     onError: () => {
//       // Force logout on client even if server 500s
//       // Never leave user in broken auth state
//       clearAuth();
//       broadcastLogout();
//       queryClient.clear();
//     },
//   });
// }
