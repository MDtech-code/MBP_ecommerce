// src/services/accountService.js

import { api } from "../client";
import { extractResponse } from "../transformers";
import { getCookie } from "@shared/lib";
// import axios from "axios";

export const accountService = {
  /**
   * POST /api/accounts/register/
   * @param {{ full_name, email, password, confirm_password }} payload
   */
  register: async (payload) => {
    const response = await api.post("/api/accounts/register/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/auth/social/
   *
   * Handles ALL social providers through one endpoint.
   * Backend strategy pattern resolves the correct provider.
   *
   * @param {{ provider: "google" | "facebook", token: string }} payload
   * @returns {{ access: string }} JWT access token
   *
   * Refresh token arrives as HttpOnly cookie automatically.
   * No manual cookie handling needed on frontend.
   */
  socialLogin: async (payload) => {
    const response = await api.post("/api/accounts/auth/social/", payload);
    return extractResponse(response);
  },

  // ── NEW ──────────────────────────────────────────────────────────────────

  /**
   * POST /api/accounts/verify-email/
   * @param {{ token: string }} payload
   */
  verifyEmail: async (payload) => {
    const response = await api.post("/api/accounts/verify-email/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/resend-verification/
   * @param {{ email: string }} payload
   */
  resendVerification: async (payload) => {
    const response = await api.post(
      "/api/accounts/resend-verification/",
      payload,
    );
    return extractResponse(response);
  },

  // ── NEW ────────────────────────────────────────────────────────────────────

  /**
   * POST /api/accounts/login/
   * @param {{ email: string, password: string }} payload
   * @returns {{ data: { access: string, user: object }, message, meta }}
   */
  login: async (payload) => {
    const response = await api.post("/api/accounts/login/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/logout/
   * Requires withCredentials so backend can clear the refresh token cookie
   */
  logout: async () => {
    const response = await api.post(
      "/api/accounts/logout/",
      {},
      {
        withCredentials: true,
      },
    );
    return extractResponse(response);
  },

  /**
   * GET /api/accounts/profile/
   * Returns full user object — called on page refresh to restore state
   */
  getProfile: async () => {
    const response = await api.get("/api/accounts/profile/");
    return extractResponse(response);
  },

  /**
   * PATCH /api/accounts/profile/
   * Partial update — only send changed fields
   */
  updateProfile: async (payload) => {
    const response = await api.patch("/api/accounts/profile/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/profile/avatar/
   * FormData upload — field name must be "avatar"
   */
  uploadAvatar: async (formData) => {
    const response = await api.post("/api/accounts/profile/avatar/", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/addresses/
   * Create a new shipping address
   * @param {{ label, address_line1, address_line2, city }} payload
   */
  createAddress: async (payload) => {
    const response = await api.post("/api/accounts/addresses/", payload);
    return extractResponse(response);
  },

  /**
   * PUT /api/accounts/addresses/:id/
   * Update an existing address
   * @param {number} id
   * @param {{ label, address_line1, address_line2, city }} payload
   */
  updateAddress: async (id, payload) => {
    const response = await api.put(`/api/accounts/addresses/${id}/`, payload);
    return extractResponse(response);
  },

  /**
   * DELETE /api/accounts/addresses/:id/
   * Delete an address — cannot delete default if it is the only address
   * @param {number} id
   */
  deleteAddress: async (id) => {
    const response = await api.delete(`/api/accounts/addresses/${id}/`);
    return extractResponse(response);
  },

  /**
   * PATCH /api/accounts/addresses/:id/set-default/
   * Set address as user default shipping address
   * @param {number} id
   */
  setDefaultAddress: async (id) => {
    const response = await api.patch(
      `/api/accounts/addresses/${id}/set-default/`,
    );
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/password-reset/
   * Sends reset link to email — always returns success message
   * regardless of whether email exists (backend security behavior)
   * @param {{ email: string }} payload
   */
  requestPasswordReset: async (payload) => {
    const response = await api.post("/api/accounts/password-reset/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/password-reset/confirm/
   * Consumes the token from the reset link URL and sets new password
   * @param {{ token: string, password: string, confirm_password: string }} payload
   */
  confirmPasswordReset: async (payload) => {
    const response = await api.post(
      "/api/accounts/password-reset/confirm/",
      payload,
    );
    return extractResponse(response);
  },

  // ── Security OTP Gate ──────────────────────────────────────────────────────

  /**
   * POST /api/accounts/security/send-otp/
   * Sends 6-digit OTP to user's current email.
   * @param {{ purpose: "change_email"|"change_password"|"delete_account" }} payload
   * @returns {{ masked_email: string }}
   */
  sendSecurityOTP: async (payload) => {
    const response = await api.post(
      "/api/accounts/security/send-otp/",
      payload,
    );
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/security/verify-otp/
   * Verifies OTP and returns verification_token for sensitive action.
   * @param {{ purpose: string, otp_code: string }} payload
   * @returns {{ verification_token: string }}
   */
  verifySecurityOTP: async (payload) => {
    const response = await api.post(
      "/api/accounts/security/verify-otp/",
      payload,
    );
    return extractResponse(response);
  },
  // ── Change Password ────────────────────────────────────────────────────────

  /**
   * POST /api/accounts/change-password/
   * Requires verification_token from OTP gate.
   * @param {{ new_password: string, confirm_new_password: string, verification_token: string }} payload
   */
  changePassword: async (payload) => {
    const response = await api.post("/api/accounts/change-password/", payload);
    return extractResponse(response);
  },

  // ── Email Change ───────────────────────────────────────────────────────────

  /**
   * POST /api/accounts/update-email/
   * Requires verification_token from OTP gate.
   * @param {{ new_email: string, verification_token: string }} payload
   * @returns {{ masked_new_email: string }}
   */
  requestEmailChange: async (payload) => {
    const response = await api.post("/api/accounts/update-email/", payload);
    return extractResponse(response);
  },

  /**
   * POST /api/accounts/update-email/confirm/
   * User enters OTP received at new email address.
   * @param {{ otp_code: string }} payload
   */
  confirmEmailChange: async (payload) => {
    const response = await api.post(
      "/api/accounts/update-email/confirm/",
      payload,
    );
    return extractResponse(response);
  },

  // ── Delete Account ─────────────────────────────────────────────────────────

  /**
   * DELETE /api/accounts/me/delete/
   * Requires verification_token from OTP gate.
   * @param {{ verification_token: string }} payload
   */
  deleteAccount: async (payload) => {
    const response = await api.delete("/api/accounts/me/delete/", {
      data: payload,
    });
    return extractResponse(response);
  },
  // /**
  //  * POST /api/accounts/change-password/
  //  * Authenticated user changes their own password
  //  * Backend logs user out after success — frontend must also clear session
  //  * @param {{ current_password: string, new_password: string,
  //  *            confirm_new_password: string }} payload
  //  */
  // changePassword: async (payload) => {
  //   const response = await api.post("/api/accounts/change-password/", payload);
  //   return extractResponse(response);
  // },
  // /**
  //  * POST /api/accounts/update-email/
  //  * Authenticated — requires new_email + password confirmation
  //  * @param {{ new_email: string, password: string }} payload
  //  */
  // requestEmailChange: async (payload) => {
  //   const response = await api.post("/api/accounts/update-email/", payload);
  //   return extractResponse(response);
  // },

  // /**
  //  * POST /api/accounts/update-email/confirm/
  //  * Public — token from email link
  //  * @param {{ token: string }} payload
  //  */
  // confirmEmailChange: async (payload) => {
  //   const response = await api.post(
  //     "/api/accounts/update-email/confirm/",
  //     payload,
  //   );
  //   return extractResponse(response);
  // },

  // /**
  //  * DELETE /api/accounts/me/delete/
  //  * Authenticated — requires password confirmation
  //  * @param {{ password: string }} payload
  //  */
  // deleteAccount: async (payload) => {
  //   const response = await api.delete("/api/accounts/me/delete/", {
  //     data: payload,
  //   });
  //   return extractResponse(response);
  // },

  /**
   * Called ONCE on app start to restore session.
   * Uses refresh token cookie to get a new access token.
   * Direct axios call — bypasses our api instance so interceptors
   * do not accidentally catch and loop this call.
   */
  bootstrap: async () => {
    console.log("i am from the bootstrap");
    const response = await api.post(
      "/api/accounts/token/refresh/",
      {},
      {
        withCredentials: true,
        headers: {
          "X-CSRFToken": getCookie("csrftoken"),
        },
      },
    );
    return extractResponse(response);
  },
};
