// src/test/hooks/account/useAuthMutations.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRegister,useVerifyEmail,useResendVerification,useLogin,useLogout,useProfile,useUpdateProfile,useUploadAvatar } from "../../../hooks/account/useAuthMutations";
import { accountService } from "../../../services/accountService";



const mockLogin = vi.fn();
const mockLogout = vi.fn();
const mockSetUser = vi.fn();
const { invalidateQueries } = vi.hoisted(() => ({
  invalidateQueries: vi.fn(),
}));



// Mock service layer
vi.mock("../../../services/accountService", () => ({
  accountService: {
    register: vi.fn(),
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
    login: vi.fn(),
    logout: vi.fn(),
    getProfile: vi.fn(),
    updateProfile: vi.fn(),
    uploadAvatar: vi.fn(),
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





vi.mock("../../../stores/authStore", () => ({
  useAuthStore: (selector) =>
    selector({
      login: mockLogin,
      logout: mockLogout,
      setUser: mockSetUser,
      user: {
        id: 1,
        email: "john@test.com",
        profile: {
          avatar: "/old-avatar.jpg",
        },
      },
    }),
}));



vi.mock("../../../lib/queryClient", () => ({
  queryClient: {
    invalidateQueries,
  },
}));

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



describe("useLogin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useLogin(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
  });

  it("calls accountService.login", async () => {
    const payload = {
      email: "john@test.com",
      password: "password123",
    };

    accountService.login.mockResolvedValue({
      data: {
        access: "jwt-token",
        user: { id: 1 },
      },
    });

    const { result } = renderHook(() => useLogin(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate(payload);
    });

    await waitFor(() =>
      expect(result.current.isSuccess).toBe(true),
    );

    expect(accountService.login).toHaveBeenCalledWith(payload);
  });

  it("stores authenticated user", async () => {
    accountService.login.mockResolvedValue({
      data: {
        access: "jwt",
        user: {
          id: 1,
        },
      },
    });

    const { result } = renderHook(() => useLogin(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({
        email: "john@test.com",
        password: "password123",
      });
    });

    await waitFor(() =>
      expect(mockLogin).toHaveBeenCalledWith({
        access: "jwt",
        user: {
          id: 1,
        },
      }),
    );
  });
});





describe("useLogin", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("starts in idle state", () => {
    const { result } = renderHook(() => useLogin(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isPending).toBe(false);
    expect(result.current.isSuccess).toBe(false);
  });

  it("calls accountService.login", async () => {
    const payload = {
      email: "john@test.com",
      password: "password123",
    };

    accountService.login.mockResolvedValue({
      data: {
        access: "jwt-token",
        user: { id: 1 },
      },
    });

    const { result } = renderHook(() => useLogin(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate(payload);
    });

    await waitFor(() =>
      expect(result.current.isSuccess).toBe(true),
    );

    expect(accountService.login).toHaveBeenCalledWith(payload);
  });

  it("stores authenticated user", async () => {
    accountService.login.mockResolvedValue({
      data: {
        access: "jwt",
        user: {
          id: 1,
        },
      },
    });

    const { result } = renderHook(() => useLogin(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({
        email: "john@test.com",
        password: "password123",
      });
    });

    await waitFor(() =>
      expect(mockLogin).toHaveBeenCalledWith({
        access: "jwt",
        user: {
          id: 1,
        },
      }),
    );
  });
});



describe("useLogout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls logout service", async () => {
    accountService.logout.mockResolvedValue({});

    const { result } = renderHook(() => useLogout(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() =>
      expect(accountService.logout).toHaveBeenCalled(),
    );
  });

  it("clears auth store after successful logout", async () => {
    accountService.logout.mockResolvedValue({});

    const { result } = renderHook(() => useLogout(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() =>
      expect(mockLogout).toHaveBeenCalled(),
    );
  });

  it("still clears auth when request fails", async () => {
    accountService.logout.mockRejectedValue(
      new Error("Network"),
    );

    const { result } = renderHook(() => useLogout(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() =>
      expect(result.current.isError).toBe(true),
    );

    expect(mockLogout).toHaveBeenCalled();
  });
});





describe("useProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("fetches profile", async () => {
    accountService.getProfile.mockResolvedValue({
      data: {
        id: 1,
      },
    });

    renderHook(() => useProfile(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() =>
      expect(accountService.getProfile).toHaveBeenCalled(),
    );
  });

  it("stores fetched user", async () => {
    accountService.getProfile.mockResolvedValue({
      data: {
        id: 1,
        email: "john@test.com",
      },
    });

    renderHook(() => useProfile(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() =>
      expect(mockSetUser).toHaveBeenCalledWith({
        id: 1,
        email: "john@test.com",
      }),
    );
  });
});



describe("useUpdateProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates store", async () => {
    accountService.updateProfile.mockResolvedValue({
      data: {
        phone: "123456",
      },
    });

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({
        phone: "123456",
      });
    });

    await waitFor(() =>
      expect(mockSetUser).toHaveBeenCalledWith({
        phone: "123456",
      }),
    );
  });

  it("invalidates profile query", async () => {
    accountService.updateProfile.mockResolvedValue({
      data: {},
    });

    const { result } = renderHook(() => useUpdateProfile(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({});
    });

    await waitFor(() =>
      expect(invalidateQueries).toHaveBeenCalledWith({
        queryKey: ["account", "profile"],
      }),
    );
  });
});



describe("useUploadAvatar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("updates only avatar without replacing user", async () => {
    accountService.uploadAvatar.mockResolvedValue({
      data: {
        avatar: "/new-avatar.jpg",
      },
    });

    const { result } = renderHook(() => useUploadAvatar(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate(new FormData());
    });

    await waitFor(() =>
      expect(mockSetUser).toHaveBeenCalledWith({
        id: 1,
        email: "john@test.com",
        profile: {
          avatar: "/new-avatar.jpg",
        },
      }),
    );
  });
});