// src/shared/api/transformers.js

/*
 ─── Backend Envelope Contract ────────────────────────────────────────────────

 Guaranteed across ALL endpoints (success AND error):

 {
   success: boolean,
   message: string | null,
   data:    any,
   errors:  {
     code:       string,          ← top-level category code (ErrorCode.*)
                                    e.g. "validation_error", "conflict_error"
     fields:     {                ← field-level errors, null if none
       [field_name]: {
         message: string,
         code:    string          ← specific code e.g. "email_already_exists"
       }
     } | null,
     non_fields: {                ← cross-field / domain / system errors
       category: "validation"     ← "validation" | "domain" |
                | "domain"           "system" | "unexpected"
                | "system"
                | "unexpected",
       message:  string,
       code:     string,          ← specific code e.g. "email_not_verified"
       extra:    object | null    ← client_extra from any BaseAppError
     } | null                        subclass — structured hints
   } | null,
   meta: {
    request_id: string           ← injected by RequestIDMiddleware
    ...                          ← pagination or other extras
   } | null
 }

 
                    
 
 */
import { ErrorCode, NonFieldCategory } from "./error-codes";
export { ErrorCode, NonFieldCategory };

// ─── Success Unwrap ───────────────────────────────────────────────────────────

/**
 * Unwraps a successful axios response from the standard backend envelope.
 *
 * Call this in every service function on the happy path:
 *   const response = await api.post("/api/.../", payload);
 *   return extractResponse(response);
 *
 * Returns the inner payload — does NOT transform, rename, or filter anything.
 * The raw backend `data` is passed through as-is to keep service functions
 * free of mapping logic (that belongs in hooks or components).
 *
 * @param {import('axios').AxiosResponse} axiosResponse
 * @returns {{
 *   data:      any,
 *   message:   string | null,
 *   meta:      object | null
 * }}
 */
export const extractResponse = (axiosResponse) => {
  const envelope = axiosResponse.data;
  return {
    data: envelope.data ?? null,
    message: envelope.message ?? null,
    meta: envelope.meta ?? null,
  };
};

// ─── Error Normalization ──────────────────────────────────────────────────────

/**
 * Normalizes a raw axios error into a consistent, fully-typed shape.
 *
 * Call this in React Query onError callbacks or in error boundaries.
 * Never inspect the raw axios error directly outside this function.
 *
 * GUARANTEES:
 *   - message          → always a string, never undefined
 *   - status           → HTTP integer or null on network error
 *   - requestId        → string or null
 *   - errors           → full errors envelope or null
 *   - errors.code      → top-level ErrorCode string (when errors present)
 *   - errors.fields    → field dict or null
 *   - errors.non_fields → { category, message, code, extra } or null
 *   - Boolean flags    → convenience for common branching in UI
 *
 * DOES NOT:
 *   - Inspect what is inside fields beyond passing through
 *   - Make assumptions about which fields exist
 *   - Transform or rename anything inside the errors envelope
 *   - Throw — always returns a normalized object
 *
 * @param {any} rawAxiosError
 * @returns {NormalizedError}
 */
export const normalizeError = (rawAxiosError) => {
  // ── Network failure — no response at all ───────────────────────────────────
  // Covers: timeout, DNS failure, CORS, server unreachable
  if (!rawAxiosError?.response) {
    return {
      message: "Network error. Please check your connection.",
      errors: null,
      meta: null,
      status: null,
      requestId: null,

      // Convenience flags
      isNetworkError: true,
      isServerError: false,
      isClientError: false,
      isAuthError: false,
      isForbidden: false,
      isNotFound: false,
      isConflict: false,
      isRateLimit: false,
    };
  }

  const { status, data } = rawAxiosError.response;

  return {
    message: data?.message ?? _deriveMessageFromStatus(status),

    // ── Structured error envelope ────────────────────────────────────────────
    // Consumer accesses:
    //   errors.code                         ← top-level category
    //   errors.fields?.email?.message       ← field error message
    //   errors.fields?.email?.code          ← field error code
    //   errors.non_fields?.category         ← "validation"|"domain"|"system"|"unexpected"
    //                                          NOTE: 401/403/404 now report
    //                                          "domain" here, not "validation" —
    //                                          see contract note at top of file
    //   errors.non_fields?.message          ← human-readable non-field message
    //   errors.non_fields?.code             ← specific error code
    //   errors.non_fields?.extra            ← client_extra (structured hints)
    errors: data?.errors ?? null,

    // ── Response metadata ────────────────────────────────────────────────────
    meta: data?.meta ?? null,
    status,
    requestId: data?.meta?.request_id ?? null,

    isNetworkError: false,
    isServerError: status >= 500,
    isClientError: status >= 400 && status < 500,
    isAuthError: status === 401,
    isForbidden: status === 403,
    isNotFound: status === 404,
    isConflict: status === 409,
    isRateLimit: status === 429,
  };
};


