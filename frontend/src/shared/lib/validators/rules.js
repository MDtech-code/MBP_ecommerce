// shared/lib/validators/rules.js




/**
 *
 * @param {string} value
 * @returns {string|null}
 */
export const required = (value) => {
  if (!value || !String(value).trim()) {
    return "This field is required.";
  }
  return null;
};

/**
 * @param {string} value
 * @returns {string|null}
 */
export const emailFormat = (value) => {
  if (!value) return null;
  const pattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  if (!pattern.test(String(value).trim())) {
    return "Enter a valid email address.";
  }
  return null;
};

/**
 
 * @param {string} value
 * @returns {string|null}
 */
export const fullName = (value) => {
  if (!value) return null;
  const normalized = String(value).trim().replace(/\s+/g, " ");
  if (normalized.split(" ").length < 2) {
    return "Please enter your full name (first and last name).";
  }
  return null;
};

/**
 *
 * @param {string} value
 * @returns {string|null}
 */
export const strongPassword = (value) => {
  if (!value) return null; 

  if (value.length < 8) {
    return "Password must be at least 8 characters long.";
  }

  if (/^\d+$/.test(value)) {
    return "Password cannot be entirely numeric.";
  }

  return null;
};

/**
 * @param {string} value
 * @returns {string|null}
 */
export const pakistaniPhone = (value) => {
  if (!value || !String(value).trim()) return null; 
  const pattern = /^\+?92\d{10}$|^0\d{10}$/;
  if (!pattern.test(String(value).trim())) {
    return "Enter a valid Pakistani phone number. Format: +923001234567 or 03001234567";
  }
  return null;
};

/**
 * @param {string} 
 * @returns {(value: string) => string|null}
 */
export const matchesField = (otherValue) => (value) => {
  if (!value) return null; 
  if (value !== otherValue) {
    return "Passwords do not match.";
  }
  return null;
};

/**

 * @param {File} file
 * @returns {string|null}
 */
export const imageMaxSize = (file) => {
  if (!file) return null;
  const maxBytes = 2 * 1024 * 1024;
  if (file.size > maxBytes) {
    return "Image size must not exceed 2MB.";
  }
  return null;
};

/**
 
 * @param {File} file
 * @returns {string|null}
 */
export const imageAllowedType = (file) => {
  if (!file) return null;
  const allowed = ["image/jpeg", "image/png", "image/webp"];
  if (!allowed.includes(file.type)) {
    return "Only JPEG, PNG and WebP images are allowed.";
  }
  return null;
};