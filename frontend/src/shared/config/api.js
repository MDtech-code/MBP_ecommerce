// src/shared/config/api.js

/**
 * Browser-side API configuration.
 *
 * Environment separation:
 *   - VITE_API_ORIGIN is server-side only (consumed by vite.config.js proxy:
 *     https://localhost:8000 in local dev, https://backend:8000 in Docker).
 *     Never use VITE_API_ORIGIN inside browser code.
 *
 *   - API_BASE_URL is for browser requests:
 *     Defaults to "" (relative paths: /api/..., /media/..., /graphql/) so
 *     requests go through the Vite HTTPS proxy in local/Docker and through
 *     the reverse proxy (Nginx/Cloudflare) in same-origin production.
 *     If production ever hosts the API on a separate domain
 *     (e.g. https://api.bikexpress.com), set VITE_PUBLIC_API_URL.
 */
export const API_BASE_URL = import.meta.env.VITE_PUBLIC_API_URL || "";

export const API_TIMEOUT = 10_000;

export const AUTH_BOOTSTRAP_TIMEOUT = 5_000;
