// shared/lib/validators/index.js



export { run, hasErrors } from "./validate";
export { registerSchema, loginSchema, phoneSchema } from "./schemas";


export {
  required,
  emailFormat,
  fullName,
  strongPassword,
  matchesField,
  pakistaniPhone,
  imageMaxSize,
  imageAllowedType,
} from "./rules";