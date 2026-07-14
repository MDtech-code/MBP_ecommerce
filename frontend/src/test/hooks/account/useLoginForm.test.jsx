// src/test/hooks/account/useLoginForm.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useLoginForm } from "../../../hooks/account/useLoginForm";
import { ErrorCode } from "../../../api/transformers";

// ─── Mocks ────────────────────────────────────────────────────────────────────

const navigate    = vi.fn();
const loginMutate = vi.fn();
const resendMutate = vi.fn();

let loginHookState = {
  isPending: false,
  isError:   false,
  error:     null,
};

let resendHookState = {
  isPending: false,
  isError:   false,
  isSuccess: false,
};

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
}));

// Mock useAuthMutations — both useLogin AND useResendVerification
vi.mock("../../../hooks/account/useAuthMutations", () => ({
  useLogin: () => ({
    mutate: loginMutate,
    ...loginHookState,
  }),
  useResendVerification: () => ({
    mutate:    resendMutate,
    ...resendHookState,
  }),
}));

// ─── Error builder ────────────────────────────────────────────────────────────

/**
 * Builds a normalized error object matching what normalizeError() returns.
 * useLoginForm calls normalizeError(error) and reads the result.
 * We mock normalizeError to return this shape directly.
 */
const makeNormalizedError = ({
  fields     = null,
  nonFields  = null,
  errorCode  = ErrorCode.VALIDATION_ERROR,
  message    = "Request failed.",
} = {}) => ({
  message,
  status:         400,
  requestId:      null,
  errors: {
    code:       errorCode,
    fields,
    non_fields: nonFields,
  },
  isNetworkError: false,
  isClientError:  true,
  isServerError:  false,
  isAuthError:    false,
  isForbidden:    false,
  isNotFound:     false,
  isRateLimit:    false,
});

// Mock normalizeError — returns structured shape directly
// so hook tests are not coupled to normalizeError's internal logic
vi.mock("../../../api/transformers", () => ({
  normalizeError: vi.fn((error) => error),
  ErrorCode: {
    INVALID_CREDENTIALS:  "invalid_credentials",
    EMAIL_NOT_VERIFIED:   "email_not_verified",
    ACCOUNT_INACTIVE:     "account_inactive",
    VALIDATION_ERROR:     "validation_error",
    AUTHENTICATION_ERROR: "authentication_error",
  },
}));

