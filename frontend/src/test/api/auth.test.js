// src/test/api/auth.test.js

import { describe, it, expect, beforeEach, vi } from "vitest";
import { api } from "../../api/client";
import {
  setAuthToken,
  getAuthToken,
  hasAuthToken,
  clearAuth,
  broadcastLogin,
  broadcastLogout,
} from "../../api/auth";

describe("auth.js", () => {
  beforeEach(() => {
    clearAuth();
    localStorage.clear();
    vi.restoreAllMocks();
  });

  // ───────────────────────────────────────────────────────────────
  // setAuthToken
  // ───────────────────────────────────────────────────────────────

  describe("setAuthToken", () => {
    it("stores access token in memory", () => {
      setAuthToken("access-token");

      expect(getAuthToken()).toBe("access-token");
    });

    it("returns true from hasAuthToken when token exists", () => {
      setAuthToken("access-token");

      expect(hasAuthToken()).toBe(true);
    });

    it("adds Authorization header to axios instance", () => {
      setAuthToken("abc123");

      expect(api.defaults.headers.common.Authorization).toBe("Bearer abc123");
    });
  });

  // ───────────────────────────────────────────────────────────────
  // clearAuth
  // ───────────────────────────────────────────────────────────────

  describe("clearAuth", () => {
    it("removes token from memory", () => {
      setAuthToken("abc");

      clearAuth();

      expect(getAuthToken()).toBeNull();
    });

    it("returns false from hasAuthToken", () => {
      setAuthToken("abc");

      clearAuth();

      expect(hasAuthToken()).toBe(false);
    });

    it("removes Authorization header", () => {
      setAuthToken("abc");

      clearAuth();

      expect(api.defaults.headers.common.Authorization).toBeUndefined();
    });
  });

  // ───────────────────────────────────────────────────────────────
  // broadcastLogin
  // ───────────────────────────────────────────────────────────────

  describe("broadcastLogin", () => {
    it("writes LOGIN event into localStorage", () => {
      const spy = vi.spyOn(Storage.prototype, "setItem");

      broadcastLogin();

      expect(spy).toHaveBeenCalledTimes(1);

      expect(spy).toHaveBeenCalledWith("auth_event", expect.any(String));

      const payload = JSON.parse(spy.mock.calls[0][1]);

      expect(payload.type).toBe("LOGIN");
      expect(payload.time).toEqual(expect.any(Number));
    });
  });

  // ───────────────────────────────────────────────────────────────
  // broadcastLogout
  // ───────────────────────────────────────────────────────────────

  describe("broadcastLogout", () => {
    it("writes LOGOUT event into localStorage", () => {
      const spy = vi.spyOn(Storage.prototype, "setItem");

      broadcastLogout();

      expect(spy).toHaveBeenCalledTimes(1);

      expect(spy).toHaveBeenCalledWith("auth_event", expect.any(String));

      const payload = JSON.parse(spy.mock.calls[0][1]);

      expect(payload.type).toBe("LOGOUT");
      expect(payload.time).toEqual(expect.any(Number));
    });
  });
});
