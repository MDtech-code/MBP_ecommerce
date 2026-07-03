// src/test/services/accountService.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { accountService } from "../../services/accountService";
import { api } from "../../api/client";

// Mock the axios instance
vi.mock("../../api/client", () => ({
  api: {
    post: vi.fn(),
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