// ─── Error handling  ──────────────────────────────────────────────────────

export const extractErrors = (normalized) => {
  const rawFields = normalized?.errors?.fields ?? {};
  const nonField = normalized?.errors?.non_fields ?? null;
  
  
 
  const fieldErrors = {};
  for (const [field, detail] of Object.entries(rawFields)) {
    fieldErrors[field] = {
      message: detail?.message ?? null,
      code: detail?.code ?? null,
    };
  }
 
  return {
    fieldErrors,
    formError: nonField?.message ?? null,
    formErrorCode: nonField?.code ?? null,
    category: nonField?.category ?? null,
    extra: nonField?.extra ?? null,
  };
};





// ─── Private Helpers ──────────────────────────────────────────────────────────

/**
 * Last-resort human-readable message from HTTP status.
 *
 * Only fires when the backend response is malformed and has no message field.
 * Your backend ALWAYS sends message, so this is a defensive fallback only.
 *
 * Messages are intentionally identical to backend's _status_to_message()
 * so the UI is consistent whether the message comes from backend or here.
 * Includes 422, added on the backend to support DomainError's widened
 * status range — mapped to the same message as 400.
 *
 * @param {number} status
 * @returns {string}
 */
const _deriveMessageFromStatus = (status) => {
  const map = {
    400: "Invalid request data.",
    401: "Authentication required.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    405: "Method not allowed.",
    409: "This action conflicts with the current state of the resource.",
    422: "Invalid request data.",
    429: "Too many requests. Please slow down.",
    500: "An unexpected error occurred. Please try again later.",
    503: "The service is temporarily unavailable. Please try again shortly.",
  };
  return map[status] ?? "Request failed.";
};




















// ─── Convenience Accessors ────────────────────────────────────────────────────
//
// These are pure helper functions — not required, but they make hook code
// cleaner and prevent repeated optional chaining at call sites.
//
// Usage in a custom hook:
//   const normalized = normalizeError(error)
//   const fieldErrors = extractFieldErrors(normalized)
//   const nonField    = extractNonFieldError(normalized)

/**
 * Extracts field-level errors from a normalized error.
 *
 * Returns the fields dict directly so callers can do:
 *   const fields = extractFieldErrors(normalized)
 *   fields?.email?.message   → "This email is already registered."
 *   fields?.email?.code      → "email_already_exists"
 *
 * @param {NormalizedError} normalizedError
 * @returns {Record<string, { message: string, code: string }> | null}
 */
/*
export const extractFieldErrors = (normalizedError) => {
  return normalizedError?.errors?.fields ?? null;
};
*/
/**
 * Extracts the non-field error block from a normalized error.
 *
 * Returns the full non_fields object:
 *   {
 *     category: "validation" | "domain" | "system" | "unexpected",
 *     message:  string,
 *     code:     string,
 *     extra:    object | null
 *   }
 *
 * Usage:
 *   const nonField = extractNonFieldError(normalized)
 *   if (nonField?.code === ErrorCode.EMAIL_NOT_VERIFIED) {
 *     // show resend button
 *   }
 *   if (nonField?.category === NonFieldCategory.DOMAIN) {
 *     // business rule blocked, OR auth/permission/not-found failed —
 *     // see contract note at top of file if you need to tell these apart
 *   }
 *   if (nonField?.extra?.retry_after) {
 *     // show countdown from client_extra
 *   }
 *
 * @param {NormalizedError} normalizedError
 * @returns {{ category: string, message: string, code: string, extra: object|null } | null}
 */
/*
export const extractNonFieldError = (normalizedError) => {
  return normalizedError?.errors?.non_fields ?? null;
};
*/
/**
 * Extracts field-level and non-field errors into a UI-ready shape,
 * without the caller needing to know which field names exist.
 *
 * This exists specifically so hooks never hardcode a list of field
 * names to pull out of normalized.errors.fields — that pattern breaks
 * Open/Closed: adding a new backend serializer field (e.g. "role")
 * would silently require editing every hook that reads field errors,
 * and forgetting to do so means that field's errors exist in the data
 * but never reach the UI. Iterating Object.entries() instead means any
 * hook using this function requires zero changes when the backend adds,
 * renames, or removes a field.
 *
 * Usage in a form hook:
 *   const normalized = isError ? normalizeError(error) : null;
 *   const { fieldErrors, formError, formErrorCode } = extractFormErrors(normalized);
 *   // fieldErrors.email?.message, fieldErrors.email?.code
 *
 * @param {NormalizedError|null} normalized
 * @returns {{
 *   fieldErrors: Record<string, { message: string|null, code: string|null }>,
 *   formError: string|null,
 *   formErrorCode: string|null
 * }}
 */
