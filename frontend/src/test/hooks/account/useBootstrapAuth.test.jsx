// src/test/hooks/account/useBootstrapAuth.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useBootstrapAuth } from "../../../hooks/account/useBootstrapAuth";

// ─────────────────────────────────────────────────────────────────────────────
// Shared mocks
// ─────────────────────────────────────────────────────────────────────────────

// const bootstrap = vi.fn();
// const getProfile = vi.fn();
const {
  bootstrap,
  getProfile,
} = vi.hoisted(() => ({
  bootstrap: vi.fn(),
  getProfile: vi.fn(),
}));

const setUser = vi.fn();
const setBootstrapping = vi.fn();

let authState = {
  isAuthenticated: false,
};

const setAuthToken = vi.fn();

vi.mock("../../../services/accountService", () => ({
  accountService: {
    bootstrap,
    getProfile,
  },
}));

vi.mock("../../../api/auth", () => ({
  setAuthToken,
}));

vi.mock("../../../stores/authStore", () => ({
  useAuthStore: (selector) =>
    selector({
      isAuthenticated: authState.isAuthenticated,
      setUser,
      setBootstrapping,
    }),
}));

// ─────────────────────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  authState = {
    isAuthenticated: false,
  };

  sessionStorage.clear();
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("useBootstrapAuth", () => {
  it("restores access token and user profile", async () => {
    bootstrap.mockResolvedValue({
      data: {
        access: "new-access-token",
      },
    });

    getProfile.mockResolvedValue({
      data: {
        id: 1,
        email: "john@test.com",
      },
    });

    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(bootstrap).toHaveBeenCalledTimes(1);
    });

    expect(setAuthToken).toHaveBeenCalledWith(
      "new-access-token"
    );

    expect(getProfile).toHaveBeenCalledTimes(1);

    expect(setUser).toHaveBeenCalledWith({
      id: 1,
      email: "john@test.com",
    });

    expect(setBootstrapping).toHaveBeenLastCalledWith(
      false
    );
  });

  it("does not fetch profile when refresh returns no access token", async () => {
    bootstrap.mockResolvedValue({
      data: {},
    });

    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(bootstrap).toHaveBeenCalled();
    });

    expect(getProfile).not.toHaveBeenCalled();

    expect(setUser).not.toHaveBeenCalled();

    expect(setBootstrapping).toHaveBeenCalledWith(
      false
    );
  });

  it("finishes silently when refresh request fails", async () => {
    bootstrap.mockRejectedValue(
      new Error("Refresh failed")
    );

    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(bootstrap).toHaveBeenCalled();
    });

    expect(getProfile).not.toHaveBeenCalled();

    expect(setUser).not.toHaveBeenCalled();

    expect(setBootstrapping).toHaveBeenLastCalledWith(
      false
    );
  });

  it("skips bootstrap when already authenticated", async () => {
    authState.isAuthenticated = true;

    renderHook(() => useBootstrapAuth());

    expect(bootstrap).not.toHaveBeenCalled();

    expect(getProfile).not.toHaveBeenCalled();

    expect(setBootstrapping).toHaveBeenCalledWith(
      false
    );
  });

  it("skips bootstrap after explicit logout", () => {
    sessionStorage.setItem("logged_out", "true");

    renderHook(() => useBootstrapAuth());

    expect(bootstrap).not.toHaveBeenCalled();

    expect(getProfile).not.toHaveBeenCalled();

    expect(setBootstrapping).toHaveBeenCalledWith(
      false
    );
  });

  it("stores restored profile after successful bootstrap", async () => {
    const profile = {
      id: 7,
      email: "alice@test.com",
      profile: {
        phone: "03001234567",
      },
    };

    bootstrap.mockResolvedValue({
      data: {
        access: "jwt-token",
      },
    });

    getProfile.mockResolvedValue({
      data: profile,
    });

    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(setUser).toHaveBeenCalled();
    });

    expect(setUser).toHaveBeenCalledWith(profile);
  });

  it("always ends bootstrapping after successful restore", async () => {
    bootstrap.mockResolvedValue({
      data: {
        access: "token",
      },
    });

    getProfile.mockResolvedValue({
      data: {
        id: 1,
      },
    });

    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(setBootstrapping).toHaveBeenLastCalledWith(
        false
      );
    });
  });

  it("always ends bootstrapping after failed restore", async () => {
    bootstrap.mockRejectedValue(
      new Error("Network Error")
    );

    renderHook(() => useBootstrapAuth());

    await waitFor(() => {
      expect(setBootstrapping).toHaveBeenLastCalledWith(
        false
      );
    });
  });
});