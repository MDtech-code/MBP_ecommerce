// src/test/api/transformers.test.js
import { describe, it, expect } from "vitest";
import {
  extractResponse,
  normalizeError,
  ErrorCode,
} from "../../api/transformers.js";

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Build a minimal axios error with the new structured errors envelope.
 *
 * Mirrors exactly what the backend now sends.
 * Use this in every test that needs a realistic API error —
 * avoids duplicating the full envelope structure in every test.
 */
const makeApiError = (status, overrides = {}) => ({
  response: {
    status,
    data: {
      success: false,
      message: overrides.message ?? "Request failed.",
      data: null,
      errors:
        overrides.errors !== undefined
          ? overrides.errors
          : {
              code: overrides.errorCode ?? ErrorCode.VALIDATION_ERROR,
              fields: overrides.fields ?? null,
              non_fields: overrides.nonFields ?? null,
            },
      meta:
        overrides.meta !== undefined
          ? overrides.meta
          : { request_id: overrides.requestId ?? "test-request-id" },
    },
  },
});

// ─── extractResponse ──────────────────────────────────────────────────────────

describe("extractResponse", () => {
  /**
   * extractResponse only touches the outer envelope — data, message, meta.
   * It never touches errors. All tests here are UNCHANGED from before.
   */

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
    const axiosResponse = { data: { success: true } };

    const result = extractResponse(axiosResponse);

    expect(result.data).toBeNull();
    expect(result.message).toBeNull();
    expect(result.meta).toBeNull();
  });
});

// ─── normalizeError ───────────────────────────────────────────────────────────

