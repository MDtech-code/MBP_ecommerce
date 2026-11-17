// src/shared/api/client.js
import axios from "axios";
import {
  API_BASE_URL,
  API_TIMEOUT,
  AUTH_BOOTSTRAP_TIMEOUT,
} from "@shared/config";

const baseConfig = {
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
};

/**
 * Primary Axios instance for standard API requests.
 * Interceptors (Bearer token injection + 401 refresh queue) are attached here.
 */
export const api = axios.create({
  ...baseConfig,
  timeout: API_TIMEOUT,
});

/**
 * Bare Axios instance exclusively for session bootstrap and token refresh.
 * Intentionally has NO response interceptors attached so a 401 from
 * /api/accounts/token/refresh/ can never trigger an infinite refresh loop.
 */
export const authClient = axios.create({
  ...baseConfig,
  timeout: AUTH_BOOTSTRAP_TIMEOUT,
});