/*
export const extractFormErrors = (normalized) => {
  const fieldErrors = {};
  for (const [field, detail] of Object.entries(normalized?.errors?.fields ?? {})) {
    fieldErrors[field] = {
      message: detail?.message ?? null,
      code: detail?.code ?? null,
    };
  }
  return {
    fieldErrors,
    formError: normalized?.errors?.non_fields?.message ?? null,
    formErrorCode: normalized?.errors?.non_fields?.code ?? null,
  };
};
*/
/**
 * Returns true if the error's non_fields.category is "domain".
 *
 * Shorthand for:
 *   normalizedError?.errors?.non_fields?.category === "domain"
 *
 * IMPORTANT: as of the current backend, this now returns true for 401
 * (missing credentials), 403 (insufficient permission), and 404
 * (not found) responses as well as genuine business-rule violations —
 * all four are backend DomainError subclasses now. If your UI needs to
 * treat "please log in" differently from "this coupon already expired",
 * do not rely on isDomainError() alone to distinguish them — check
 * normalized.isAuthError / isForbidden / isNotFound first, since those
 * remain status-derived and unaffected by this change.
 *
 * @param {NormalizedError} normalizedError
 * @returns {boolean}
 */
/*
export const isDomainError = (normalizedError) => {
  return (
    normalizedError?.errors?.non_fields?.category === NonFieldCategory.DOMAIN
  );
};
*/

/**
 * Returns true if the error is a system/infrastructure error.
 * When true: show "try again later" — retrying is safe.
 *
 * @param {NormalizedError} normalizedError
 * @returns {boolean}
 */
/*
export const isSystemError = (normalizedError) => {
  return (
    normalizedError?.errors?.non_fields?.category === NonFieldCategory.SYSTEM
  );
};
*/

















































// // src/api/transformers.js
// //
// // ─── Backend Envelope Contract ────────────────────────────────────────────────
// //
// // Guaranteed across ALL endpoints (success AND error):
// //
// // {
// //   success: boolean,
// //   message: string | null,
// //   data:    any,
// //   errors:  {
// //     code:       string,          ← top-level category code (ErrorCode.*)
// //                                    e.g. "validation_error", "conflict_error"
// //     fields:     {                ← field-level errors, null if none
// //       [field_name]: {
// //         message: string,
// //         code:    string          ← specific code e.g. "email_already_exists"
// //       }
// //     } | null,
// //     non_fields: {                ← cross-field / domain / system errors
// //       category: "validation"     ← "validation" | "domain" |
// //                | "domain"           "system" | "unexpected"
// //                | "system"
// //                | "unexpected",
// //       message:  string,
// //       code:     string,          ← specific code e.g. "email_not_verified"
// //       extra:    object | null    ← client_extra from DomainError /
// //     } | null                        InfrastructureError — structured hints
// //   } | null,
// //   meta: {
// //     request_id: string           ← injected by RequestIDMiddleware
// //     ...                          ← pagination or other extras
// //   } | null
// // }
// //
// // NON-FIELD CATEGORIES (what errors.non_fields.category means):
// //
// //   "validation"  → DRF field/auth/permission error (client sent bad data)
// //   "domain"      → Business rule violation (DomainError raised in service)
// //   "system"      → Infrastructure failure (InfrastructureError, 503)
// //   "unexpected"  → Unhandled server exception (bug — contact support)
// //
// // SECURITY NOTE:
// //   exc.internal is NEVER present in any response.
// //   Only exc.client_extra reaches extra. Safe to render.
// //
// // ─────────────────────────────────────────────────────────────────────────────

// // ─── Error Code Registry ──────────────────────────────────────────────────────

