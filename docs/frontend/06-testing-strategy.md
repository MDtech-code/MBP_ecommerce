# Frontend Testing Strategy

This document outlines the testing philosophy, stack, and mocking strategies used in the BikeExpress frontend. Our goal is to ensure UI reliability and bulletproof business logic without creating brittle tests.

---

## 1. Testing Stack

* **Runner & Asserter:** Vitest (Fast, Vite-native alternative to Jest).
* **UI Rendering:** React Testing Library (RTL).
* **Environment:** `jsdom` (Simulates a browser environment in Node).
* **Global Setup:** `src/test/setup.js` (Injects custom RTL matchers like `toBeInTheDocument`).

---

## 2. Directory Structure (`src/test/`)

Tests mirror the `src/` directory exactly. 

* **`api/`:** Unit tests for infrastructure (`auth.js`, `transformers.js`). Tests token logic and data unwrapping.
* **`services/`:** Unit tests for endpoint calls. 
* **`stores/`:** Unit tests for global Zustand state (`authStore.test.js`).
* **`hooks/`:** Tests for custom business logic hooks (e.g., testing if `useLoginForm` maps backend errors correctly to fields).
* **`components/` & `pages/`:** Integration tests focusing on UI rendering and user interactions.

---

## 3. The Mocking Philosophy (Crucial Rule)

To prevent cascading test failures, we strictly isolate layers using `vi.mock`.

### Rule 1: Pages mock Hooks
When testing a Page (e.g., `Register.test.jsx`), **do not** make real API calls or deal with React Query providers. Instead, mock the custom hook (`useRegisterForm`) to return specific states (`isPending`, `fieldErrors`) and test if the UI reacts correctly.

### Rule 2: Hooks mock Services & Stores
When testing a Hook (e.g., `useLoginForm.test.jsx`), **do not** make Axios calls. Mock the `accountService.login` function and the `useAuthStore`. Test if the hook correctly calls the service and updates the store on success.

### Rule 3: Services mock Axios (`api/client.js`)
When testing a Service (e.g., `accountService.test.js`), mock the underlying `api.post/get` methods to return the exact envelope shape the backend provides (`{ success, message, data, errors, meta }`).

---

## 4. How to Run Tests

```bash
# Run all tests once
npm run test

# Run tests in watch mode (great for active development)
npm run test:watch

# Open the Vitest UI dashboard in your browser
npm run test:ui
```