// shared/lib/validators/validate.js


/**
 * Run all rules for a single field value.
 * Returns the first error message or null if all pass.
 *
 * @param {Array<Function>} rules
 * @param {any} value
 * @returns {string|null}
 */


const runField = (rules, value) => {
  for (const rule of rules) {
    const error = rule(value);
    if (error !== null) return error;
  }
  return null;
};

/**
 * Run a full schema against form values.
 *
 * @param {Record<string, Array<Function>>} schema
 * @param {Record<string, any>} values
 * @returns {Record<string, { message: string, code: null }>}
 */
export const run = (schema, values) => {
  const errors = {};

  for (const [field, rules] of Object.entries(schema)) {
    const message = runField(rules, values[field]);
    if (message !== null) {
      errors[field] = {
        message,
        code: null, // client errors have no backend code — UI treats null as no special action
      };
    }
  }

  return errors;
};

/**
 * Check if a run() result has any errors.
 *
 * @param {Record<string, any>} fieldErrors
 * @returns {boolean}
 */
export const hasErrors = (fieldErrors) => Object.keys(fieldErrors).length > 0;