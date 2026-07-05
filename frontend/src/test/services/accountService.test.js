// src/test/services/accountService.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { accountService } from "../../services/accountService";
import { api } from "../../api/client";

// Mock the axios instance
vi.mock("../../api/client", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
    patch: vi.fn(),
  },
}));

// ─── Shared mock responses ────────────────────────────────────────────────────

const mockSuccessEnvelope = (data, message = "Success.") => ({
  data: {
    success: true,
    message,
    data,
    errors: null,
    meta: { request_id: "test-123" },
  },
});

const mockErrorEnvelope = (errors, message = "Failed.") => ({
  data: {
    success: false,
    message,
    data: null,
    errors,
    meta: { request_id: "test-456" },
  },
});

// ─── register ─────────────────────────────────────────────────────────────────

describe("accountService.register", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls correct endpoint with payload", async () => {
    const payload = {
      full_name: "John Doe",
      email: "john@test.com",
      password: "password123",
      confirm_password: "password123",
    };

    api.post.mockResolvedValue(
      mockSuccessEnvelope({ user: { id: 1 } }, "Registration successful."),
    );

    await accountService.register(payload);

    expect(api.post).toHaveBeenCalledWith("/api/accounts/register/", payload);
    expect(api.post).toHaveBeenCalledTimes(1);
  });

  it("returns extracted envelope on success", async () => {
    const userData = { user: { id: 1, email: "john@test.com" } };

    api.post.mockResolvedValue(
      mockSuccessEnvelope(userData, "Registration successful."),
    );

    const result = await accountService.register({
      full_name: "John",
      email: "john@test.com",
      password: "pass1234",
      confirm_password: "pass1234",
    });

    expect(result.data).toEqual(userData);
    expect(result.message).toBe("Registration successful.");
    expect(result.meta).toEqual({ request_id: "test-123" });
  });

  it("does not catch errors — lets them bubble up", async () => {
    const networkError = new Error("Network Error");
    networkError.response = null;

    api.post.mockRejectedValue(networkError);

    await expect(
      accountService.register({
        full_name: "John",
        email: "john@test.com",
        password: "pass1234",
        confirm_password: "pass1234",
      }),
    ).rejects.toThrow("Network Error");
  });

  it("bubbles up 400 validation error without catching", async () => {
    const validationError = new Error("Request failed with status 400");
    validationError.response = mockErrorEnvelope({
      email: ["This email is already registered."],
    }).data;

    api.post.mockRejectedValue(validationError);

    await expect(
      accountService.register({
        full_name: "John",
        email: "john@test.com",
        password: "pass1234",
        confirm_password: "pass1234",
      }),
    ).rejects.toThrow();
  });
});


// ADD to src/test/services/accountService.test.js
// below existing register tests

// ─── verifyEmail ──────────────────────────────────────────────────────────────

describe("accountService.verifyEmail", () => {

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls correct endpoint with token payload", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(null, "Email verified successfully.")
    )

    await accountService.verifyEmail({ token: "test-token-123" })

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/verify-email/",
      { token: "test-token-123" }
    )
  })

  it("returns extracted envelope on success", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(null, "Email verified successfully.")
    )

    const result = await accountService.verifyEmail({ token: "test-token-123" })

    expect(result.data).toBeNull()
    expect(result.message).toBe("Email verified successfully.")
  })

  it("bubbles up error without catching", async () => {
    const error = new Error("Invalid token")
    error.response = {
      status: 400,
      data: {
        message: "Invalid or expired token.",
        errors: { non_field_errors: ["Invalid or expired token."] },
        meta: null,
      },
    }

    api.post.mockRejectedValue(error)

    await expect(
      accountService.verifyEmail({ token: "bad-token" })
    ).rejects.toThrow("Invalid token")
  })

})

// ─── resendVerification ───────────────────────────────────────────────────────

describe("accountService.resendVerification", () => {

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("calls correct endpoint with email payload", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(null, "Verification email sent.")
    )

    await accountService.resendVerification({ email: "john@test.com" })

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/resend-verification/",
      { email: "john@test.com" }
    )
  })

  it("returns extracted envelope on success", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(null, "Verification email sent.")
    )

    const result = await accountService.resendVerification({
      email: "john@test.com",
    })

    expect(result.message).toBe("Verification email sent.")
    expect(result.data).toBeNull()
  })

  it("bubbles up error without catching", async () => {
    const error = new Error("Not found")
    error.response = {
      status: 404,
      data: {
        message: "No account found with this email.",
        errors: null,
        meta: null,
      },
    }

    api.post.mockRejectedValue(error)

    await expect(
      accountService.resendVerification({ email: "ghost@test.com" })
    ).rejects.toThrow("Not found")
  })

})







