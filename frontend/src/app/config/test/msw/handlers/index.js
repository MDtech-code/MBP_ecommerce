// src/app/config/test/msw/handlers/index.js
//
// Combines all domain handlers into one array for the MSW server.
// Add new handler files here as new features are built.
// Order matters — MSW matches the first handler that fits.
// Put more specific handlers before general ones if there is overlap.

import { authHandlers } from "./auth";
import { cartHandlers } from "./cart";
import { productHandlers } from "./products";

export const handlers = [...authHandlers, ...cartHandlers, ...productHandlers];
