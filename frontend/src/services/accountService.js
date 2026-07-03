// src/services/accountService.js

import { api } from "../api/client";
import { extractResponse } from "../api/transformers";

export const accountService = {
  /**
   * POST /api/accounts/register/
   * @param {{ full_name, email, password, confirm_password }} payload
   */
  register: async (payload) => {
    const response = await api.post("/api/accounts/register/", payload);
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
};

// // src/services/accountService.js

// import { api } from "../api/client";
// import { extractResponse } from "../api/transformers";

// /**
//  * Account Service
//  *
//  * Handles all HTTP calls for the accounts app.
//  * Endpoints: /api/accounts/
//  *
//  * Rules:
//  *  - Every function calls extractResponse() before returning
//  *  - Never catch errors here — let them bubble to TanStack Query
//  *  - Never import hooks here — services are plain async functions
//  *  - Never access component state here
//  */

// export const accountService = {
//   /**
//    * Register a new user
//    * POST /api/accounts/register/
//    *
//    * @param {{ full_name, email, password, confirm_password }} payload
//    * @returns {{ data: { user }, message, meta }}
//    */
//   register: async (payload) => {
//     const response = await api.post("/api/accounts/register/", payload);
//     return extractResponse(response);
//   },

//   /**
//    * Login with email and password
//    * POST /api/accounts/login/
//    *
//    * @param {{ email, password }} payload
//    * @returns {{ data: { access, user }, message, meta }}
//    */
//   login: async (payload) => {
//     const response = await api.post("/api/accounts/login/", payload);
//     return extractResponse(response);
//   },

//   /**
//    * Logout current user
//    * POST /api/accounts/logout/
//    * Refresh token cookie is cleared by backend
//    *
//    * @returns {{ data: null, message, meta }}
//    */
//   logout: async () => {
//     const response = await api.post(
//       "/api/accounts/logout/",
//       {},
//       {
//         withCredentials: true, // backend needs to clear the cookie
//       },
//     );
//     return extractResponse(response);
//   },
// };

// // Note: token/refresh is NOT here
// // It is called directly inside interceptors.js — not via TanStack Query
// // because it runs during the axios error handling cycle, not component lifecycle
