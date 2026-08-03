// src/shared/api/error-codes.js
//
// ─── Error Code Contract ───────────────────────────────────────────────────
//
// Pure data contract — no logic, no imports beyond nothing. This file
// exists separately from transformers.js on purpose: it is a shared
// vocabulary the backend and frontend both speak, not a transformation
// step. FSD treats these as different concerns even within the same
// shared/api slice — a constants/contract module should not be bundled
// inside the module that contains transformation logic (normalizeError,
// extractFieldErrors, etc.), so that either can be read, tested, or
// replaced independently of the other.
//
// SYNC CONTRACT:
//   This object MUST stay 1:1 with apps/core/error_codes.py → ErrorCode.
//   - Never hardcode an error code string anywhere else in the codebase —
//     always import ErrorCode from here.
//   - Never delete a code — comment it as deprecated instead, exactly as
//     the backend registry does.
//   - Adding a backend code → add it here in the same PR.
//   - Changing a value string is a breaking change for both sides.
//   - Grouped by domain with a comment block, mirroring the backend file's
//     section headers, so a diff against the backend is easy to eyeball.
//
// USAGE:
//   import { ErrorCode } from '@shared/api/error-codes'
//
//   // Top-level category check
//   if (normalized.errors?.code === ErrorCode.CONFLICT_ERROR) { ... }
//
//   // Specific cause check
//   if (normalized.errors?.non_fields?.code === ErrorCode.COUPON_EXPIRED) { ... }
//
//   // Field-level check
//   if (normalized.errors?.fields?.email?.code === ErrorCode.EMAIL_ALREADY_EXISTS) { ... }
//
// ─────────────────────────────────────────────────────────────────────────────

