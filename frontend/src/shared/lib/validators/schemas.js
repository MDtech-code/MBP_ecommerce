// shared/lib/validators/schemas.js


import {
  required,
  emailFormat,
  fullName,
  strongPassword,
  matchesField,
  pakistaniPhone,
} from "./rules";

/**
 * Register form schema.
 * Receives current form values because confirm_password needs form.password.
 *
 * @param {{ password: string }} form
 * @returns {Record<string, Array<Function>>}
 */
export const registerSchema = (form) => ({
  full_name: [required, fullName],
  email: [required, emailFormat],
  password: [required, strongPassword],
  confirm_password: [required, matchesField(form.password)],
});

/**
 * Login form schema.
 */
export const loginSchema = {
  email: [required, emailFormat],
  password: [required],
};

/**
 * Profile phone update schema.
 */
export const phoneSchema = {
  phone: [required, pakistaniPhone],
};