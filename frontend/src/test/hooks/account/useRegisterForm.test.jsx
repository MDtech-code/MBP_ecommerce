// src/test/hooks/account/useRegisterForm.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRegisterForm } from "../../../hooks/account/useRegisterForm";
import { accountService } from "../../../services/accountService";
import { ErrorCode } from "../../../api/transformers";


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

// ─── Mock error builder ───────────────────────────────────────────────────────

/**
 * Builds a mock axios error with the NEW structured errors envelope.
 *
 * Always use this helper in tests — never build raw error objects inline.
 * If the backend contract changes, update this one place only.
 *
 * @param {object} options
 * @param {number}      options.status      - HTTP status code
 * @param {string}      options.message     - top-level human readable message
 * @param {object|null} options.fields      - field errors {field: {message, code}}
 * @param {object|null} options.nonFields   - non-field error {message, code}
 * @param {string}      options.errorCode   - top-level errors.code
 */
const makeMockError = ({
  status = 400,
  message = "Request failed.",
  fields = null,
  nonFields = null,
  errorCode = ErrorCode.VALIDATION_ERROR,
} = {}) => {
  const error = new Error(message);
  error.response = {
    status,
    data: {
      success: false,
      message,
      data: null,
      errors: {
        code: errorCode,
        fields,
        non_fields: nonFields,
      },
      meta: { request_id: "test-request-id" },
    },
  };
  return error;
};

// ─── useRegisterForm ──────────────────────────────────────────────────────────

describe("useRegisterForm", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── Initial state ──────────────────────────────────────────────────────────

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

  it("returns null field errors initially", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.fieldErrors).toEqual({
      full_name: null,
      email: null,
      password: null,
      confirm_password: null,
    });
  });

  it("returns null formError initially", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.formError).toBeNull();
  });

  it("isPending is false initially", () => {
    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });
    expect(result.current.isPending).toBe(false);
  });

  // ── handleChange ───────────────────────────────────────────────────────────

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
        target: { name: "full_name", value: "John Doe" },
      });
    });

    act(() => {
      result.current.handleChange({
        target: { name: "email", value: "john@test.com" },
      });
    });

    expect(result.current.form.full_name).toBe("John Doe");
    expect(result.current.form.email).toBe("john@test.com");
    expect(result.current.form.password).toBe("");
    expect(result.current.form.confirm_password).toBe("");
  });

  // ── Success flow ───────────────────────────────────────────────────────────

  it("navigates to /verify-email on successful registration", async () => {
    accountService.register.mockResolvedValue({
      data: { email: "john@test.com" },
      message: "Account created successfully.",
      meta: { request_id: "abc" },
    });

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/verify-email");
    });
  });

  it("stores email in localStorage on successful registration", async () => {
    const setItemSpy = vi.spyOn(Storage.prototype, "setItem");

    accountService.register.mockResolvedValue({
      data: { email: "john@test.com" },
      message: "Account created successfully.",
      meta: null,
    });

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "email", value: "john@test.com" },
      });
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(setItemSpy).toHaveBeenCalledWith(
        "pending_verification_email",
        "john@test.com"
      );
    });
  });

  // ── Field error flow ───────────────────────────────────────────────────────

  it("exposes field error messages from errors.fields", async () => {
    /**
     * Backend sends NEW structured shape:
     * errors.fields.{field}.message → fieldErrors.{field}
     *
     * OLD: errors.full_name[0] → fieldErrors.full_name
     * NEW: errors.fields.full_name.message → fieldErrors.full_name
     */
    accountService.register.mockRejectedValue(
      makeMockError({
        fields: {
          full_name: {
            message: "Please enter your full name (first and last name).",
            code: ErrorCode.INVALID_FULL_NAME,
          },
          password: {
            message: "Password must be at least 8 characters.",
            code: "min_length",
          },
        },
      })
    );

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.fieldErrors.full_name).toBe(
        "Please enter your full name (first and last name)."
      );
      expect(result.current.fieldErrors.password).toBe(
        "Password must be at least 8 characters."
      );
    });
  });

  it("exposes null for fields with no error", async () => {
    /**
     * When only email has an error, other fields must be null.
     * The hook must not carry over errors from previous submissions.
     */
    accountService.register.mockRejectedValue(
      makeMockError({
        fields: {
          email: {
            message: "An account with this email already exists.",
            code: ErrorCode.EMAIL_ALREADY_EXISTS,
          },
        },
      })
    );

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.fieldErrors.email).toBe(
        "An account with this email already exists."
      );
      // Other fields must be null — not undefined, not ""
      expect(result.current.fieldErrors.full_name).toBeNull();
      expect(result.current.fieldErrors.password).toBeNull();
      expect(result.current.fieldErrors.confirm_password).toBeNull();
    });
  });

  it("exposes confirm_password field error for password mismatch", async () => {
    accountService.register.mockRejectedValue(
      makeMockError({
        fields: {
          confirm_password: {
            message: "Passwords do not match.",
            code: ErrorCode.PASSWORD_MISMATCH,
          },
        },
      })
    );

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.fieldErrors.confirm_password).toBe(
        "Passwords do not match."
      );
    });
  });



  it("formError is null when errors.non_fields is null", async () => {
    /**
     * When only field errors exist, formError must be null.
     * Non-field banner must not appear for field-level errors.
     */
    accountService.register.mockRejectedValue(
      makeMockError({
        fields: {
          email: {
            message: "Email required.",
            code: "required",
          },
        },
        nonFields: null,
      })
    );

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.formError).toBeNull();
    });
  });

  // ── Network error ──────────────────────────────────────────────────────────

  it("exposes network error message when no response", async () => {
    /**
     * Network errors have no response object — normalizeError handles this
     * by returning a specific message with errors=null.
     * formError picks up normalized.message as fallback.
     *
     * Note: fieldErrors all remain null on network error
     * because errors.fields does not exist.
     */
    const networkError = new Error("Network Error");
    // No .response property — simulates offline/timeout
    accountService.register.mockRejectedValue(networkError);

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      // All field errors must be null
      expect(result.current.fieldErrors.email).toBeNull();
      expect(result.current.fieldErrors.full_name).toBeNull();
    });
  });

  // ── Navigation guard ───────────────────────────────────────────────────────

  it("does not navigate on validation error", async () => {
    accountService.register.mockRejectedValue(
      makeMockError({
        fields: {
          email: {
            message: "An account with this email already exists.",
            code: ErrorCode.EMAIL_ALREADY_EXISTS,
          },
        },
      })
    );

    const { result } = renderHook(() => useRegisterForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    await waitFor(() => {
      expect(result.current.fieldErrors.email).toBe(
        "An account with this email already exists."
      );
    });

    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
