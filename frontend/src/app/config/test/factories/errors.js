// src/app/config/test/factories/errors.js
//
// Factories for backend error envelopes.
// These match the EXACT shape your backend sends and your transformers.js reads.
// Use these in MSW handlers — never write inline error objects in tests.

// ── Raw backend error envelope ────────────────────────────────────────────────
// This is what the backend sends — what MSW handlers return.
export const createRawErrorResponse = (overrides = {}) => ({
  success: false,
  message: "Something went wrong.",
  data: null,
  errors: {
    code: "validation_error",
    fields: null,
    non_fields: null,
  },
  meta: {
    request_id: "test-request-id-001",
  },
  ...overrides,
});

// ── Field error envelope ──────────────────────────────────────────────────────
// For errors on specific form fields.
// fields: { email: { message: "...", code: "..." } }
//
// Usage:
//   createFieldErrorResponse({
//     email: { message: "Already registered.", code: "email_already_exists" }
//   })
export const createFieldErrorResponse = (fields, overrides = {}) =>
  createRawErrorResponse({
    message: "Validation failed. Please check the highlighted fields.",
    errors: {
      code: "validation_error",
      fields,
      non_fields: null,
    },
    ...overrides,
  });

// ── Non-field error envelope ──────────────────────────────────────────────────
// For domain / auth / system errors not tied to a specific field.
// category: "validation" | "domain" | "system" | "unexpected"
//
// Usage:
//   createNonFieldErrorResponse({
//     category: "domain",
//     message: "Email not verified.",
//     code: "email_not_verified",
//   })
export const createNonFieldErrorResponse = (
  nonFieldsOverrides = {},
  overrides = {},
) =>
  createRawErrorResponse({
    message: nonFieldsOverrides.message ?? "An error occurred.",
    errors: {
      code: "conflict_error",
      fields: null,
      non_fields: {
        category: "domain",
        message: "An error occurred.",
        code: "unknown",
        extra: null,
        ...nonFieldsOverrides,
      },
    },
    ...overrides,
  });

// ── Common pre-built error responses ─────────────────────────────────────────
// These are the exact responses your backend returns for common scenarios.
// Import the one you need in an MSW handler override.

export const invalidCredentialsError = () =>
  createNonFieldErrorResponse(
    {
      category: "domain",
      message: "Invalid email or password.",
      code: "invalid_credentials",
    },
    {
      errors: {
        code: "authentication_error",
        fields: null,
        non_fields: {
          category: "domain",
          message: "Invalid email or password.",
          code: "invalid_credentials",
          extra: null,
        },
      },
      message: "Invalid email or password.",
    },
  );

export const emailNotVerifiedError = () =>
  createNonFieldErrorResponse(
    {
      category: "domain",
      message: "Please verify your email address before logging in.",
      code: "email_not_verified",
    },
    {
      errors: {
        code: "conflict_error",
        fields: null,
        non_fields: {
          category: "domain",
          message: "Please verify your email address before logging in.",
          code: "email_not_verified",
          extra: null,
        },
      },
      message: "Please verify your email address before logging in.",
    },
  );

export const emailAlreadyExistsError = () =>
  createFieldErrorResponse({
    email: {
      message: "A user with this email already exists.",
      code: "email_already_exists",
    },
  });

export const passwordTooWeakError = () =>
  createFieldErrorResponse({
    password: {
      message: "Password is too weak.",
      code: "password_too_weak",
    },
  });

export const tokenExpiredError = () =>
  createNonFieldErrorResponse({
    category: "domain",
    message: "Session expired. Please log in again.",
    code: "token_expired",
  });

export const networkError = () => ({
  // Simulates axios network error (no response)
  message: "Network Error",
  response: undefined,
  request: {},
  isAxiosError: true,
});