// /**
//  * Mirror of apps/core/error_codes.py → ErrorCode class.
//  *
//  * SYNC CONTRACT:
//  *   This object MUST stay 1:1 with the backend ErrorCode class.
//  *   - Never hardcode error code strings anywhere else in the codebase.
//  *   - Never delete a code — comment it as deprecated instead.
//  *   - Adding a backend code → add it here in the same PR.
//  *   - Changing a value = breaking change for both sides.
//  *
//  * USAGE:
//  *   import { ErrorCode } from '../api/transformers'
//  *
//  *   // Top-level category check
//  *   if (normalized.errors?.code === ErrorCode.CONFLICT_ERROR) { ... }
//  *
//  *   // Specific cause check
//  *   if (normalized.errors?.non_fields?.code === ErrorCode.EMAIL_NOT_VERIFIED) { ... }
//  *
//  *   // Field-level check
//  *   if (normalized.errors?.fields?.email?.code === ErrorCode.EMAIL_ALREADY_EXISTS) { ... }
//  */
// export const ErrorCode = {
//   // ── Authentication ──────────────────────────────────────────────────────────
//   INVALID_CREDENTIALS: "invalid_credentials",
//   EMAIL_NOT_VERIFIED: "email_not_verified",
//   ACCOUNT_DISABLED: "account_disabled",
//   ACCOUNT_INACTIVE: "account_inactive",
//   SESSION_EXPIRED: "session_expired",
//   TOKEN_INVALID: "token_invalid",
//   TOKEN_EXPIRED: "token_expired",
//   // ── OTP / Security Verification ────────────────────────────────────────────
//   OTP_RESEND_COOLDOWN: "otp_resend_cooldown",
//   OTP_NOT_FOUND: "otp_not_found",
//   OTP_EXPIRED: "otp_expired",
//   OTP_INVALID: "otp_invalid",
//   OTP_ATTEMPTS_EXCEEDED: "otp_attempts_exceeded",
//   VERIFICATION_SESSION_INVALID: "verification_session_invalid",
//   VERIFICATION_SESSION_EXPIRED: "verification_session_expired",

//   // ── Social Auth ────────────────────────────────────────────────────────────
//   UNSUPPORTED_AUTH_PROVIDER: "unsupported_auth_provider",
//   INVALID_SOCIAL_TOKEN: "invalid_social_token",
//   AUTH_PROVIDER_UNREACHABLE: "auth_provider_unreachable",
//   SOCIAL_EMAIL_NOT_VERIFIED: "social_email_not_verified",
//   SOCIAL_EMAIL_MISSING: "social_email_missing", 

//   // ── Registration / Email ────────────────────────────────────────────────────
//   EMAIL_ALREADY_EXISTS: "email_already_exists",
//   EMAIL_INVALID_FORMAT: "email_invalid_format",

//   // ── User / Profile ──────────────────────────────────────────────────────────
//   INVALID_FULL_NAME: "invalid_full_name",
//   INVALID_PHONE: "invalid_phone",
//   INVALID_DATE_OF_BIRTH: "invalid_date_of_birth",
//   INVALID_ADDRESS: "invalid_address",

//   // ── Password ────────────────────────────────────────────────────────────────
//   PASSWORD_TOO_WEAK: "password_too_weak",
//   PASSWORD_MISMATCH: "password_mismatch",
//   PASSWORD_SAME_AS_OLD: "password_same_as_old",

//   // ── File Upload ─────────────────────────────────────────────────────────────
//   INVALID_IMAGE_SIZE: "invalid_image_size",
//   INVALID_IMAGE_TYPE: "invalid_image_type",

//   // ── Top-level Category Codes (errors.code) ──────────────────────────────────
//   // These describe WHAT CLASS of error occurred.
//   // Frontend branches on these first, then reads non_fields.code for specifics.
//   VALIDATION_ERROR: "validation_error", // 400 — bad input / field errors
//   AUTHENTICATION_ERROR: "authentication_error", // 401
//   PERMISSION_ERROR: "permission_error", // 403
//   NOT_FOUND: "not_found", // 404
//   METHOD_NOT_ALLOWED: "method_not_allowed", // 405
//   CONFLICT_ERROR: "conflict_error", // 409 — valid data, state refuses
//   RATE_LIMIT_EXCEEDED: "rate_limit_exceeded", // 429
//   SERVER_ERROR: "server_error", // 500 / 503
// };

// // ─── Non-field Category Constants ────────────────────────────────────────────

