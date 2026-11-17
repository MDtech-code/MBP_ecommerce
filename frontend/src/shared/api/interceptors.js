
// src/shared/api/interceptors.js
import { api, authClient } from "./client";
import {
  setAuthToken,
  getAuthToken,
  getCookie,
} from "@shared/lib";
import { useAuthStore } from "@entities/user";





let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(p => error ? p.reject(error) : p.resolve(token))
  failedQueue = []
}

export const setupInterceptors = () => {
  console.log("[Interceptor] Setting up request and response interceptors...");

  // Request interceptor — attach token to every request
  api.interceptors.request.use(
    (config) => {
      const token = getAuthToken()
      if (token) {
        config.headers.Authorization = `Bearer ${token}`
      }
      return config
    },
    (error) => Promise.reject(error)
  )

  // Response interceptor — handle 401, 429
  api.interceptors.response.use(
    (response) => response,
    async (error) => {
      const originalRequest = error.config
      const status = error.response?.status
      const errorCode = error.response?.data?.errors?.code
      if (error.code === "ECONNABORTED") {
        console.warn(
          "[Interceptor] Request timed out:",
          originalRequest?.url,
        );
      }
      if (sessionStorage.getItem("logged_out") === "true") {
        console.log("[Interceptor] Skipping 401 refresh — session is marked logged_out");
        return Promise.reject(error);
      }
      // ─── 401 handling ─────────────────────────────────────
      // Only refresh if it's a token expiry, not invalid credentials
      // Invalid credentials return 401 with specific error code
      if (
        status === 401 &&
        !originalRequest._retry &&
        !originalRequest.url?.includes("/api/accounts/token/refresh/") &&
        errorCode !== "invalid_credentials"  
      ) {
        if (isRefreshing) {
          console.log(
            "[Interceptor] Refresh already in progress — queueing request:",
            originalRequest?.url,
          );
          return new Promise((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          })
            .then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return api(originalRequest);
            })
            .catch((err) => Promise.reject(err));
        }

        originalRequest._retry = true;
        isRefreshing = true;
        

        try {
          console.log(
            "[Interceptor] 401 detected — calling /api/accounts/token/refresh/ for:",
            originalRequest?.url,
          );
          const response = await authClient.post(
            "/api/accounts/token/refresh/",
            {},
            {
              withCredentials: true,
              headers: {
                "X-CSRFToken": getCookie("csrftoken"),
              },
            },
          );

          const newToken = response.data.data.access;
          console.log("[Interceptor] Token refresh succeeded — replaying queued requests");
          setAuthToken(newToken);
          processQueue(null, newToken);
          return api(originalRequest);
        } catch (err) {
          console.warn("[Interceptor] Token refresh failed — logging out user", err?.response?.status);
          processQueue(err, null);
          useAuthStore.getState().logout();
          return Promise.reject(err);
        } finally {
          isRefreshing = false;
        }
      }

      // ─── 429 rate limit ───────────────────────────────────
      if (status === 429) {
        const retryAfter = error.response?.headers["retry-after"] || 60
        console.warn(`Rate limited. Retry after ${retryAfter}s`)
        // Could implement exponential backoff here later
        return Promise.reject(error)
      }

      // ─── 500 server error ─────────────────────────────────
      if (status >= 500) {
        console.error("Server error:", error.response?.data)
      }

      return Promise.reject(error)
    }
  )
}
