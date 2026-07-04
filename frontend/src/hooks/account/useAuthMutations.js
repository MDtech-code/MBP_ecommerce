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