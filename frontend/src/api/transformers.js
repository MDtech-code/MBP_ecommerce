// src/api/transformers.js

/**
 * Backend envelope contract (guaranteed across ALL endpoints):
 * {
 *   success: boolean,
 *   message: string | null,
 *   data:    any,
 *   errors:  {
 *     code:       string,       ← top-level category: "validation_error" etc.
 *     fields:     {             ← field-level errors, null if none
 *       field_name: {
 *         message: string,
 *         code:    string       ← machine-readable: "email_already_exists" etc.
 *       }
 *     } | null,
 *     non_fields: {             ← cross-field / auth errors, null if none
 *       message: string,
 *       code:    string
 *     } | null
 *   } | null,
 *   meta: object | null
 * }
 */

// ─── Success Unwrap ───────────────────────────────────────────────────────────

/**
 * Unwraps a successful axios response envelope.
 * Call this in every service function on the happy path.
 *
 * Returns exactly what the backend sent inside the envelope.
 * Does NOT transform, rename, or filter anything inside data.
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
 *   - message      → always a string
 *   - errors.code  → top-level category string, always present on API errors
 *   - errors.fields     → field-level errors dict or null
 *   - errors.non_fields → non-field error {message, code} or null
 *   - status       → HTTP status code or null on network error
 *   - requestId    → meta.request_id if present
 *   - Boolean flags for common HTTP status categories
 *
 * Does NOT:
 *   - Inspect what is inside fields or non_fields beyond passing through
 *   - Make assumptions about which fields exist
 *   - Transform error structure
 *
 * @param {any} error - raw axios error
 * @returns {NormalizedError}
 */
export const normalizeError = (error) => {
  // ── No response — network failure, timeout, CORS ──────────────────────────
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
    // Human readable summary — use backend message, derive from status if missing
    message: data?.message ?? deriveMessageFromStatus(status),

    // Structured error envelope — pass through untouched
    // Consumer accesses: errors.code / errors.fields.x / errors.non_fields
    errors: data?.errors ?? null,

    // Pass through untouched
    meta: data?.meta ?? null,

    // HTTP metadata
    status,
    requestId: data?.meta?.request_id ?? null,

    // Status category flags
    isNetworkError: false,
    isServerError: status >= 500,
    isClientError: status >= 400 && status < 500,
    isAuthError: status === 401,
    isForbidden: status === 403,
    isNotFound: status === 404,
    isRateLimit: status === 429,
  };
};

// ─── Error Code Constants ─────────────────────────────────────────────────────

/**
 * Mirror of apps/core/error_codes.py — ErrorCode class.
 *
 * These MUST stay in sync with the backend registry.
 * Frontend switches on these values — treat them as a public API contract.
 * Never hardcode error code strings outside this object.
 *
 * Usage:
 *   import { ErrorCode } from '../api/transformers'
 *   if (errors?.non_fields?.code === ErrorCode.EMAIL_NOT_VERIFIED) { ... }
 */
export const ErrorCode = {
  // Authentication
  INVALID_CREDENTIALS: "invalid_credentials",
  EMAIL_NOT_VERIFIED: "email_not_verified",
  ACCOUNT_DISABLED: "account_disabled",
  SESSION_EXPIRED: "session_expired",
  TOKEN_INVALID: "token_invalid",
  TOKEN_EXPIRED: "token_expired",
  ACCOUNT_INACTIVE: "account_inactive",

  // Registration / Email
  EMAIL_ALREADY_EXISTS: "email_already_exists",
  EMAIL_INVALID_FORMAT: "email_invalid_format",

  // User / Profile
  INVALID_FULL_NAME: "invalid_full_name",
  INVALID_PHONE: "invalid_phone",
  INVALID_DATE_OF_BIRTH: "invalid_date_of_birth",
  INVALID_ADDRESS: "invalid_address",

  // Password
  PASSWORD_TOO_WEAK: "password_too_weak",
  PASSWORD_MISMATCH: "password_mismatch",
  PASSWORD_SAME_AS_OLD: "password_same_as_old",

  // File Upload
  INVALID_IMAGE_SIZE: "invalid_image_size",
  INVALID_IMAGE_TYPE: "invalid_image_type",

  // Top-level category codes
  VALIDATION_ERROR: "validation_error",
  AUTHENTICATION_ERROR: "authentication_error",
  PERMISSION_ERROR: "permission_error",
  NOT_FOUND: "not_found",
  RATE_LIMIT_EXCEEDED: "rate_limit_exceeded",
  SERVER_ERROR: "server_error",
  METHOD_NOT_ALLOWED: "method_not_allowed",
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