describe("accountService.login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls correct endpoint with credentials", async () => {
    const payload = {
      email: "john@test.com",
      password: "password123",
    };

    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        {
          access: "jwt-token",
          user: { id: 1 },
        },
        "Login successful.",
      ),
    );

    await accountService.login(payload);

    expect(api.post).toHaveBeenCalledWith("/api/accounts/login/", payload);
  });

  it("returns extracted login response", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        {
          access: "jwt",
          user: { id: 1 },
        },
        "Login successful.",
      ),
    );

    const result = await accountService.login({
      email: "john@test.com",
      password: "password123",
    });

    expect(result.data.access).toBe("jwt");
    expect(result.data.user.id).toBe(1);
    expect(result.message).toBe("Login successful.");
  });

  it("bubbles authentication error", async () => {
    const error = new Error("Unauthorized");

    error.response = {
      status: 401,
      data: {
        message: "Login failed.",
        errors: {
          non_field_errors: ["Invalid email or password."],
        },
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.login({
        email: "john@test.com",
        password: "wrong",
      }),
    ).rejects.toThrow("Unauthorized");
  });
});






describe("accountService.login", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls correct endpoint with credentials", async () => {
    const payload = {
      email: "john@test.com",
      password: "password123",
    };

    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        {
          access: "jwt-token",
          user: { id: 1 },
        },
        "Login successful.",
      ),
    );

    await accountService.login(payload);

    expect(api.post).toHaveBeenCalledWith("/api/accounts/login/", payload);
  });

  it("returns extracted login response", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        {
          access: "jwt",
          user: { id: 1 },
        },
        "Login successful.",
      ),
    );

    const result = await accountService.login({
      email: "john@test.com",
      password: "password123",
    });

    expect(result.data.access).toBe("jwt");
    expect(result.data.user.id).toBe(1);
    expect(result.message).toBe("Login successful.");
  });

  it("bubbles authentication error", async () => {
    const error = new Error("Unauthorized");

    error.response = {
      status: 401,
      data: {
        message: "Login failed.",
        errors: {
          non_field_errors: ["Invalid email or password."],
        },
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.login({
        email: "john@test.com",
        password: "wrong",
      }),
    ).rejects.toThrow("Unauthorized");
  });
});


describe("accountService.logout", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls logout endpoint with credentials", async () => {
    api.post.mockResolvedValue(mockSuccessEnvelope(null, "Logged out."));

    await accountService.logout();

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/logout/",
      {},
      {
        withCredentials: true,
      },
    );
  });

  it("returns extracted response", async () => {
    api.post.mockResolvedValue(mockSuccessEnvelope(null, "Logged out."));

    const result = await accountService.logout();

    expect(result.message).toBe("Logged out.");
    expect(result.data).toBeNull();
  });
});


describe("accountService.getProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls profile endpoint", async () => {
    api.get.mockResolvedValue(
      mockSuccessEnvelope({
        id: 1,
        email: "john@test.com",
      }),
    );

    await accountService.getProfile();

    expect(api.get).toHaveBeenCalledWith("/api/accounts/profile/");
  });
});


describe("accountService.updateProfile", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("patches profile fields", async () => {
    const payload = {
      phone: "123456",
    };

    api.patch.mockResolvedValue(mockSuccessEnvelope(payload, "Updated."));

    await accountService.updateProfile(payload);

    expect(api.patch).toHaveBeenCalledWith("/api/accounts/profile/", payload);
  });
});




describe("accountService.uploadAvatar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("uploads multipart form data", async () => {
    const formData = new FormData();

    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        {
          avatar: "/avatar.jpg",
        },
        "Avatar updated.",
      ),
    );

    await accountService.uploadAvatar(formData);

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/profile/avatar/",
      formData,
      {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      },
    );
  });
});

// ─── requestPasswordReset ─────────────────────────────────────────────────────

