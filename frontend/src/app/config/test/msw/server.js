// src/app/config/test/msw/server.js
//
// Single MSW server instance shared across all tests.
// Imported in setup.js — do not import directly in test files.
// To override a handler in a test: import { server } and call server.use(...)

import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
