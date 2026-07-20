// src/app/config/test/factories/user.js
//
// Factory functions for user-related test data.
// Every test that needs a user object imports from here.
// Never define inline user objects in test files.
//
// Pattern: createX(overrides = {}) — caller only specifies what differs.

// ── User ──────────────────────────────────────────────────────────────────────
export const createUser = (overrides = {}) => ({
  id: 1,
  email: "testuser@example.com",
  full_name: "Test User",
  is_verified: true,
  is_active: true,
  date_joined: "2024-01-01T00:00:00Z",
  profile: {
    avatar: null,
    phone: null,
    date_of_birth: null,
  },
  addresses: [],
  ...overrides,
});

// ── Unverified user ───────────────────────────────────────────────────────────
// Shorthand for the common test case of email not verified yet
export const createUnverifiedUser = (overrides = {}) =>
  createUser({ is_verified: false, ...overrides });

// ── Address ───────────────────────────────────────────────────────────────────
export const createAddress = (overrides = {}) => ({
  id: 1,
  label: "Home",
  address_line1: "123 Main Street",
  address_line2: "",
  city: "Lahore",
  province: "Punjab",
  postal_code: "54000",
  country: "Pakistan",
  is_default: true,
  ...overrides,
});

// ── User with addresses ───────────────────────────────────────────────────────
export const createUserWithAddresses = (addresses = [], overrides = {}) =>
  createUser({
    addresses: addresses.length ? addresses : [createAddress()],
    ...overrides,
  });

// ── Login response ────────────────────────────────────────────────────────────
// Shape returned by POST /api/accounts/login/ → extractResponse → data
export const createLoginResponseData = (overrides = {}) => ({
  access: "fake-access-token-abc123",
  user: createUser(),
  ...overrides,
});

// ── Zustand store seeder ──────────────────────────────────────────────────────
// Use in beforeEach to seed auth state for tests needing authenticated user.
//
// Usage:
//   import { seedAuthStore } from '@app/config/test/factories/user'
//   beforeEach(() => seedAuthStore())
//   beforeEach(() => seedAuthStore({ user: createUser({ is_verified: false }) }))
export const seedAuthStore = async (options = {}) => {
  // Import dynamically to avoid circular deps at module load time
  //   const { useAuthStore } = require("@entities/user");
  const { useAuthStore } = await import("@entities/user");
  useAuthStore.setState({
    user: options.user ?? createUser(),
    isAuthenticated: options.isAuthenticated ?? true,
    isBootstrapping: options.isBootstrapping ?? false,
  });
};
