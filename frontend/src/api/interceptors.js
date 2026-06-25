// src/api/interceptors.js

import axios from "axios";
import { api } from "./client";
import { setAuthToken, clearAuth,broadcastLogin,broadcastLogout } from "./auth";

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
    failedQueue.forEach((prom) => {
        if (error) {
            prom.reject(error);
        } else {
            prom.resolve(token);
        }
    });

    failedQueue = [];
};

api.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;

        // ✅ 401 handling
        if (error.response?.status === 401 && !originalRequest._retry) {

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
                const response = await axios.post(
                    `${import.meta.env.VITE_API_ORIGIN}/token/refresh/`,
                    {},
                    { withCredentials: true }
                );

                const newAccess = response.data.data.access;

                setAuthToken(newAccess);
                broadcastLogin();
                
                processQueue(null, newAccess);

                return api(originalRequest);

            } catch (err) {
                processQueue(err, null);
                clearAuth();
                broadcastLogout();
                window.location.href = "/login";
                return Promise.reject(err);

            } finally {
                isRefreshing = false;
            }
        }

         // Rate limit handling
         if (error.response?.status === 429) {
             alert("Too many requests. Please slow down.");
             return Promise.reject(error);
         }

        return Promise.reject(error);
    }
);
/*
import axios from "axios";
import { api } from "./client";
import { setAuthToken, clearAuth, broadcastLogout } from "./auth";

let refreshPromise = null;

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = axios
      .post(`${import.meta.env.VITE_API_ORIGIN}/token/refresh/`, {}, { withCredentials: true })
      .then((res) => {
        const newAccess = res.data.data.access;
        setAuthToken(newAccess);
        return newAccess;
      })
      .catch((err) => {
        clearAuth();
        broadcastLogout();
        window.location.href = "/login";
        throw err;
      })
      .finally(() => {
        refreshPromise = null;
      });
  }

  return refreshPromise;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const newAccess = await refreshAccessToken();
        originalRequest.headers.Authorization = `Bearer ${newAccess}`;
        return api(originalRequest);
      } catch (err) {
        return Promise.reject(err);
      }
    }

    if (error.response?.status === 429) {
      alert("Too many requests. Please slow down.");
    }

    return Promise.reject(error);
  }
);
*/