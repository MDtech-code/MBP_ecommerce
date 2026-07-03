// src/hooks/useAuthMutations.js
import { useMutation } from "@tanstack/react-query";
import { authService } from "../services/authService";
import { normalizeError } from "../api/transformers";
import {
  setAuthToken,
  broadcastLogin,
  broadcastLogout,
  clearAuth,
} from "../api/auth";
import { queryClient } from "../lib/queryClient";

/**
 * Login mutation hook.
 *
 * Usage:
 *   const { mutate: login, isPending, error } = useLogin()
 *   login({ email, password })
 *
 * On success: sets access token, broadcasts login, invalidates all queries
 * On error: returns normalized error — component decides how to display
 */
export function useLogin() {
  return useMutation({
    mutationFn: authService.login,

    onSuccess: ({ data, message }) => {
      // Set access token in memory + axios headers
      setAuthToken(data.access);

      // Notify other tabs
      broadcastLogin();

      // Clear any stale cached data from previous session
      queryClient.clear();
    },

    onError: (error) => {
      // Normalize for consistent handling — component uses this
      return normalizeError(error);
    },
  });
}

/**
 * Logout mutation hook.
 */
export function useLogout() {
  return useMutation({
    mutationFn: authService.logout,

    onSuccess: () => {
      clearAuth();
      broadcastLogout();
      queryClient.clear();
    },

    onError: () => {
      // Force logout on client even if server call fails
      clearAuth();
      broadcastLogout();
      queryClient.clear();
    },
  });
}

/**
 * Register mutation hook.
 */
export function useRegister() {
  return useMutation({
    mutationFn: authService.register,
    // No onSuccess token setting — most flows require email verification first
  });
}
