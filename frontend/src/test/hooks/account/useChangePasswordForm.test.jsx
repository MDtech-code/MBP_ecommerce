// src/test/hooks/account/useChangePasswordForm.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useChangePasswordForm } from "../../../hooks/account/useChangePasswordForm";

// ─────────────────────────────────────────────────────────────────────────────
// Mocks
// ─────────────────────────────────────────────────────────────────────────────

const mutate = vi.fn();

let hookState = {
  isPending: false,
  isError: false,
  isSuccess: false,
  error: null,
};

vi.mock("../../../hooks/account/useAuthMutations", () => ({
  useChangePassword: () => ({
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

describe("useChangePasswordForm", () => {
  it("starts with empty fields", () => {
    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.fields).toEqual({
      current_password: "",
      new_password: "",
      confirm_new_password: "",
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.currentPasswordError).toBeNull();
    expect(result.current.newPasswordError).toBeNull();
    expect(result.current.confirmNewPasswordError).toBeNull();
    expect(result.current.formError).toBeNull();
  });

  it("updates current_password field via handleChange", () => {
    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "current_password",
          value: "OldPass123!",
        },
      });
    });

    expect(result.current.fields.current_password).toBe(
      "OldPass123!",
    );
  });

  it("updates new_password field via handleChange", () => {
    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "new_password",
          value: "NewPass456!",
        },
      });
    });

    expect(result.current.fields.new_password).toBe(
      "NewPass456!",
    );
  });

  it("updates confirm_new_password field via handleChange", () => {
    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "confirm_new_password",
          value: "NewPass456!",
        },
      });
    });

    expect(result.current.fields.confirm_new_password).toBe(
      "NewPass456!",
    );
  });

  it("submits all three fields on handleSubmit", () => {
    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "current_password",
          value: "OldPass123!",
        },
      });
      result.current.handleChange({
        target: {
          name: "new_password",
          value: "NewPass456!",
        },
      });
      result.current.handleChange({
        target: {
          name: "confirm_new_password",
          value: "NewPass456!",
        },
      });
    });

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    expect(mutate).toHaveBeenCalledTimes(1);
    expect(mutate).toHaveBeenCalledWith({
      current_password: "OldPass123!",
      new_password: "NewPass456!",
      confirm_new_password: "NewPass456!",
    });
  });

  it("exposes pending state", () => {
    hookState.isPending = true;

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.isPending).toBe(true);
  });

  it("exposes success state", () => {
    hookState.isSuccess = true;

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.isSuccess).toBe(true);
  });

  it("maps current_password field error", () => {
    hookState.isError = true;
    hookState.error = {
      errors: {
        current_password: ["Current password is incorrect."],
      },
    };

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.currentPasswordError).toBe(
      "Current password is incorrect.",
    );
  });

  it("maps new_password field error", () => {
    hookState.isError = true;
    hookState.error = {
      errors: {
        new_password: [
          "Password must be at least 8 characters.",
        ],
      },
    };

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.newPasswordError).toBe(
      "Password must be at least 8 characters.",
    );
  });

  it("maps confirm_new_password field error", () => {
    hookState.isError = true;
    hookState.error = {
      errors: {
        confirm_new_password: ["Passwords do not match."],
      },
    };

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.confirmNewPasswordError).toBe(
      "Passwords do not match.",
    );
  });

  it("maps non_field_errors into formError", () => {
    hookState.isError = true;
    hookState.error = {
      errors: {
        non_field_errors: ["Current password is incorrect."],
      },
    };

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.formError).toBe(
      "Current password is incorrect.",
    );
  });

  it("falls back to message when no non_field_errors", () => {
    hookState.isError = true;
    hookState.error = {
      errors: {},
      message: "Something went wrong.",
    };

    const { result } = renderHook(() =>
      useChangePasswordForm(),
    );

    expect(result.current.formError).toBe(
      "Something went wrong.",
    );
  });
});