// src/test/hooks/account/useForgotPasswordForm.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useForgotPasswordForm } from "../../../hooks/account/useForgotPasswordForm";

// ─────────────────────────────────────────────────────────────────────────────
// Mocks
// ─────────────────────────────────────────────────────────────────────────────

const navigate = vi.fn();
const mutate = vi.fn();

let hookState = {
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
};

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
}));

vi.mock("../../../hooks/account/useAuthMutations", () => ({
  useRequestPasswordReset: () => ({
    mutate,
    ...hookState,
  }),
}));

vi.mock("../../../api/transformers", () => ({
  normalizeError: vi.fn((error) => error),
}));

// ─────────────────────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  hookState = {
    isPending: false,
    isError: false,
    isSuccess: false,
    error: null,
  };
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("useForgotPasswordForm", () => {
  it("starts with empty email", () => {
    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    expect(result.current.email).toBe("");
    expect(result.current.isPending).toBe(false);
    expect(result.current.emailError).toBeNull();
    expect(result.current.formError).toBeNull();
  });

  it("updates email field via handleEmailChange", () => {
    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    act(() => {
      result.current.handleEmailChange({
        target: { value: "john@test.com" },
      });
    });

    expect(result.current.email).toBe("john@test.com");
  });

  it("calls mutate with email on submit", () => {
    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    act(() => {
      result.current.handleEmailChange({
        target: { value: "john@test.com" },
      });
    });

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith(
      { email: "john@test.com" },
      expect.objectContaining({
        onSuccess: expect.any(Function),
      }),
    );
  });

  it("navigates to /forgot-password/sent with email state on success", () => {
    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    act(() => {
      result.current.handleEmailChange({
        target: { value: "john@test.com" },
      });
    });

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    const options = mutate.mock.calls[0][1];

    act(() => {
      options.onSuccess();
    });

    expect(navigate).toHaveBeenCalledWith(
      "/forgot-password/sent",
      {
        state: { email: "john@test.com" },
        replace: true,
      },
    );
  });

  it("exposes pending state", () => {
    hookState.isPending = true;

    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    expect(result.current.isPending).toBe(true);
  });

  it("maps email field error", () => {
    hookState.isError = true;
   hookState.error = {
  errors: {
    fields: { email: { message: "Enter a valid email address.", code: "invalid" } },
    non_fields: null,
    code: "validation_error",
  },
};

    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    expect(result.current.emailError).toBe(
      "Enter a valid email address.",
    );
  });

  it("maps non_field_errors into formError", () => {
    hookState.isError = true;
    hookState.error = {
  errors: {
    fields: null,
    non_fields: { message: "Too many requests. Try again later.", code: "rate_limit_exceeded" },
    code: "rate_limit_exceeded",
  },
};

    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    expect(result.current.formError).toBe(
      "Too many requests. Try again later.",
    );
  });

  it("falls back to message when no non_field_errors", () => {
    hookState.isError = true;
    hookState.error = {
  errors: {
    fields: null,
    non_fields: null,
    code: "validation_error",
  },
  message: "Something went wrong.",
};

    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    expect(result.current.formError).toBe(
      "Something went wrong.",
    );
  });

  it("does not navigate when not successful", () => {
    const { result } = renderHook(() =>
      useForgotPasswordForm(),
    );

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    // mutate was called but onSuccess was never triggered
    expect(navigate).not.toHaveBeenCalled();
  });
});