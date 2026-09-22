import { describe, expect, it, vi } from "vitest";
import { extractResponse, extractData, extractPagination, extractRateLimit, normalizeError, extractErrors } from "./transformers";

const rawError = (status, data) => ({ response: { status, data } });

describe("success adapters", () => {
  it("unwraps null data without inventing a user on registration", () => {
    expect(extractResponse({ data: { success: true, data: null, message: "Verify email", meta: { request_id: "r1" } } })).toEqual({
      data: null, message: "Verify email", meta: { request_id: "r1" },
    });
  });
  it("provides safe absent-data defaults", () => {
    expect(extractResponse({ data: {} })).toEqual({ data: null, message: null, meta: null });
    expect(extractData(null, [])).toEqual([]);
    expect(extractData({ data: false }, [])).toBe(false);
    expect(extractPagination(null)).toEqual({});
    expect(extractPagination({ meta: { pagination: { page: 2 } } })).toEqual({ page: 2 });
    expect(extractRateLimit(null)).toBeNull();
    expect(extractRateLimit({ meta: { rateLimit: { remaining: 2 } } })).toEqual({ remaining: 2 });
  });
});

describe("error normalization", () => {
  it.each([null, undefined, new Error("connection down")])("handles no response without throwing", (raw) => {
    const result = normalizeError(raw);
    expect(result.isNetworkError).toBe(true);
    expect(result.status).toBeNull();
    expect(result.message).toMatch(/Network error/);
  });
  it.each([
    [400, "isClientError"], [401, "isAuthError"], [403, "isForbidden"],
    [404, "isNotFound"], [409, "isConflict"], [422, "isClientError"],
    [429, "isRateLimit"], [500, "isServerError"], [503, "isServerError"],
  ])("maps %i to %s and supplies a fallback", (status, flag) => {
    const result = normalizeError(rawError(status, "<html>proxy error</html>"));
    expect(result[flag]).toBe(true);
    expect(result.isNetworkError).toBe(false);
    expect(typeof result.message).toBe("string");
    expect(result.message).not.toContain("html");
  });
  it("uses the generic fallback for an unknown status", () => {
    expect(normalizeError(rawError(418)).message).toBe("Request failed.");
  });
  it("preserves field and domain envelopes and correlation metadata", () => {
    const errors = { code: "validation_error", fields: { email: { code: "invalid", message: "Invalid email" } }, non_fields: null };
    const normalized = normalizeError(rawError(400, { message: "Registration failed", errors, meta: { request_id: "r1" } }));
    expect(normalized.errors).toBe(errors);
    expect(normalized.requestId).toBe("r1");
    expect(extractErrors(normalized).fieldErrors.email).toEqual({ code: "invalid", message: "Invalid email" });
    expect(extractErrors({ errors: { non_fields: { message: "Already exists", code: "conflict_error", category: "domain", extra: { safe: true } } } })).toEqual({
      fieldErrors: {}, formError: "Already exists", formErrorCode: "conflict_error", category: "domain", extra: { safe: true },
    });
  });
  it("handles absent and incomplete field details", () => {
    expect(extractErrors(null)).toEqual({ fieldErrors: {}, formError: null, formErrorCode: null, category: null, extra: null });
    expect(extractErrors({ errors: { fields: { email: {} } } }).fieldErrors.email).toEqual({ message: null, code: null });
  });
  it("provides actionable network and malformed-server form errors", () => {
    expect(extractErrors(normalizeError(null)).formError).toMatch(/Network error/);
    expect(extractErrors(normalizeError(rawError(500, "bad gateway"))).formError).toMatch(/unexpected error/i);
  });
  it("does not turn field-only errors into an extra form banner", () => {
    expect(extractErrors(normalizeError(rawError(400, {
      message: "Registration failed", errors: { fields: { email: { message: "Invalid" } } },
    }))).formError).toBeNull();
  });
});

describe("rate-limit metadata", () => {
  it("prefers structured reset over the English fallback", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
    const result = normalizeError(rawError(429, {
      meta: { rateLimit: { limit: 2, remaining: 0, resetAt: "2026-01-01T00:01:00Z" } },
      errors: { non_fields: { message: "available in 999 seconds" } },
    }));
    expect(result.rateLimit).toEqual({ limit: 2, remaining: 0, resetAt: "2026-01-01T00:01:00Z", retryAfterSeconds: 60 });
  });
  it("clamps elapsed structured resets to zero", () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:01:00Z"));
    expect(normalizeError(rawError(429, { meta: { rateLimit: { resetAt: "2026-01-01T00:00:00Z" } } })).rateLimit.retryAfterSeconds).toBe(0);
  });
  it.each(["Request available in 1 second.", "Request available in 1 seconds."])("parses fallback: %s", (message) => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-01-01T00:00:00Z"));
    expect(normalizeError(rawError(429, { errors: { non_fields: { message } } })).rateLimit).toEqual({
      limit: null, remaining: 0, resetAt: "2026-01-01T00:00:01.000Z", retryAfterSeconds: 1,
    });
  });
  it.each([undefined, "Please try later"])("handles unavailable fallback: %s", (message) => {
    expect(normalizeError(rawError(429, { errors: { non_fields: { message } } })).rateLimit.resetAt).toBeNull();
  });
});
