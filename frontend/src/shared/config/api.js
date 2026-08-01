// src/shared/config/api.js

/**
 * VITE_API_ORIGIN = https://backend:8000
 * → Only for Vite proxy (server side config)
 * → NEVER use directly in browser requests!
 *
 * For direct browser requests (token refresh, bootstrap)
 * → Must use localhost (what browser can actually reach)
 */

// ✅ Dynamic - works in all environments automatically
export const DIRECT_API_ORIGIN = `${window.location.protocol}//${window.location.hostname}:8000`;


