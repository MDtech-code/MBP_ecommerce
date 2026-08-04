// src/shared/lib/cookies.js

/**
 * Get a cookie value by name and parse it as JSON if possible.
 * @param {string} name - The cookie name
 * @returns {any|null} - The parsed value or null if not found
 */
export const getCookie = (name) => {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) {
    const raw = parts.pop().split(";").shift();
    try {
      return JSON.parse(decodeURIComponent(raw));
    } catch {
      return decodeURIComponent(raw); // fallback to string
    }
  }
  return null;
};

/**
 * Set a cookie with any JSON‑serializable value.
 * @param {string} name
 * @param {any} value
 * @param {Object} options - { maxAge, path, secure, sameSite }
 */
export const setCookie = (name, value, options = {}) => {
  const encoded = encodeURIComponent(
    typeof value === "string" ? value : JSON.stringify(value)
  );
  let cookie = `${name}=${encoded}`;
  if (options.maxAge) cookie += `; max-age=${options.maxAge}`;
  if (options.path) cookie += `; path=${options.path}`;
  if (options.secure) cookie += `; secure`;
  if (options.sameSite) cookie += `; samesite=${options.sameSite}`;
  document.cookie = cookie;
};

/**
 * Clear a cookie by name.
 * @param {string} name
 * @param {string} path
 */
export const clearCookie = (name, path = "/") => {
  document.cookie = `${name}=; Max-Age=0; path=${path}`;
};