export const ErrorCode = {
  // ── Authentication ──────────────────────────────────────────────────────────
  INVALID_CREDENTIALS: "invalid_credentials",
  EMAIL_NOT_VERIFIED: "email_not_verified",
  ACCOUNT_DISABLED: "account_disabled",
  ACCOUNT_INACTIVE: "account_inactive",
  SESSION_EXPIRED: "session_expired",
  TOKEN_INVALID: "token_invalid",
  TOKEN_EXPIRED: "token_expired",

  // ── OTP / Security Verification ────────────────────────────────────────────
  OTP_RESEND_COOLDOWN: "otp_resend_cooldown",
  OTP_NOT_FOUND: "otp_not_found",
  OTP_EXPIRED: "otp_expired",
  OTP_INVALID: "otp_invalid",
  OTP_ATTEMPTS_EXCEEDED: "otp_attempts_exceeded",
  VERIFICATION_SESSION_INVALID: "verification_session_invalid",
  VERIFICATION_SESSION_EXPIRED: "verification_session_expired",

  // ── Social Auth ────────────────────────────────────────────────────────────
  UNSUPPORTED_AUTH_PROVIDER: "unsupported_auth_provider",
  INVALID_SOCIAL_TOKEN: "invalid_social_token",
  AUTH_PROVIDER_UNREACHABLE: "auth_provider_unreachable",
  SOCIAL_EMAIL_NOT_VERIFIED: "social_email_not_verified",
  SOCIAL_EMAIL_MISSING: "social_email_missing",

  // ── Registration / Email ────────────────────────────────────────────────────
  EMAIL_ALREADY_EXISTS: "email_already_exists",
  EMAIL_INVALID_FORMAT: "email_invalid_format",

  // ── User / Profile ──────────────────────────────────────────────────────────
  INVALID_FULL_NAME: "invalid_full_name",
  INVALID_PHONE: "invalid_phone",
  INVALID_DATE_OF_BIRTH: "invalid_date_of_birth",
  INVALID_ADDRESS: "invalid_address",

  // ── Password ────────────────────────────────────────────────────────────────
  PASSWORD_TOO_WEAK: "password_too_weak",
  PASSWORD_MISMATCH: "password_mismatch",
  PASSWORD_SAME_AS_OLD: "password_same_as_old",

  // ── File Upload ─────────────────────────────────────────────────────────────
  INVALID_IMAGE_SIZE: "invalid_image_size",
  INVALID_IMAGE_TYPE: "invalid_image_type",

  // ── Cart ────────────────────────────────────────────────────────────────────
  CART_EMPTY: "cart_empty",
  CART_QUANTITY_EXCEEDS_STOCK: "cart_quantity_exceeds_stock",

  // ── Coupons ─────────────────────────────────────────────────────────────────
  COUPON_INVALID: "coupon_invalid",
  COUPON_EXPIRED: "coupon_expired",
  COUPON_ALREADY_USED: "coupon_already_used",
  COUPON_LIMIT_REACHED: "coupon_limit_reached",
  COUPON_NOT_APPLIED: "coupon_not_applied",

  // ── Orders ──────────────────────────────────────────────────────────────────
  PRODUCT_UNAVAILABLE: "product_unavailable",
  INSUFFICIENT_STOCK: "insufficient_stock",
  PAYMENT_METHOD_UNAVAILABLE: "payment_method_unavailable",
  ORDER_NOT_CANCELLABLE: "order_not_cancellable",

  // ── Logistics ───────────────────────────────────────────────────────────────
  ORDER_NOT_CONFIRMED: "order_not_confirmed",
  SHIPMENT_ALREADY_EXISTS: "shipment_already_exists",
  TRACKING_NUMBER_EXISTS: "tracking_number_exists",
  INVALID_SHIPMENT_TRANSITION: "invalid_shipment_transition",
  SHIPMENT_NOT_FOUND: "shipment_not_found",
  ORDER_HAS_NO_SHIPMENT: "order_has_no_shipment",

  // ── Logistics / Settlement ───────────────────────────────────────────────────
  SETTLEMENT_ALREADY_EXISTS: "settlement_exists",
  SETTLEMENT_ALREADY_RECONCILED: "settlement_already_reconciled",
  SHIPMENT_NOT_DELIVERED: "shipment_not_delivered",
  SHIPMENT_ALREADY_SETTLED: "shipment_already_settled",

  // ── Logistics / Courier ───────────────────────────────────────────────────────
  COURIER_API_NOT_CONFIGURED: "courier_api_not_configured",
  COURIER_API_TIMEOUT: "courier_api_timeout",
  COURIER_API_ERROR: "courier_api_error",

  // ── Reviews ─────────────────────────────────────────────────────────────────
  ORDER_NOT_DELIVERED: "order_not_delivered",
  REVIEW_ALREADY_EXISTS: "review_already_exists",
  CANNOT_VOTE_OWN_REVIEW: "cannot_vote_own_review",
  REVIEW_NOT_APPROVED: "review_not_approved",

  // ── Returns ─────────────────────────────────────────────────────────────────
  RETURN_WINDOW_EXPIRED: "return_window_expired",
  RETURN_ALREADY_EXISTS: "return_already_exists",
  PHOTOS_REQUIRED: "photos_required",
  RETURN_NOT_APPROVED: "return_not_approved",
  REFUND_EXCEEDS_ORIGINAL: "refund_exceeds_original",

  // ── Payments ────────────────────────────────────────────────────────────────
  ORDER_NOT_PAYABLE: "order_not_payable",
  INVALID_GATEWAY: "invalid_gateway",
  PAYMENT_ALREADY_SUCCESS: "payment_already_success",
  PAYMENT_GATEWAY_TIMEOUT: "payment_gateway_timeout",
  PAYMENT_GATEWAY_ERROR: "payment_gateway_error",
  PAYMENT_GATEWAY_NOT_CONFIGURED: "payment_gateway_not_configured",

  // ── Wishlist ────────────────────────────────────────────────────────────────
  WISHLIST_ITEM_ALREADY_EXISTS: "wishlist_item_already_exists",
  WISHLIST_ITEM_NOT_FOUND: "wishlist_item_not_found",

  // ── Top-level Category Codes (errors.code) ───────────────────────────────────
  // These describe WHAT CLASS of error occurred.
  // Frontend branches on these first, then reads non_fields.code for specifics.
  // Stable across the backend's non_fields.category change (see
  // transformers.js contract note) — these values never moved.
  VALIDATION_ERROR: "validation_error", // 400 / 422 — bad input / field errors
  AUTHENTICATION_ERROR: "authentication_error", // 401
  PERMISSION_ERROR: "permission_error", // 403
  NOT_FOUND: "not_found", // 404
  METHOD_NOT_ALLOWED: "method_not_allowed", // 405
  CONFLICT_ERROR: "conflict_error", // 409 — valid data, state refuses
  RATE_LIMIT_EXCEEDED: "rate_limit_exceeded", // 429
  SERVER_ERROR: "server_error", // 500 / 503
};

/**
 * Mirror of the non_fields.category values the backend produces.
 *
 * Lives here rather than in transformers.js for the same reason
 * ErrorCode does — it is a data contract, not transformation logic.
 *
 * Use these instead of comparing raw strings:
 *   if (non_fields?.category === NonFieldCategory.DOMAIN) { ... }
 *
 * CATEGORY DECISION GUIDE for UI:
 *   VALIDATION  → Show inline or toast — user can fix it
 *   DOMAIN      → Show informative toast/modal — business rule blocked
 *                 the action, OR credentials/permission/not-found failed.
 *                 As of the current backend, DOMAIN covers all three of
 *                 those in addition to plain business-rule violations.
 *                 See transformers.js's contract note if you need to tell
 *                 these apart — prefer isAuthError / isForbidden /
 *                 isNotFound (status-derived) for that distinction.
 *   SYSTEM      → Show "try again later" — infrastructure issue, retry safe
 *   UNEXPECTED  → Show "something went wrong" — bug, report to support
 */
export const NonFieldCategory = {
  VALIDATION: "validation",
  DOMAIN: "domain",
  SYSTEM: "system",
  UNEXPECTED: "unexpected",
};