// src/app/config/test/server.js
// MSW request boundary for the Vitest suite.
//
// Policy: an unhandled request is an ERROR, not a passthrough. Every test must
// declare the traffic it expects with `server.use(...)`, so a test can never
// silently reach the real network or another test's handler.
//
// jsdom runs at https://shop.example.test/ (see vitest.config.js
// `environmentOptions.jsdom.url`), so relative axios calls are intercepted as
// absolute URLs on that origin.

import { setupServer } from "msw/node";
import { afterAll, afterEach, beforeAll } from "vitest";

export const server = setupServer();

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

// Per-test handlers never leak into the next test.
afterEach(() => {
  server.resetHandlers();
});

afterAll(() => {
  server.close();
});
