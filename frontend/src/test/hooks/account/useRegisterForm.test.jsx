// src/test/hooks/account/useRegisterForm.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRegisterForm } from "../../../hooks/account/useRegisterForm";
import { accountService } from "../../../services/accountService";

// Mock service
vi.mock("../../../services/accountService", () => ({
  accountService: {
    register: vi.fn(),
  },
}));

// Mock react-router-dom navigate
const mockNavigate = vi.fn();
vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
}));

const makeWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ─── useRegisterForm ──────────────────────────────────────────────────────────

describe("useRegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Initial state ─────────────────────────────────────────────────────────

  it("returns empty form state initially", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.form).toEqual({
      full_name: "",
      email: "",
      password: "",
      confirm_password: "",
    });
  });

  it("returns no errors initially", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.fieldErrors).toEqual({
      full_name: null,
      email: null,
      password: null,
      confirm_password: null,
    });
    expect(result.current.formError).toBeNull();
  });

  it("isPending is false initially", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });
    expect(result.current.isPending).toBe(false);
  });

  // ── handleChange ──────────────────────────────────────────────────────────

  it("updates form field when handleChange is called", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "email", value: "john@test.com" },
      });
    });

    expect(result.current.form.email).toBe("john@test.com");
  });

  it("updates only the changed field, leaves others intact", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "full_name", value: "John" },
      });
    });

    act(() => {
      result.current.handleChange({
        target: { name: "email", value: "john@test.com" },
      });
    });

    expect(result.current.form.full_name).toBe("John");
    expect(result.current.form.email).toBe("john@test.com");
    expect(result.current.form.password).toBe("");
    expect(result.current.form.confirm_password).toBe("");
  });

  // ── Success flow ──────────────────────────────────────────────────────────

  it("navigates to /verify-email on successful registration", async () => {
    accountService.register.mockResolvedValue({
      data: { user: { id: 1 } },
      message: "Registration successful.",
      meta: { request_id: "abc" },
    });

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/verify-email");
    });
  });

  // ── Error flow ────────────────────────────────────────────────────────────

  it("exposes field errors from backend on validation failure", async () => {
    const mockError = new Error("Validation failed");
    mockError.response = {
      status: 400,
      data: {
        success: false,
        message: "Registration failed.",
        data: null,
        errors: {
          full_name: ["This field is required."],
          password: ["Password must be at least 8 characters."],
        },
        meta: { request_id: "abc" },
      },
    };

    accountService.register.mockRejectedValue(mockError);

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.fieldErrors.full_name).toBe(
        "This field is required.",
      );
      expect(result.current.fieldErrors.password).toBe(
        "Password must be at least 8 characters.",
      );
    });
  });

  it("exposes formError for non_field_errors", async () => {
    const mockError = new Error("Login failed");
    mockError.response = {
      status: 400,
      data: {
        success: false,
        message: "Failed.",
        data: null,
        errors: {
          non_field_errors: ["An account already exists with this email."],
        },
        meta: { request_id: "abc" },
      },
    };

    accountService.register.mockRejectedValue(mockError);

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.formError).toBe(
        "An account already exists with this email.",
      );
    });
  });

  it("does not navigate on error", async () => {
    const mockError = new Error("Failed");
    mockError.response = {
      status: 400,
      data: {
        message: "Failed.",
        errors: { email: ["Required."] },
        meta: null,
      },
    };

    accountService.register.mockRejectedValue(mockError);

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.fieldErrors.email).toBe("Required.");
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
