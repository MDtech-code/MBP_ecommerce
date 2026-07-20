// src/app/config/test/setup.js
//
// Runs once before every test file.
// Keeps tests isolated and predictable.

import "@testing-library/jest-dom";
import { server } from "./msw/server";
import { useAuthStore } from "@entities/user";
import { clearAuth } from "@shared/lib";
import { beforeAll,afterEach,afterAll } from "vitest";

// ── MSW lifecycle ─────────────────────────────────────────────────────────────
// Start the mock server before all tests.
// Reset handlers after each test so overrides don't bleed across tests.
// Close the server after all tests finish.
beforeAll(() => server.listen({ onUnhandledRequest: "warn" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// ── Zustand reset ─────────────────────────────────────────────────────────────
// authStore uses plain create() (no persist middleware).
// Reset to initial state after every test to prevent state bleed.
afterEach(() => {
  useAuthStore.setState({
    user: null,
    isAuthenticated: false,
    isBootstrapping: false, // false in tests — bootstrap doesn't run
  });
  clearAuth(); // clear in-memory access token
});

// ── Storage reset ─────────────────────────────────────────────────────────────
// Clear any localStorage/sessionStorage written by features
afterEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});
