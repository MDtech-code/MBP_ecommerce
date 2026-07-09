// src/test/hooks/account/useProfileForm.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useProfileForm } from "../../../hooks/account/useProfileForm";

// ─────────────────────────────────────────────────────────────────────────────
// Shared Mocks
// ─────────────────────────────────────────────────────────────────────────────

const mutate = vi.fn();

let hookState = {
  isPending: false,
  isError: false,
  error: null,
};

vi.mock("../../../hooks/account/useAuthMutations", () => ({
  useUpdateProfile: () => ({
    mutate,
    ...hookState,
  }),
}));

vi.mock("../../../stores/authStore", () => ({
  useAuthStore: (selector) =>
    selector({
      user: {
        id: 1,
        email: "john@test.com",
        profile: {
          phone: "03001234567",
          date_of_birth: "2000-01-01",
          gender: "Male",
        },
      },
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
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("useProfileForm", () => {
  it("initializes form using authenticated user profile", () => {
    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(result.current.form).toEqual({
      phone: "03001234567",
      date_of_birth: "2000-01-01",
      gender: "Male",
      
    });
  });

  it("starts with no validation errors", () => {
    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(result.current.formError).toBeNull();

    expect(result.current.fieldErrors).toEqual({
      phone: null,
      date_of_birth: null,
      gender: null,
      
    });
  });

  it("updates phone field", () => {
    const { result } = renderHook(() =>
      useProfileForm()
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "phone",
          value: "03111222333",
        },
      });
    });

    expect(result.current.form.phone).toBe(
      "03111222333"
    );
  });

  
  
  it("submits current form values", () => {
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useProfileForm(onSaveSuccess)
    );

    act(() => {
      result.current.handleSubmit({
        preventDefault: vi.fn(),
      });
    });

    expect(mutate).toHaveBeenCalledTimes(1);

    expect(mutate).toHaveBeenCalledWith(
      result.current.form,
      expect.objectContaining({
        onSuccess: expect.any(Function),
      })
    );
  });

  it("calls supplied success callback after successful update", () => {
    const onSaveSuccess = vi.fn();

    const { result } = renderHook(() =>
      useProfileForm(onSaveSuccess)
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

    expect(onSaveSuccess).toHaveBeenCalledTimes(1);
  });

  it("exposes pending state", () => {
    hookState.isPending = true;

    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(result.current.isPending).toBe(true);
  });

  it("maps form level errors", () => {
    hookState.isError = true;

    hookState.error = {
      errors: {
        non_field_errors: [
          "Unable to update profile.",
        ],
      },
    };

    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(result.current.formError).toBe(
      "Unable to update profile."
    );
  });

  it("maps phone validation errors", () => {
    hookState.isError = true;

    hookState.error = {
      errors: {
        phone: ["Invalid phone number."],
      },
    };

    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(result.current.fieldErrors.phone).toBe(
      "Invalid phone number."
    );
  });

 


});