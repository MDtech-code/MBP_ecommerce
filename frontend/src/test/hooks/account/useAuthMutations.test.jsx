// src/test/hooks/account/useAuthMutations.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRegister } from "../../../hooks/account/useAuthMutations";
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
