// src/hooks/account/useAuth.js

import { useMutation, useQuery } from "@tanstack/react-query";
import { accountService } from "../../services/accountService";
import { useAuthStore } from "../../stores/authStore";

import { queryClient } from "../../lib/queryClient";

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
 * useProfile
 * GET /api/accounts/profile/
 * Called on protected pages to restore user state after page refresh
 * Only runs when user has an access token (hasAuthToken check in component)
 */
export function useProfile(options = {}) {
  const setUser = useAuthStore((state) => state.setUser);

  return useQuery({
    queryKey: ["account", "profile"],
    queryFn: async () => {
      const result = await accountService.getProfile();
      // Sync fetched profile into Zustand so UI is always consistent
      setUser(result.data);
      return result;
    },
    ...options,
  });
}

export function useUpdateProfile() {
  const setUser = useAuthStore((state) => state.setUser);
  return useMutation({
    mutationFn: accountService.updateProfile,
    onSuccess: ({ data }) => {
      setUser(data);
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}



export function useUploadAvatar() {
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  return useMutation({
    mutationFn: accountService.uploadAvatar,
    onSuccess: ({ data }) => {
      setUser({
        ...user,
        profile: {
          ...user.profile,
          avatar: data.avatar,
        },
      });
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

/**
 * useChangePassword
 * POST /api/accounts/change-password/
 * Backend invalidates all sessions after success — we must also clear
 * client auth state so user is forced to log in again with new password
 * Navigation to login handled in useChangePasswordForm.js after success
 */
export function useChangePassword() {
  const logout = useAuthStore((state) => state.logout);

  return useMutation({
    mutationFn: accountService.changePassword,
    onSuccess: () => {
      // Backend has already invalidated all server sessions
      // Clear client state to match — user must re-authenticate
      logout();
    },
  });
}



// src/hooks/account/useAuthMutations.js
// Add these after useChangePassword

/**
 * useCreateAddress
 * POST /api/accounts/addresses/
 * On success: sync full user back into store so addresses list updates
 * immediately without page refresh
 */
export function useCreateAddress() {
  

  return useMutation({
    mutationFn: accountService.createAddress,
    onSuccess: () => {
      // Refetch full profile — addresses are nested in user object
      // invalidateQueries triggers useProfile to re-fetch and setUser
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}

/**
 * useUpdateAddress
 * PUT /api/accounts/addresses/:id/
 * On success: refetch profile to sync updated address into store
 */
export function useUpdateAddress() {
  return useMutation({
    mutationFn: ({ id, data }) => accountService.updateAddress(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}

/**
 * useDeleteAddress
 * DELETE /api/accounts/addresses/:id/
 * On success: refetch profile — deleted address must disappear from list
 */
export function useDeleteAddress() {
  return useMutation({
    mutationFn: (id) => accountService.deleteAddress(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}

/**
 * useSetDefaultAddress
 * PATCH /api/accounts/addresses/:id/set-default/
 * On success: refetch profile — is_default flags must update across all cards
 */
export function useSetDefaultAddress() {
  return useMutation({
    mutationFn: (id) => accountService.setDefaultAddress(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}