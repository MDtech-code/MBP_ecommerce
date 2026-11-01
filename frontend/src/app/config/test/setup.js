// src/app/config/test/setup.js
// Vitest global setup — sourced from vitest.config.js `test.setupFiles`.
// Wired in now so that `npm run test` boots; individual tests still need the
// MSW server (src/app/config/test/server.js) before they can run.

import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Cookies are global in jsdom and survive between tests. Every test here starts
// from a clean browser session, so a token set by one test can never satisfy the
// CSRF guard in the next one.
function clearCookies() {
  for (const cookie of document.cookie.split(';')) {
    const name = cookie.split('=')[0].trim();
    if (name) {
      document.cookie = `${name}=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT`;
    }
  }
  sessionStorage.clear();
  localStorage.clear();
}

afterEach(() => {
  cleanup();
  clearCookies();
});

// jsdom does not implement matchMedia; theme code and daisyUI read it.
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
