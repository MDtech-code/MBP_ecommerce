// src/test/api/transformers.test.js
import { describe, it, expect } from "vitest";
import { extractResponse, normalizeError } from "../../api/transformers";

// ─── extractResponse ──────────────────────────────────────────────────────────

describe("extractResponse", () => {
  it("extracts data, message and meta from successful axios response", () => {
    const axiosResponse = {
      data: {
        success: true,
        message: "Registration successful.",
        data: { user: { id: 1, email: "test@test.com" } },
        errors: null,
        meta: { request_id: "abc-123" },
      },
    };

    const result = extractResponse(axiosResponse);

    expect(result.data).toEqual({ user: { id: 1, email: "test@test.com" } });
    expect(result.message).toBe("Registration successful.");
    expect(result.meta).toEqual({ request_id: "abc-123" });
  });

  it("returns null for data when backend sends null", () => {
    const axiosResponse = {
      data: {
        success: true,
        message: "Logged out.",
        data: null,
        errors: null,
        meta: null,
      },
    };

    const result = extractResponse(axiosResponse);

    expect(result.data).toBeNull();
    expect(result.meta).toBeNull();
  });

  it("returns null for missing fields using nullish coalescing", () => {
    const axiosResponse = {
      data: {
        success: true,
      },
    };

    const result = extractResponse(axiosResponse);

    expect(result.data).toBeNull();
    expect(result.message).toBeNull();
    expect(result.meta).toBeNull();
  });
});

// ─── normalizeError ───────────────────────────────────────────────────────────

describe("normalizeError", () => {
  // ── Network error ────────────────────────────────────────────────────────

  describe("network error (no response)", () => {
    it("returns network error shape when error has no response", () => {
      const error = { response: null };
      const result = normalizeError(error);

      expect(result.isNetworkError).toBe(true);
      expect(result.status).toBeNull();
      expect(result.requestId).toBeNull();
      expect(result.errors).toBeNull();
      expect(result.message).toBe(
        "Network error. Please check your connection.",
      );
    });

    it("handles completely empty error object", () => {
      const result = normalizeError({});

      expect(result.isNetworkError).toBe(true);
      expect(result.isServerError).toBe(false);
      expect(result.isClientError).toBe(false);
    });
  });

  // ── Field validation errors (400) ────────────────────────────────────────

  describe("400 field validation errors", () => {
    it("extracts message, errors and requestId from field error response", () => {
      const error = {
        response: {
          status: 400,
          data: {
            success: false,
            message: "Registration failed.",
            data: null,
            errors: {
              full_name: ["This field is required."],
              password: ["Password must be at least 8 characters."],
            },
            meta: { request_id: "abc-123" },
          },
        },
      };

      const result = normalizeError(error);

      expect(result.message).toBe("Registration failed.");
      expect(result.errors).toEqual({
        full_name: ["This field is required."],
        password: ["Password must be at least 8 characters."],
      });
      expect(result.requestId).toBe("abc-123");
      expect(result.status).toBe(400);
      expect(result.isClientError).toBe(true);
      expect(result.isServerError).toBe(false);
      expect(result.isAuthError).toBe(false);
      expect(result.isNetworkError).toBe(false);
    });

    it("passes errors through untouched — does not transform content", () => {
      const rawErrors = {
        email: ["Already registered.", "Must be valid email."],
        password: ["Too short."],
      };

      const error = {
        response: {
          status: 400,
          data: {
            message: "Failed.",
            errors: rawErrors,
            meta: null,
          },
        },
      };

      const result = normalizeError(error);

      // Exactly what backend sent — no transformation
      expect(result.errors).toEqual(rawErrors);
    });
  });

  // ── Non field errors (401 credential failure) ────────────────────────────

  describe("non field errors", () => {
    it("passes non_field_errors through untouched in errors object", () => {
      const error = {
        response: {
          status: 401,
          data: {
            success: false,
            message: "Login failed.",
            data: null,
            errors: {
              non_field_errors: ["Invalid email or password."],
            },
            meta: { request_id: "xyz-456" },
          },
        },
      };

      const result = normalizeError(error);

      expect(result.message).toBe("Login failed.");
      expect(result.errors.non_field_errors).toEqual([
        "Invalid email or password.",
      ]);
      expect(result.isAuthError).toBe(true);
      expect(result.requestId).toBe("xyz-456");
    });
  });

  // ── HTTP status flags ────────────────────────────────────────────────────

  describe("HTTP status flags", () => {
    const makeError = (status) => ({
      response: {
        status,
        data: { message: "error", errors: null, meta: null },
      },
    });

    it("sets isAuthError true for 401", () => {
      expect(normalizeError(makeError(401)).isAuthError).toBe(true);
    });

    it("sets isForbidden true for 403", () => {
      expect(normalizeError(makeError(403)).isForbidden).toBe(true);
    });

    it("sets isNotFound true for 404", () => {
      expect(normalizeError(makeError(404)).isNotFound).toBe(true);
    });

    it("sets isRateLimit true for 429", () => {
      expect(normalizeError(makeError(429)).isRateLimit).toBe(true);
    });

    it("sets isServerError true for 500", () => {
      expect(normalizeError(makeError(500)).isServerError).toBe(true);
    });

    it("sets isServerError true for 503", () => {
      expect(normalizeError(makeError(503)).isServerError).toBe(true);
    });

    it("sets isClientError true for 400", () => {
      expect(normalizeError(makeError(400)).isClientError).toBe(true);
    });

    it("sets isClientError false for 500", () => {
      expect(normalizeError(makeError(500)).isClientError).toBe(false);
    });
  });

  // ── Fallback message ─────────────────────────────────────────────────────

  describe("fallback message", () => {
    it("uses backend message when present", () => {
      const error = {
        response: {
          status: 400,
          data: {
            message: "Custom backend message.",
            errors: null,
            meta: null,
          },
        },
      };
      expect(normalizeError(error).message).toBe("Custom backend message.");
    });

    it("derives message from status when backend sends none", () => {
      const error = {
        response: {
          status: 500,
          data: {},
        },
      };
      expect(normalizeError(error).message).toBe(
        "Server error. Please try again later.",
      );
    });

    it("returns generic fallback for unknown status", () => {
      const error = {
        response: {
          status: 418,
          data: {},
        },
      };
      expect(normalizeError(error).message).toBe(
        "An unexpected error occurred.",
      );
    });
  });

  // ── Meta passthrough ─────────────────────────────────────────────────────

  describe("meta passthrough", () => {
    it("passes full meta through untouched", () => {
      const meta = {
        request_id: "abc-123",
        page: 1,
        total_pages: 5,
        has_next: true,
        source: "database",
        elapsed_ms: 120,
      };

      const error = {
        response: {
          status: 400,
          data: { message: "Failed.", errors: null, meta },
        },
      };

      const result = normalizeError(error);

      // Entire meta object passes through — no fields dropped
      expect(result.meta).toEqual(meta);
    });

    it("returns null meta when backend sends none", () => {
      const error = {
        response: {
          status: 400,
          data: { message: "Failed.", errors: null, meta: null },
        },
      };
      expect(normalizeError(error).meta).toBeNull();
    });
  });
});
