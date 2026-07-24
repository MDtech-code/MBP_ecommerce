// src/entities/user/model/authStore.js


import {
  setAuthToken,
  clearAuth,
  broadcastLogin,
  broadcastLogout,
} from "@shared/lib";
import { queryClient } from "@shared/lib";




/**
 * authStore — single source of truth for client auth state
 *
 * Owns:
 *   user object from login/profile response
 *   isAuthenticated boolean
 *   login() — sets token + stores user + broadcasts
 *   logout() — clears token + clears user + clears cache + broadcasts
 *   setUser() — updates user after profile fetch or edit
 *
 * Does NOT own:
 *   access token — that lives in auth.js memory
 *   server data — that lives in React Query cache
 */

export const createAuthSlice = (set) => ({
    user: null,
    isAuthenticated: false,
    isBootstrapping: true,

    /**
     * Called after successful login
     * Receives the full data object from login response
     * data.access → token
     * data.user   → user object
     */
    login: (data) => {
      sessionStorage.removeItem("logged_out");

      setAuthToken(data.access);
      broadcastLogin();
      set(
        {
          user: data.user,
          isAuthenticated: true,
        },
        false,
        "auth/login",
      );
    },

    /**
     * Called after profile fetch on page refresh
     * Updates user object without touching token
     * (token already restored by interceptor via refresh cookie)
     */
    setUser: (user) => {
      set({
        user,
        isAuthenticated: true,
      });
    },

    setBootstrapping: (value) => {
      // ← new action
      set({ isBootstrapping: value });
    },

    /**
     * Called on logout — clears everything
     */
    logout: () => {
      clearAuth();
      broadcastLogout();
      queryClient.clear();
      sessionStorage.setItem("logged_out", "true");
      set(
        {
          user: null,
          isAuthenticated: false,
        },
        false,
        "auth/logout",
      );
    },
  })

