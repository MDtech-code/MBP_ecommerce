// src/test/stores/authStore.test.js

import { describe, it, expect, beforeEach, vi } from "vitest";

// ─────────────────────────────────────────────────────────────
// Mock auth helpers
// ─────────────────────────────────────────────────────────────

vi.mock("../../api/auth", () => ({
  setAuthToken: vi.fn(),
  clearAuth: vi.fn(),
  broadcastLogin: vi.fn(),
  broadcastLogout: vi.fn(),
}));

vi.mock("../../lib/queryClient", () => ({
  queryClient: {
    clear: vi.fn(),
  },
}));

import { useAuthStore } from "../../stores/authStore";
import {
  setAuthToken,
  clearAuth,
  broadcastLogin,
  broadcastLogout,
} from "../../api/auth";

import { queryClient } from "../../lib/queryClient";

describe("authStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    sessionStorage.clear();

    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      isBootstrapping: true,
    });
  });

  // ────────────────────────────────────────────────────────────
  // Initial State
  // ────────────────────────────────────────────────────────────

  describe("initial state", () => {
    it("starts unauthenticated", () => {
      const state = useAuthStore.getState();

      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(state.isBootstrapping).toBe(true);
    });
  });

  // ────────────────────────────────────────────────────────────
  // login()
  // ────────────────────────────────────────────────────────────

  describe("login", () => {
    it("stores authenticated user", () => {
      const data = {
        access: "jwt-token",
        user: {
          id: 1,
          email: "john@test.com",
        },
      };

      useAuthStore.getState().login(data);

      const state = useAuthStore.getState();

      expect(state.user).toEqual(data.user);
      expect(state.isAuthenticated).toBe(true);
    });

    it("stores access token", () => {
      const data = {
        access: "jwt-token",
        user: {},
      };

      useAuthStore.getState().login(data);

      expect(setAuthToken).toHaveBeenCalledWith("jwt-token");
    });

    it("broadcasts login event", () => {
      useAuthStore.getState().login({
        access: "jwt",
        user: {},
      });

      expect(broadcastLogin).toHaveBeenCalledTimes(1);
    });

    it("removes logged_out flag", () => {
      sessionStorage.setItem("logged_out", "true");

      useAuthStore.getState().login({
        access: "jwt",
        user: {},
      });

      expect(sessionStorage.getItem("logged_out")).toBeNull();
    });
  });

  // ────────────────────────────────────────────────────────────
  // setUser()
  // ────────────────────────────────────────────────────────────

  describe("setUser", () => {
    it("updates user after bootstrap/profile fetch", () => {
      const user = {
        id: 5,
        email: "profile@test.com",
      };

      useAuthStore.getState().setUser(user);

      const state = useAuthStore.getState();

      expect(state.user).toEqual(user);
      expect(state.isAuthenticated).toBe(true);
    });
  });

  // ────────────────────────────────────────────────────────────
  // setBootstrapping()
  // ────────────────────────────────────────────────────────────

  describe("setBootstrapping", () => {
    it("updates bootstrapping flag", () => {
      useAuthStore.getState().setBootstrapping(false);

      expect(useAuthStore.getState().isBootstrapping).toBe(false);
    });
  });

  // ────────────────────────────────────────────────────────────
  // logout()
  // ────────────────────────────────────────────────────────────

  describe("logout", () => {
    it("clears authenticated state", () => {
      useAuthStore.setState({
        user: { id: 1 },
        isAuthenticated: true,
      });

      useAuthStore.getState().logout();

      const state = useAuthStore.getState();

      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });

    it("clears auth helper", () => {
      useAuthStore.getState().logout();

      expect(clearAuth).toHaveBeenCalledTimes(1);
    });

    it("broadcasts logout", () => {
      useAuthStore.getState().logout();

      expect(broadcastLogout).toHaveBeenCalledTimes(1);
    });

    it("clears react-query cache", () => {
      useAuthStore.getState().logout();

      expect(queryClient.clear).toHaveBeenCalledTimes(1);
    });

    it("stores logged_out flag", () => {
      useAuthStore.getState().logout();

      expect(sessionStorage.getItem("logged_out")).toBe("true");
    });
  });
});