describe("normalizeError", () => {
  // ── Network error ──────────────────────────────────────────────────────────

  describe("network error (no response)", () => {
    /**
     * Network errors have no response object at all.
     * These tests are UNCHANGED — network errors don't touch errors shape.
     */

    it("returns network error shape when error has no response", () => {
      const result = normalizeError({ response: null });

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

  // ── errors envelope passthrough ────────────────────────────────────────────

  describe("errors envelope passthrough", () => {
    /**
     * normalizeError passes errors through completely untouched.
     * The shape it passes through is now the NEW structured envelope.
     *
     * CHANGED: old tests built flat errors objects.
     *          new tests build structured {code, fields, non_fields} objects.
     */

    it("passes structured errors envelope through untouched", () => {
      const structuredErrors = {
        code: ErrorCode.VALIDATION_ERROR,
        fields: {
          email: {
            message: "An account with this email already exists.",
            code: ErrorCode.EMAIL_ALREADY_EXISTS,
          },
          password: {
            message: "Password must be at least 8 characters.",
            code: ErrorCode.PASSWORD_TOO_WEAK,
          },
        },
        non_fields: null,
      };

      const error = makeApiError(400, { errors: structuredErrors });
      const result = normalizeError(error);

      // Passed through completely untouched — not modified by normalizeError
      expect(result.errors).toEqual(structuredErrors);
    });

    it("errors.code is accessible directly for category switching", () => {
      /**
       * Frontend top-level category switching:
       *   switch (errors.code) {
       *     case ErrorCode.VALIDATION_ERROR:    // show field errors
       *     case ErrorCode.AUTHENTICATION_ERROR: // redirect to login
       *   }
       */
      const error = makeApiError(400, {
        errorCode: ErrorCode.VALIDATION_ERROR,
      });

      const result = normalizeError(error);

      expect(result.errors.code).toBe(ErrorCode.VALIDATION_ERROR);
    });

    it("errors.fields.email.code accessible for field-level action", () => {
      /**
       * Field-level code switching:
       *   if (errors.fields?.email?.code === ErrorCode.EMAIL_ALREADY_EXISTS) {
       *     // show "Try logging in instead" suggestion
       *   }
       */
      const error = makeApiError(400, {
        fields: {
          email: {
            message: "An account with this email already exists.",
            code: ErrorCode.EMAIL_ALREADY_EXISTS,
          },
        },
      });

      const result = normalizeError(error);

      expect(result.errors.fields.email.code).toBe(
        ErrorCode.EMAIL_ALREADY_EXISTS,
      );
      expect(result.errors.fields.email.message).toBe(
        "An account with this email already exists.",
      );
    });

    it("errors.non_fields accessible for banner-level errors", () => {
      /**
       * Non-field error switching — this is the login email_not_verified case:
       *   if (errors.non_fields?.code === ErrorCode.EMAIL_NOT_VERIFIED) {
       *     // show error message + "Resend verification email" button
       *   }
       *
       * OLD: errors.non_field_errors = ["Please verify your email."]
       *      → frontend could only display it, no action possible
       * NEW: errors.non_fields = {message: "...", code: "email_not_verified"}
       *      → frontend renders message + resend button based on code
       */
      const error = makeApiError(401, {
        errorCode: ErrorCode.AUTHENTICATION_ERROR,
        nonFields: {
          message: "Please verify your email address before logging in.",
          code: ErrorCode.EMAIL_NOT_VERIFIED,
        },
      });

      const result = normalizeError(error);

      expect(result.errors.non_fields.code).toBe(ErrorCode.EMAIL_NOT_VERIFIED);
      expect(result.errors.non_fields.message).toBe(
        "Please verify your email address before logging in.",
      );
    });

    it("errors.fields is null when error has no field errors", () => {
      /**
       * Frontend can safely do: if (errors.fields) { ... }
       * Guaranteed null — never undefined, never empty object.
       */
      const error = makeApiError(401, {
        errorCode: ErrorCode.AUTHENTICATION_ERROR,
        fields: null,
        nonFields: {
          message: "Invalid email or password.",
          code: ErrorCode.INVALID_CREDENTIALS,
        },
      });

      const result = normalizeError(error);

      expect(result.errors.fields).toBeNull();
    });

    it("errors.non_fields is null when error has no non-field errors", () => {
      /**
       * Frontend can safely do: if (errors.non_fields) { ... }
       * Guaranteed null — never undefined, never empty object.
       */
      const error = makeApiError(400, {
        fields: {
          email: { message: "Email required.", code: "required" },
        },
        nonFields: null,
      });

      const result = normalizeError(error);

      expect(result.errors.non_fields).toBeNull();
    });

    it("errors null when backend sends null errors", () => {
      /**
       * 500 in production — backend sends errors=null entirely.
       * normalizeError must pass null through without crashing.
       */
      const error = makeApiError(500, { errors: null });
      const result = normalizeError(error);

      expect(result.errors).toBeNull();
    });
  });

  // ── ErrorCode constants ────────────────────────────────────────────────────

  describe("ErrorCode constants", () => {
    /**
     * NEW TEST GROUP.
     * ErrorCode is now exported from transformers.js.
     * Frontend imports ErrorCode and switches on values — never hardcodes strings.
     * These tests verify the constants are present and have correct values
     * so a typo in the registry does not silently break all error handling.
     */

    it("ErrorCode.EMAIL_NOT_VERIFIED equals 'email_not_verified'", () => {
      expect(ErrorCode.EMAIL_NOT_VERIFIED).toBe("email_not_verified");
    });

    it("ErrorCode.EMAIL_ALREADY_EXISTS equals 'email_already_exists'", () => {
      expect(ErrorCode.EMAIL_ALREADY_EXISTS).toBe("email_already_exists");
    });

    it("ErrorCode.INVALID_CREDENTIALS equals 'invalid_credentials'", () => {
      expect(ErrorCode.INVALID_CREDENTIALS).toBe("invalid_credentials");
    });

    it("ErrorCode.VALIDATION_ERROR equals 'validation_error'", () => {
      expect(ErrorCode.VALIDATION_ERROR).toBe("validation_error");
    });

    it("ErrorCode.AUTHENTICATION_ERROR equals 'authentication_error'", () => {
      expect(ErrorCode.AUTHENTICATION_ERROR).toBe("authentication_error");
    });

    it("ErrorCode.PASSWORD_MISMATCH equals 'password_mismatch'", () => {
      expect(ErrorCode.PASSWORD_MISMATCH).toBe("password_mismatch");
    });

    it("all ErrorCode values are non-empty strings", () => {
      /**
       * Guards against accidental undefined or empty string values
       * in the registry — both would silently break frontend switching.
       */
      Object.entries(ErrorCode).forEach(([key, value]) => {
        (expect(typeof value).toBe("string"),
          `ErrorCode.${key} must be a string`);
        (expect(value.length).toBeGreaterThan(0),
          `ErrorCode.${key} must not be empty`);
      });
    });
  });

  // ── HTTP status flags — UNCHANGED ─────────────────────────────────────────

  describe("HTTP status flags", () => {
    /**
     * Status flags are derived purely from response.status.
     * No dependency on errors shape — all UNCHANGED.
     */
    const makeError = (status) => ({
      response: {
        status,
        data: { message: "error", errors: null, meta: null },
      },
    });

    it("sets isAuthError true for 401", () =>
      expect(normalizeError(makeError(401)).isAuthError).toBe(true));
    it("sets isForbidden true for 403", () =>
      expect(normalizeError(makeError(403)).isForbidden).toBe(true));
    it("sets isNotFound true for 404", () =>
      expect(normalizeError(makeError(404)).isNotFound).toBe(true));
    it("sets isRateLimit true for 429", () =>
      expect(normalizeError(makeError(429)).isRateLimit).toBe(true));
    it("sets isServerError true for 500", () =>
      expect(normalizeError(makeError(500)).isServerError).toBe(true));
    it("sets isServerError true for 503", () =>
      expect(normalizeError(makeError(503)).isServerError).toBe(true));
    it("sets isClientError true for 400", () =>
      expect(normalizeError(makeError(400)).isClientError).toBe(true));
    it("sets isClientError false for 500", () =>
      expect(normalizeError(makeError(500)).isClientError).toBe(false));
  });

  // ── Fallback message — UNCHANGED ──────────────────────────────────────────

  describe("fallback message", () => {
    it("uses backend message when present", () => {
      const error = makeApiError(400, { message: "Custom backend message." });
      expect(normalizeError(error).message).toBe("Custom backend message.");
    });

    it("derives message from status when backend sends none", () => {
      const error = { response: { status: 500, data: {} } };
      expect(normalizeError(error).message).toBe(
        "Server error. Please try again later.",
      );
    });

    it("returns generic fallback for unknown status", () => {
      const error = { response: { status: 418, data: {} } };
      expect(normalizeError(error).message).toBe(
        "An unexpected error occurred.",
      );
    });
  });

  // ── Meta passthrough — UNCHANGED ──────────────────────────────────────────

  describe("meta passthrough", () => {
    it("passes full meta through untouched", () => {
      const meta = {
        request_id: "abc-123",
        page: 1,
        total_pages: 5,
        has_next: true,
      };

      const error = makeApiError(400, { meta });
      const result = normalizeError(error);

      expect(result.meta).toEqual(meta);
    });

    it("returns null meta when backend sends none", () => {
      const error = makeApiError(400, { meta: null });
      expect(normalizeError(error).meta).toBeNull();
    });

    it("requestId extracted from meta.request_id", () => {
      const error = makeApiError(400, { requestId: "my-request-id" });
      expect(normalizeError(error).requestId).toBe("my-request-id");
    });
  });
});
