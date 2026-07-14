
// src/api/interceptors.js
import axios from "axios"
import { api } from "./client"
import { setAuthToken, clearAuth, broadcastLogout,getAuthToken } from "./auth"
import { getCookie } from "../utils/getCsrfToken";

let isRefreshing = false
let failedQueue = []

const processQueue = (error, token = null) => {
  failedQueue.forEach(p => error ? p.reject(error) : p.resolve(token))
  failedQueue = []
}

export const setupInterceptors = () => {

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

      // ─── 401 handling ─────────────────────────────────────
      // Only refresh if it's a token expiry, not invalid credentials
      // Invalid credentials return 401 with specific error code
      if (
        status === 401 &&
        !originalRequest._retry &&
        !originalRequest.url?.includes("/api/accounts/token/refresh/") &&
        errorCode !== "invalid_credentials" // ← fine-grained check
      ) {
        if (isRefreshing) {
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
          console.log("i am from intercepter file ");
          const response = await axios.post(
            `${import.meta.env.VITE_API_ORIGIN}/api/accounts/token/refresh/`,
            {},
            {
              withCredentials: true,
              headers: {
                "X-CSRFToken": getCookie("csrftoken"), // attach CSRF token
              },
            },
          );

          const newToken = response.data.data.access;
          setAuthToken(newToken);
          processQueue(null, newToken);
          return api(originalRequest);
        } catch (err) {
          processQueue(err, null);
          clearAuth();
          broadcastLogout();
          // window.location.href = "/login";
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