// /**
//  * Mirror of the non_fields.category values the backend produces.
//  *
//  * Use these instead of comparing raw strings:
//  *   if (non_fields?.category === NonFieldCategory.DOMAIN) { ... }
//  *
//  * CATEGORY DECISION GUIDE for UI:
//  *   VALIDATION  → Show inline or toast — user can fix it
//  *   DOMAIN      → Show informative toast/modal — business rule blocked action
//  *   SYSTEM      → Show "try again later" — infrastructure issue, retry safe
//  *   UNEXPECTED  → Show "something went wrong" — bug, report to support
//  */
// export const NonFieldCategory = {
//   VALIDATION: "validation",
//   DOMAIN: "domain",
//   SYSTEM: "system",
//   UNEXPECTED: "unexpected",
// };

// // ─── Success Unwrap ───────────────────────────────────────────────────────────

// /**
//  * Unwraps a successful axios response from the standard backend envelope.
//  *
//  * Call this in every service function on the happy path:
//  *   const response = await api.post("/api/.../", payload);
//  *   return extractResponse(response);
//  *
//  * Returns the inner payload — does NOT transform, rename, or filter anything.
//  * The raw backend `data` is passed through as-is to keep service functions
//  * free of mapping logic (that belongs in hooks or components).
//  *
//  * @param {import('axios').AxiosResponse} axiosResponse
//  * @returns {{
//  *   data:      any,
//  *   message:   string | null,
//  *   meta:      object | null
//  * }}
//  */
// export const extractResponse = (axiosResponse) => {
//   const envelope = axiosResponse.data;
//   return {
//     data: envelope.data ?? null,
//     message: envelope.message ?? null,
//     meta: envelope.meta ?? null,
//   };
// };

// // ─── Error Normalization ──────────────────────────────────────────────────────

// /**
//  * Normalizes a raw axios error into a consistent, fully-typed shape.
//  *
//  * Call this in React Query onError callbacks or in error boundaries.
//  * Never inspect the raw axios error directly outside this function.
//  *
//  * GUARANTEES:
//  *   - message          → always a string, never undefined
//  *   - status           → HTTP integer or null on network error
//  *   - requestId        → string or null
//  *   - errors           → full errors envelope or null
//  *   - errors.code      → top-level ErrorCode string (when errors present)
//  *   - errors.fields    → field dict or null
//  *   - errors.non_fields → { category, message, code, extra } or null
//  *   - Boolean flags    → convenience for common branching in UI
//  *
//  * DOES NOT:
//  *   - Inspect what is inside fields beyond passing through
//  *   - Make assumptions about which fields exist
//  *   - Transform or rename anything inside the errors envelope
//  *   - Throw — always returns a normalized object
//  *
//  * @param {any} rawAxiosError
//  * @returns {NormalizedError}
//  */
// export const normalizeError = (rawAxiosError) => {
//   // ── Network failure — no response at all ───────────────────────────────────
//   // Covers: timeout, DNS failure, CORS, server unreachable
//   if (!rawAxiosError?.response) {
//     return {
//       message: "Network error. Please check your connection.",
//       errors: null,
//       meta: null,
//       status: null,
//       requestId: null,

//       // Convenience flags
//       isNetworkError: true,
//       isServerError: false,
//       isClientError: false,
//       isAuthError: false,
//       isForbidden: false,
//       isNotFound: false,
//       isConflict: false,
//       isRateLimit: false,
//     };
//   }

//   const { status, data } = rawAxiosError.response;

//   return {
//     // ── Human-readable summary ───────────────────────────────────────────────
//     // Prefer backend message (always present on API errors).
//     // Fall back to status-derived string only on malformed/unexpected responses.
//     message: data?.message ?? _deriveMessageFromStatus(status),

//     // ── Structured error envelope ────────────────────────────────────────────
//     // Passed through untouched — shape guaranteed by backend contract above.
//     // Consumer accesses:
//     //   errors.code                         ← top-level category
//     //   errors.fields?.email?.message       ← field error message
//     //   errors.fields?.email?.code          ← field error code
//     //   errors.non_fields?.category         ← "validation"|"domain"|"system"|"unexpected"
//     //   errors.non_fields?.message          ← human-readable non-field message
//     //   errors.non_fields?.code             ← specific error code
//     //   errors.non_fields?.extra            ← client_extra (structured hints)
//     errors: data?.errors ?? null,

//     // ── Response metadata ────────────────────────────────────────────────────
//     meta: data?.meta ?? null,
//     status,
//     requestId: data?.meta?.request_id ?? null,