describe("accountService.requestPasswordReset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls correct endpoint with email payload", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        null,
        "If this email is registered, a password reset link has been sent.",
      ),
    );

    await accountService.requestPasswordReset({
      email: "john@test.com",
    });

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/password-reset/",
      { email: "john@test.com" },
    );
  });

  it("returns extracted envelope on success", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        null,
        "If this email is registered, a password reset link has been sent.",
      ),
    );

    const result = await accountService.requestPasswordReset({
      email: "john@test.com",
    });

    expect(result.data).toBeNull();
    expect(result.message).toBe(
      "If this email is registered, a password reset link has been sent.",
    );
    expect(result.meta).toEqual({ request_id: "test-123" });
  });

  it("bubbles up error without catching", async () => {
    const error = new Error("Rate limited");
    error.response = {
      status: 429,
      data: {
        message: "Too many requests.",
        errors: null,
        meta: null,
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.requestPasswordReset({
        email: "john@test.com",
      }),
    ).rejects.toThrow("Rate limited");
  });
});

// ─── confirmPasswordReset ─────────────────────────────────────────────────────

describe("accountService.confirmPasswordReset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls correct endpoint with token and passwords", async () => {
    const payload = {
      token: "reset-token-uuid",
      password: "NewPass123!",
      confirm_password: "NewPass123!",
    };

    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        null,
        "Password reset successfully. You can now log in.",
      ),
    );

    await accountService.confirmPasswordReset(payload);

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/password-reset/confirm/",
      payload,
    );
  });

  it("returns extracted envelope on success", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        null,
        "Password reset successfully. You can now log in.",
      ),
    );

    const result = await accountService.confirmPasswordReset({
      token: "reset-token-uuid",
      password: "NewPass123!",
      confirm_password: "NewPass123!",
    });

    expect(result.data).toBeNull();
    expect(result.message).toBe(
      "Password reset successfully. You can now log in.",
    );
  });

  it("bubbles up invalid token error without catching", async () => {
    const error = new Error("Invalid token");
    error.response = {
      status: 400,
      data: {
        message: "Invalid or expired token.",
        errors: {
          non_field_errors: ["Invalid or expired token."],
        },
        meta: null,
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.confirmPasswordReset({
        token: "bad-token",
        password: "NewPass123!",
        confirm_password: "NewPass123!",
      }),
    ).rejects.toThrow("Invalid token");
  });

  it("bubbles up validation error without catching", async () => {
    const error = new Error("Validation failed");
    error.response = {
      status: 400,
      data: {
        message: "Password reset failed.",
        errors: {
          password: ["Password must be at least 8 characters."],
          confirm_password: ["Passwords do not match."],
        },
        meta: null,
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.confirmPasswordReset({
        token: "valid-token",
        password: "abc",
        confirm_password: "xyz",
      }),
    ).rejects.toThrow("Validation failed");
  });
});

// ─── changePassword ───────────────────────────────────────────────────────────

describe("accountService.changePassword", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls correct endpoint with all password fields", async () => {
    const payload = {
      current_password: "OldPass123!",
      new_password: "NewPass456!",
      confirm_new_password: "NewPass456!",
    };

    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        null,
        "Password changed successfully. Please log in again.",
      ),
    );

    await accountService.changePassword(payload);

    expect(api.post).toHaveBeenCalledWith(
      "/api/accounts/change-password/",
      payload,
    );
  });

  it("returns extracted envelope on success", async () => {
    api.post.mockResolvedValue(
      mockSuccessEnvelope(
        null,
        "Password changed successfully. Please log in again.",
      ),
    );

    const result = await accountService.changePassword({
      current_password: "OldPass123!",
      new_password: "NewPass456!",
      confirm_new_password: "NewPass456!",
    });

    expect(result.data).toBeNull();
    expect(result.message).toBe(
      "Password changed successfully. Please log in again.",
    );
  });

  it("bubbles up wrong current password error without catching", async () => {
    const error = new Error("Unauthorized");
    error.response = {
      status: 400,
      data: {
        message: "Password change failed.",
        errors: {
          current_password: ["Current password is incorrect."],
        },
        meta: null,
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.changePassword({
        current_password: "wrong",
        new_password: "NewPass456!",
        confirm_new_password: "NewPass456!",
      }),
    ).rejects.toThrow("Unauthorized");
  });

  it("bubbles up validation error without catching", async () => {
    const error = new Error("Validation failed");
    error.response = {
      status: 400,
      data: {
        message: "Password change failed.",
        errors: {
          new_password: ["Password must be at least 8 characters."],
          confirm_new_password: ["Passwords do not match."],
        },
        meta: null,
      },
    };

    api.post.mockRejectedValue(error);

    await expect(
      accountService.changePassword({
        current_password: "OldPass123!",
        new_password: "abc",
        confirm_new_password: "xyz",
      }),
    ).rejects.toThrow("Validation failed");
  });
});