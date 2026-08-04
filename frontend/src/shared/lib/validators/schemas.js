// shared/lib/validators/schemas.js
//
// Form schemas — bind fields to ordered rule arrays.
// One schema per form that has client-side validation.
//
// Cross-field rules (matchesField) are DYNAMIC — they need current form state.
// So schemas that contain cross-field rules are FUNCTIONS that receive form
// values and return the schema object. Pure schemas are plain objects.
//
// Naming convention:
//   registerSchema(form)   ← function, needs form.password for confirm check
//   loginSchema            ← plain object, no cross-field dependency

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