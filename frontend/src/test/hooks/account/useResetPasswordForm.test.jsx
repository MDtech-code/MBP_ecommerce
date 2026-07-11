// src/test/hooks/account/useResetPasswordForm.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useResetPasswordForm } from "../../../hooks/account/useResetPasswordForm";

// ─────────────────────────────────────────────────────────────────────────────
// Mocks
// ─────────────────────────────────────────────────────────────────────────────

const navigate = vi.fn();
const mutate = vi.fn();

let hookState = {
  isPending: false,
  isError: false,
  error: null,
};

// searchParams controlled per test
let mockToken = "valid-reset-token";

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
  useSearchParams: () => [
    {
      get: (key) => (key === "token" ? mockToken : null),
    },
  ],
}));

vi.mock("../../../hooks/account/useAuthMutations", () => ({
  useConfirmPasswordReset: () => ({
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
    error: null,
  };

  mockToken = "valid-reset-token";
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("useResetPasswordForm", () => {
  it("starts with empty fields", () => {
    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    expect(result.current.fields).toEqual({
      password: "",
      confirm_password: "",
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.passwordError).toBeNull();
    expect(result.current.confirmPasswordError).toBeNull();
    expect(result.current.formError).toBeNull();
    expect(result.current.tokenMissing).toBe(false);
  });

  it("detects missing token from URL", () => {
    mockToken = null;

    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    expect(result.current.tokenMissing).toBe(true);
  });

  it("updates password field via handleChange", () => {
    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "password",
          value: "NewPass123!",
        },
      });
    });

    expect(result.current.fields.password).toBe(
      "NewPass123!",
    );
  });

  it("updates confirm_password field via handleChange", () => {
    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "confirm_password",
          value: "NewPass123!",
        },
      });
    });

    expect(result.current.fields.confirm_password).toBe(
      "NewPass123!",
    );
  });

  it("submits token and passwords on handleSubmit", () => {
    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: { name: "password", value: "NewPass123!" },
      });
      result.current.handleChange({
        target: {
          name: "confirm_password",
          value: "NewPass123!",
        },
      });
    });

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith(
      {
        token: "valid-reset-token",
        password: "NewPass123!",
        confirm_password: "NewPass123!",
      },
      expect.objectContaining({
        onSuccess: expect.any(Function),
      }),
    );
  });

  it("does not call mutate when token is missing", () => {
    mockToken = null;

    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    expect(mutate).not.toHaveBeenCalled();
  });

  it("navigates to /login with success message on success", () => {
    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    const options = mutate.mock.calls[0][1];

    act(() => {
      options.onSuccess();
    });

    expect(navigate).toHaveBeenCalledWith("/login", {
      state: {
        successMessage:
          "Password reset successfully. You can now log in.",
      },
      replace: true,
    });
  });

  it("exposes pending state", () => {
    hookState.isPending = true;

    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    expect(result.current.isPending).toBe(true);
  });

  it("maps password field error", () => {
    hookState.isError = true;
    hookState.error = {
  errors: {
    fields: { password: { message: "Password must be at least 8 characters.", code: "min_length" } },
    non_fields: null,
    code: "validation_error",
  },
};

    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    expect(result.current.passwordError).toBe(
      "Password must be at least 8 characters.",
    );
  });

  it("maps confirm_password field error", () => {
    hookState.isError = true;
    hookState.error = {
  errors: {
    fields: { confirm_password: { message: "Passwords do not match.", code: "password_mismatch" } },
    non_fields: null,
    code: "validation_error",
  },
};

    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    expect(result.current.confirmPasswordError).toBe(
      "Passwords do not match.",
    );
  });

  it("maps non_field_errors into formError", () => {
    hookState.isError = true;
    hookState.error = {
  errors: {
    fields: null,
    non_fields: { message: "Invalid or expired token.", code: "token_invalid" },
    code: "validation_error",
  },
};

    const { result } = renderHook(() =>
      useResetPasswordForm(),
    );

    expect(result.current.formError).toBe(
      "Invalid or expired token.",
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
      useResetPasswordForm(),
    );

    expect(result.current.formError).toBe(
      "Something went wrong.",
    );
  });
});