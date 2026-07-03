// src/api/transformers.js

/**
 * Backend envelope contract (guaranteed across ALL endpoints):
 * {
 *   success: boolean,
 *   message: string | null,
 *   data: any,
 *   errors: any | null,
 *   meta: object | null
 * }
 *
 * These functions ONLY unwrap the envelope.
 * They make zero assumptions about what data, errors, or meta contain.
 * That is the consuming component or hook's responsibility.
 */

// ─── Success Unwrap ───────────────────────────────────────────────────────────

/**
 * Unwraps a successful axios response envelope.
 * Call this in every service function.
 *
 * Returns exactly what the backend sent inside the envelope.
 * Does NOT transform, rename, or filter anything inside.
 *
 * @param {import('axios').AxiosResponse} axiosResponse
 * @returns {{ data: any, message: string|null, meta: object|null }}
 */
export const extractResponse = (axiosResponse) => {
  const envelope = axiosResponse.data;

  return {
    data: envelope.data ?? null,
    message: envelope.message ?? null,
    meta: envelope.meta ?? null,
  };
};

// ─── Error Unwrap ─────────────────────────────────────────────────────────────

/**
 * Normalizes a raw axios error into a consistent shape.
 *
 * Guarantees:
 *   - message    → always a string (from backend or derived from status)
 *   - errors     → exactly what backend sent, untouched
 *   - meta       → exactly what backend sent, untouched
 *   - status     → HTTP status code or null on network error
 *   - requestId  → meta.request_id if present
 *   - Boolean flags for common HTTP status categories
 *
 * Does NOT:
 *   - Inspect what is inside errors
 *   - Inspect what is inside meta
 *   - Make assumptions about field names
 *   - Transform error structure
 *
 * @param {any} error - raw axios error
 * @returns {NormalizedError}
 */
export const normalizeError = (error) => {
  // ── No response — network failure, timeout, CORS ─────────────────────────
  if (!error?.response) {
    return {
      message: "Network error. Please check your connection.",
      errors: null,
      meta: null,
      status: null,
      requestId: null,
      isNetworkError: true,
      isServerError: false,
      isClientError: false,
      isAuthError: false,
      isForbidden: false,
      isNotFound: false,
      isRateLimit: false,
    };
  }

  const { status, data } = error.response;

  return {
    // Human readable — use backend message if present, derive from status if not
    message: data?.message ?? deriveMessageFromStatus(status),

    // Pass through untouched — consumer knows the shape for their endpoint
    errors: data?.errors ?? null,

    // Pass through untouched — consumer knows what meta their endpoint returns
    meta: data?.meta ?? null,

    // HTTP metadata — safe to derive mechanically from status code
    status,
    requestId: data?.meta?.request_id ?? null,

    // Status category flags — purely mechanical, no content assumptions
    isNetworkError: false,
    isServerError: status >= 500,
    isClientError: status >= 400 && status < 500,
    isAuthError: status === 401,
    isForbidden: status === 403,
    isNotFound: status === 404,
    isRateLimit: status === 429,
  };
};

// ─── Private Helpers ──────────────────────────────────────────────────────────

/**
 * Last-resort message when backend does not send one.
 * Your backend always sends message, so this rarely fires.
 */
const deriveMessageFromStatus = (status) => {
  const map = {
    400: "Invalid request. Please check your input.",
    401: "Your session has expired. Please log in again.",
    403: "You don't have permission to do this.",
    404: "The requested resource was not found.",
    409: "A conflict occurred. Please try again.",
    429: "Too many requests. Please slow down.",
    500: "Server error. Please try again later.",
    502: "Service unavailable. Please try again.",
    503: "Service temporarily unavailable.",
  };
  return map[status] ?? "An unexpected error occurred.";
};
