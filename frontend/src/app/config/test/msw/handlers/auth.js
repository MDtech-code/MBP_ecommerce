// src/app/config/test/msw/handlers/auth.js
//
// Default happy-path handlers for all /api/accounts/ endpoints.
// These are the baseline — override in individual tests for error cases.
//
// Usage in a test:
//   import { server } from "@app/config/test/msw/server"
//   import { http, HttpResponse } from "msw"
//   import { emailNotVerifiedError } from "@app/config/test/factories/errors"
//
//   server.use(
//     http.post("/api/accounts/login/", () =>
//       HttpResponse.json(emailNotVerifiedError(), { status: 400 })
//     )
//   )

import { http, HttpResponse } from "msw";
import { createUser, createLoginResponseData } from "../../factories/user";

const success = (data, message = null, meta = null) => ({
  success: true,
  message,
  data,
  errors: null,
  meta: { request_id: "test-request-id", ...meta },
});

export const authHandlers = [
  // ── Register ──────────────────────────────────────────────────────────────
  http.post("/api/accounts/register/", () => {
    return HttpResponse.json(
      success(null, "Registration successful. Please verify your email."),
      { status: 201 },
    );
  }),

  // ── Login ─────────────────────────────────────────────────────────────────
  http.post("/api/accounts/login/", () => {
    return HttpResponse.json(
      success(createLoginResponseData(), "Login successful."),
    );
  }),

  // ── Logout ────────────────────────────────────────────────────────────────
  http.post("/api/accounts/logout/", () => {
    return HttpResponse.json(success(null, "Logged out successfully."));
  }),

  // ── Bootstrap (token refresh) ─────────────────────────────────────────────
  // Default: user has a valid refresh cookie — returns new access token
  http.post("/api/accounts/token/refresh/", () => {
    return HttpResponse.json(success({ access: "refreshed-access-token-xyz" }));
  }),

  // ── Profile ───────────────────────────────────────────────────────────────
  http.get("/api/accounts/profile/", () => {
    return HttpResponse.json(success(createUser()));
  }),

  http.patch("/api/accounts/profile/", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(success({ ...createUser(), ...body }));
  }),

  // ── Avatar ────────────────────────────────────────────────────────────────
  http.post("/api/accounts/profile/avatar/", () => {
    return HttpResponse.json(
      success({ avatar: "/media/avatars/test-avatar.jpg" }),
    );
  }),

  // ── Verify email ──────────────────────────────────────────────────────────
  http.post("/api/accounts/verify-email/", () => {
    return HttpResponse.json(success(null, "Email verified successfully."));
  }),

  // ── Resend verification ───────────────────────────────────────────────────
  http.post("/api/accounts/resend-verification/", () => {
    return HttpResponse.json(
      success(null, "Verification email sent. Please check your inbox."),
    );
  }),

  // ── Addresses ─────────────────────────────────────────────────────────────
  http.post("/api/accounts/addresses/", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json(success({ id: 99, ...body, is_default: false }), {
      status: 201,
    });
  }),

  http.put("/api/accounts/addresses/:id/", async ({ request, params }) => {
    const body = await request.json();
    return HttpResponse.json(success({ id: Number(params.id), ...body }));
  }),

  http.delete("/api/accounts/addresses/:id/", () => {
    return HttpResponse.json(success(null, "Address deleted."));
  }),

  http.patch("/api/accounts/addresses/:id/set-default/", ({ params }) => {
    return HttpResponse.json(
      success({ id: Number(params.id), is_default: true }),
    );
  }),

  // ── Password reset ────────────────────────────────────────────────────────
  http.post("/api/accounts/password-reset/", () => {
    return HttpResponse.json(
      success(null, "If that email exists, a reset link has been sent."),
    );
  }),

  http.post("/api/accounts/password-reset/confirm/", () => {
    return HttpResponse.json(success(null, "Password reset successful."));
  }),

  // ── Change password ───────────────────────────────────────────────────────
  http.post("/api/accounts/change-password/", () => {
    return HttpResponse.json(success(null, "Password changed successfully."));
  }),

  // ── Social login ──────────────────────────────────────────────────────────
  http.post("/api/accounts/auth/social/", () => {
    return HttpResponse.json(success(createLoginResponseData()));
  }),
];
