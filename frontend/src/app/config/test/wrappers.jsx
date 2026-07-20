// src/app/config/test/wrappers.jsx
//
// Reusable React wrappers for renderHook and render calls.
// Every test that needs QueryClient or Router imports from here.
// Never create a QueryClient inside a test file directly.

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { render } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { createUser } from "./factories/user";

// ── QueryClient factory ────────────────────────────────────────────────────────
// Creates a fresh QueryClient per test.
// retry: false — tests should not retry failed requests.
// gcTime: 0   — no caching between tests.
export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// ── Hook wrapper ───────────────────────────────────────────────────────────────
// Use for renderHook() calls.
// Provides QueryClient only — no router.
// Add MemoryRouter inside if the hook uses useNavigate/useSearchParams.
//
// Usage:
//   const { result } = renderHook(() => useLoginForm(), {
//     wrapper: createWrapper(),
//   });
export function createWrapper(options = {}) {
  const queryClient = createTestQueryClient();
  return function Wrapper({ children }) {
    return (
      <QueryClientProvider client={queryClient}>
        {options.route !== undefined ? (
          <MemoryRouter initialEntries={[options.route]}>
            {children}
          </MemoryRouter>
        ) : (
          // Most hooks need router for useNavigate — default to "/" route
          <MemoryRouter initialEntries={[options.initialRoute ?? "/"]}>
            {children}
          </MemoryRouter>
        )}
      </QueryClientProvider>
    );
  };
}

// ── Component wrapper ──────────────────────────────────────────────────────────
// Use for render() calls on widgets and pages.
//
// Usage:
//   renderWithProviders(<LoginPage />, { route: "/login" });
export function renderWithProviders(ui, options = {}) {
  return render(ui, {
    wrapper: createWrapper(options),
    ...options,
  });
}

// ── Hook render shorthand ──────────────────────────────────────────────────────
// Shorthand for renderHook with wrapper already applied.
//
// Usage:
//   const { result } = renderHookWithProviders(() => useLoginForm());
export function renderHookWithProviders(hook, options = {}) {
  return renderHook(hook, {
    wrapper: createWrapper(options),
    ...options,
  });
}

// ── Authenticated wrapper ──────────────────────────────────────────────────────
// Pre-seeds Zustand authStore with a logged-in user.
// Use for tests that need an authenticated context.
//
// Usage:
//   const { result } = renderHookWithProviders(
//     () => useProfileForm(),
//     { wrapper: createAuthenticatedWrapper({ user: createUser() }) }
//   );
export async function createAuthenticatedWrapper( options = {}) {
//   const { useAuthStore } = require("@entities/user");
  const { useAuthStore } = await import("@entities/user");
//   const { createUser } = require("./factories/user");

  useAuthStore.setState({
    user: options.user ?? createUser(),
    isAuthenticated: true,
    isBootstrapping: false,
  });

  return createWrapper(options);
}