// ─── Reset ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();

  loginHookState = {
    isPending: false,
    isError:   false,
    error:     null,
  };

  resendHookState = {
    isPending: false,
    isError:   false,
    isSuccess: false,
  };
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("useLoginForm", () => {

  // ── Initial state ──────────────────────────────────────────────────────────

  it("starts with empty form", () => {
    const { result } = renderHook(() => useLoginForm());

    expect(result.current.form).toEqual({ email: "", password: "" });
    expect(result.current.formError).toBeNull();
    expect(result.current.formErrorCode).toBeNull();
    expect(result.current.fieldErrors).toEqual({ email: null, password: null });
    expect(result.current.isPending).toBe(false);
  });

  // ── handleChange ───────────────────────────────────────────────────────────

  it("updates email field", () => {
    const { result } = renderHook(() => useLoginForm());

    act(() => {
      result.current.handleChange({ target: { name: "email", value: "john@test.com" } });
    });

    expect(result.current.form.email).toBe("john@test.com");
  });

  it("updates password field", () => {
    const { result } = renderHook(() => useLoginForm());

    act(() => {
      result.current.handleChange({ target: { name: "password", value: "secret123" } });
    });

    expect(result.current.form.password).toBe("secret123");
  });

  it("updates only changed field — leaves others intact", () => {
    const { result } = renderHook(() => useLoginForm());

    act(() => {
      result.current.handleChange({ target: { name: "email", value: "john@test.com" } });
    });
    act(() => {
      result.current.handleChange({ target: { name: "password", value: "secret123" } });
    });

    expect(result.current.form.email).toBe("john@test.com");
    expect(result.current.form.password).toBe("secret123");
  });

  // ── handleSubmit ───────────────────────────────────────────────────────────

  it("submits current form values to login mutate", () => {
    const { result } = renderHook(() => useLoginForm());

    act(() => {
      result.current.handleChange({ target: { name: "email",    value: "john@test.com" } });
      result.current.handleChange({ target: { name: "password", value: "password123"  } });
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(loginMutate).toHaveBeenCalledTimes(1);
    expect(loginMutate).toHaveBeenCalledWith(
      { email: "john@test.com", password: "password123" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("navigates to /profile after successful login", () => {
    const { result } = renderHook(() => useLoginForm());

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    const onSuccess = loginMutate.mock.calls[0][1].onSuccess;
    act(() => { onSuccess(); });

    expect(navigate).toHaveBeenCalledWith("/profile");
  });

  // ── isPending ──────────────────────────────────────────────────────────────

  it("exposes isPending from useLogin", () => {
    loginHookState.isPending = true;
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.isPending).toBe(true);
  });

  // ── Error reading — new shape ──────────────────────────────────────────────

  it("reads formError from errors.non_fields.message", () => {
    /**
     * normalizeError is mocked to return its input directly.
     * We set hookState.error to the already-normalized shape
     * that the hook reads from: errors.non_fields.message
     *
     * OLD shape the hook used to read:
     *   errors.non_field_errors[0]
     * NEW shape:
     *   errors.non_fields.message
     */
    loginHookState.isError = true;
    loginHookState.error   = makeNormalizedError({
      nonFields: {
        message: "Invalid email or password.",
        code:    ErrorCode.INVALID_CREDENTIALS,
      },
    });

    const { result } = renderHook(() => useLoginForm());

    expect(result.current.formError).toBe("Invalid email or password.");
  });

  it("reads formErrorCode from errors.non_fields.code", () => {
    loginHookState.isError = true;
    loginHookState.error   = makeNormalizedError({
      nonFields: {
        message: "Please verify your email address before logging in.",
        code:    ErrorCode.EMAIL_NOT_VERIFIED,
      },
    });

    const { result } = renderHook(() => useLoginForm());

    expect(result.current.formErrorCode).toBe(ErrorCode.EMAIL_NOT_VERIFIED);
  });

  it("reads fieldErrors from errors.fields.{field}.message", () => {
    /**
     * OLD shape: errors.email[0]
     * NEW shape: errors.fields.email.message
     */
    loginHookState.isError = true;
    loginHookState.error   = makeNormalizedError({
      fields: {
        email:    { message: "Email address is required.", code: "required" },
        password: { message: "Password is required.",     code: "required" },
      },
    });

    const { result } = renderHook(() => useLoginForm());

    expect(result.current.fieldErrors.email).toBe("Email address is required.");
    expect(result.current.fieldErrors.password).toBe("Password is required.");
  });

  it("returns null fieldErrors when no field errors present", () => {
    loginHookState.isError = true;
    loginHookState.error   = makeNormalizedError({
      nonFields: {
        message: "Invalid email or password.",
        code:    ErrorCode.INVALID_CREDENTIALS,
      },
    });

    const { result } = renderHook(() => useLoginForm());

    expect(result.current.fieldErrors.email).toBeNull();
    expect(result.current.fieldErrors.password).toBeNull();
  });

  it("returns null formError when no error", () => {
    loginHookState.isError = false;
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.formError).toBeNull();
    expect(result.current.formErrorCode).toBeNull();
  });

  // ── handleResend ───────────────────────────────────────────────────────────

  it("calls resendVerification with email from localStorage", () => {
    localStorage.setItem("pending_verification_email", "john@test.com");

    const { result } = renderHook(() => useLoginForm());

    act(() => { result.current.handleResend(); });

    expect(resendMutate).toHaveBeenCalledWith(
      { email: "john@test.com" },
    );
  });

  it("falls back to form.email when localStorage is empty", () => {
    const { result } = renderHook(() => useLoginForm());

    act(() => {
      result.current.handleChange({ target: { name: "email", value: "typed@test.com" } });
    });

    act(() => { result.current.handleResend(); });

    expect(resendMutate).toHaveBeenCalledWith(
      { email: "typed@test.com" },
      
    );
  });

  it("does not call resendVerification when email is empty", () => {
    const { result } = renderHook(() => useLoginForm());
    // No localStorage, no form email typed
    act(() => { result.current.handleResend(); });
    expect(resendMutate).not.toHaveBeenCalled();
  });

  it("exposes isResending from useResendVerification", () => {
    resendHookState.isPending = true;
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.isResending).toBe(true);
  });

  it("exposes isResendSuccess from useResendVerification", () => {
    resendHookState.isSuccess = true;
    const { result } = renderHook(() => useLoginForm());
    expect(result.current.isResendSuccess).toBe(true);
  });
});