//     // ── Status category flags ────────────────────────────────────────────────
//     // Use these for coarse branching. Use errors.code for fine-grained logic.
//     //
//     // isNetworkError → no internet / server unreachable
//     // isServerError  → 5xx — backend failed, not user's fault
//     // isClientError  → 4xx — user/client did something wrong
//     // isAuthError    → 401 — redirect to login
//     // isForbidden    → 403 — show "access denied"
//     // isNotFound     → 404 — show "not found" page/message
//     // isConflict     → 409 — state conflict (already exists, already cancelled, etc.)
//     // isRateLimit    → 429 — show "slow down" message with retry hint
//     isNetworkError: false,
//     isServerError: status >= 500,
//     isClientError: status >= 400 && status < 500,
//     isAuthError: status === 401,
//     isForbidden: status === 403,
//     isNotFound: status === 404,
//     isConflict: status === 409,
//     isRateLimit: status === 429,
//   };
// };

// // ─── Convenience Accessors ────────────────────────────────────────────────────
// //
// // These are pure helper functions — not required, but they make hook code
// // cleaner and prevent repeated optional chaining at call sites.
// //
// // Usage in a custom hook:
// //   const normalized = normalizeError(error)
// //   const fieldErrors = extractFieldErrors(normalized)
// //   const nonField    = extractNonFieldError(normalized)

// /**
//  * Extracts field-level errors from a normalized error.
//  *
//  * Returns the fields dict directly so callers can do:
//  *   const fields = extractFieldErrors(normalized)
//  *   fields?.email?.message   → "This email is already registered."
//  *   fields?.email?.code      → "email_already_exists"
//  *
//  * @param {NormalizedError} normalizedError
//  * @returns {Record<string, { message: string, code: string }> | null}
//  */
// export const extractFieldErrors = (normalizedError) => {
//   return normalizedError?.errors?.fields ?? null;
// };

// /**
//  * Extracts the non-field error block from a normalized error.
//  *
//  * Returns the full non_fields object:
//  *   {
//  *     category: "validation" | "domain" | "system" | "unexpected",
//  *     message:  string,
//  *     code:     string,
//  *     extra:    object | null
//  *   }
//  *
//  * Usage:
//  *   const nonField = extractNonFieldError(normalized)
//  *   if (nonField?.code === ErrorCode.EMAIL_NOT_VERIFIED) {
//  *     // show resend button
//  *   }
//  *   if (nonField?.category === NonFieldCategory.DOMAIN) {
//  *     // business rule blocked — show informative message
//  *   }
//  *   if (nonField?.extra?.retry_after) {
//  *     // show countdown from client_extra
//  *   }
//  *
//  * @param {NormalizedError} normalizedError
//  * @returns {{ category: string, message: string, code: string, extra: object|null } | null}
//  */
// export const extractNonFieldError = (normalizedError) => {
//   return normalizedError?.errors?.non_fields ?? null;
// };

// /**
//  * Returns true if the error is a domain error (business rule violation).
//  *
//  * Shorthand for:
//  *   normalizedError?.errors?.non_fields?.category === "domain"
//  *
//  * @param {NormalizedError} normalizedError
//  * @returns {boolean}
//  */
// export const isDomainError = (normalizedError) => {
//   return (
//     normalizedError?.errors?.non_fields?.category === NonFieldCategory.DOMAIN
//   );
// };

// /**
//  * Returns true if the error is a system/infrastructure error.
//  * When true: show "try again later" — retrying is safe.
//  *
//  * @param {NormalizedError} normalizedError
//  * @returns {boolean}
//  */
// export const isSystemError = (normalizedError) => {
//   return (
//     normalizedError?.errors?.non_fields?.category === NonFieldCategory.SYSTEM
//   );
// };

// // ─── Private Helpers ──────────────────────────────────────────────────────────

// /**
//  * Last-resort human-readable message from HTTP status.
//  *
//  * Only fires when the backend response is malformed and has no message field.
//  * Your backend ALWAYS sends message, so this is a defensive fallback only.
//  *
//  * Messages are intentionally identical to backend's _status_to_message()
//  * so the UI is consistent whether the message comes from backend or here.
//  *
//  * @param {number} status
//  * @returns {string}
//  */
// const _deriveMessageFromStatus = (status) => {
//   const map = {
//     400: "Invalid request data.",
//     401: "Authentication required.",
//     403: "You do not have permission to perform this action.",
//     404: "The requested resource was not found.",
//     405: "Method not allowed.",
//     409: "This action conflicts with the current state of the resource.",
//     429: "Too many requests. Please slow down.",
//     500: "An unexpected error occurred. Please try again later.",
//     503: "The service is temporarily unavailable. Please try again shortly.",
//   };
//   return map[status] ?? "Request failed.";
// };

