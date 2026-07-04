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
          address_line1: "Street 1",
          address_line2: "House 5",
          city: "Lahore",
          province: "Punjab",
          postal_code: "54000",
          country: "Pakistan",
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
      address_line1: "Street 1",
      address_line2: "House 5",
      city: "Lahore",
      province: "Punjab",
      postal_code: "54000",
      country: "Pakistan",
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
      address_line1: null,
      address_line2: null,
      city: null,
      province: null,
      postal_code: null,
      country: null,
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

  it("updates city field", () => {
    const { result } = renderHook(() =>
      useProfileForm()
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "city",
          value: "Islamabad",
        },
      });
    });

    expect(result.current.form.city).toBe(
      "Islamabad"
    );
  });

  it("updates country field", () => {
    const { result } = renderHook(() =>
      useProfileForm()
    );

    act(() => {
      result.current.handleChange({
        target: {
          name: "country",
          value: "Turkey",
        },
      });
    });

    expect(result.current.form.country).toBe(
      "Turkey"
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

  it("maps postal code validation errors", () => {
    hookState.isError = true;

    hookState.error = {
      errors: {
        postal_code: ["Invalid postal code."],
      },
    };

    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(
      result.current.fieldErrors.postal_code
    ).toBe("Invalid postal code.");
  });

  it("maps country validation errors", () => {
    hookState.isError = true;

    hookState.error = {
      errors: {
        country: ["Country is required."],
      },
    };

    const { result } = renderHook(() =>
      useProfileForm()
    );

    expect(result.current.fieldErrors.country).toBe(
      "Country is required."
    );
  });
});