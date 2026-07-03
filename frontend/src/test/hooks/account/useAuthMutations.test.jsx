// src/test/hooks/account/useAuthMutations.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRegister,useVerifyEmail,useResendVerification } from "../../../hooks/account/useAuthMutations";
import { accountService } from "../../../services/accountService";

// Mock service layer
vi.mock("../../../services/accountService", () => ({
  accountService: {
    register: vi.fn(),
  },
}));

// Wrapper providing QueryClient to hooks
const makeWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      mutations: { retry: false },
    },
  });

  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ─── useRegister ──────────────────────────────────────────────────────────────

describe("useRegister", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useRegister(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.isError).toBe(false);
    expect(result.current.isSuccess).toBe(false);
  });

  it("calls accountService.register with correct payload", async () => {
    const payload = {
      full_name: "John Doe",
      email: "john@test.com",
      password: "password123",
      confirm_password: "password123",
    };

    accountService.register.mockResolvedValue({
      data: { user: { id: 1 } },
      message: "Registration successful.",
      meta: { request_id: "abc" },
    });

    const { result } = renderHook(() => useRegister(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate(payload);
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(accountService.register).toHaveBeenCalledWith(payload, expect.anything())
  });

  it("exposes error when service rejects", async () => {
    const mockError = new Error("Request failed");
    mockError.response = {
      status: 400,
      data: {
        message: "Registration failed.",
        errors: { email: ["Already registered."] },
        meta: { request_id: "abc" },
      },
    };

    accountService.register.mockRejectedValue(mockError);

    const { result } = renderHook(() => useRegister(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({
        full_name: "John",
        email: "john@test.com",
        password: "pass1234",
        confirm_password: "pass1234",
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(mockError);
  });
});



// ADD to src/test/hooks/account/useAuthMutations.test.jsx

// Add to mock at top
vi.mock("../../../services/accountService", () => ({
  accountService: {
    register: vi.fn(),
    verifyEmail: vi.fn(),           // ← add
    resendVerification: vi.fn(),    // ← add
  },
}))

// ─── useVerifyEmail ───────────────────────────────────────────────────────────

describe("useVerifyEmail", () => {

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in idle state", () => {
    const { result } = renderHook(() => useVerifyEmail(), {
      wrapper: makeWrapper(),
    })

    expect(result.current.isPending).toBe(false)
    expect(result.current.isError).toBe(false)
    expect(result.current.isSuccess).toBe(false)
  })

  it("calls accountService.verifyEmail with token payload", async () => {
    accountService.verifyEmail.mockResolvedValue({
      data: null,
      message: "Email verified successfully.",
      meta: null,
    })

    const { result } = renderHook(() => useVerifyEmail(), {
      wrapper: makeWrapper(),
    })

    act(() => {
      result.current.mutate({ token: "test-token-123" })
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(accountService.verifyEmail).toHaveBeenCalledWith(
      { token: "test-token-123" },
      expect.anything()
    )
  })

  it("exposes error when token is invalid", async () => {
    const mockError = new Error("Invalid token")
    mockError.response = {
      status: 400,
      data: {
        message: "Invalid or expired token.",
        errors: { non_field_errors: ["Invalid or expired token."] },
        meta: null,
      },
    }

    accountService.verifyEmail.mockRejectedValue(mockError)

    const { result } = renderHook(() => useVerifyEmail(), {
      wrapper: makeWrapper(),
    })

    act(() => {
      result.current.mutate({ token: "bad-token" })
    })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBe(mockError)
  })

})

// ─── useResendVerification ────────────────────────────────────────────────────

describe("useResendVerification", () => {

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("starts in idle state", () => {
    const { result } = renderHook(() => useResendVerification(), {
      wrapper: makeWrapper(),
    })

    expect(result.current.isPending).toBe(false)
    expect(result.current.isError).toBe(false)
    expect(result.current.isSuccess).toBe(false)
  })

  it("calls accountService.resendVerification with email", async () => {
    accountService.resendVerification.mockResolvedValue({
      data: null,
      message: "Verification email sent.",
      meta: null,
    })

    const { result } = renderHook(() => useResendVerification(), {
      wrapper: makeWrapper(),
    })

    act(() => {
      result.current.mutate({ email: "john@test.com" })
    })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(accountService.resendVerification).toHaveBeenCalledWith(
      { email: "john@test.com" },
      expect.anything()
    )
  })

})