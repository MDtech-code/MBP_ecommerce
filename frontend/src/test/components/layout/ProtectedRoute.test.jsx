// src/test/components/layout/ProtectedRoute.test.jsx

import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import {
  MemoryRouter,
  Routes,
  Route,
} from "react-router-dom";

import ProtectedRoute from "../../../components/layout/ProtectedRoute";

// ────────────────────────────────────────────────────────────────
// Mock auth.js
// ────────────────────────────────────────────────────────────────
const { hasAuthToken } = vi.hoisted(() => ({
  hasAuthToken: vi.fn(),
}));


vi.mock("../../../api/auth", () => ({
  hasAuthToken:vi.fn(),
}));

// ────────────────────────────────────────────────────────────────
// Mock Zustand
// ────────────────────────────────────────────────────────────────

let authState = {
  isAuthenticated: false,
  isBootstrapping: false,
};

vi.mock("../../../stores/authStore", () => ({
  useAuthStore: (selector) => selector(authState),
}));

// ────────────────────────────────────────────────────────────────
// Helper
// ────────────────────────────────────────────────────────────────

function renderProtected(initialRoute = "/profile") {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <Routes>
        <Route element={<ProtectedRoute />}>
          <Route
            path="/profile"
            element={<div>Protected Profile</div>}
          />
        </Route>

        <Route
          path="/login"
          element={<div>Login Page</div>}
        />
      </Routes>
    </MemoryRouter>,
  );
}

// ────────────────────────────────────────────────────────────────
// Reset
// ────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  authState = {
    isAuthenticated: false,
    isBootstrapping: false,
  };

  hasAuthToken.mockReturnValue(false);
});

// ────────────────────────────────────────────────────────────────
// Tests
// ────────────────────────────────────────────────────────────────

describe("ProtectedRoute", () => {
  it("shows nothing while bootstrapping", () => {
    authState.isBootstrapping = true;

    const { container } = renderProtected();

    expect(container).toBeEmptyDOMElement();
  });

  it("redirects to login when user is unauthenticated and has no token", () => {
    authState.isAuthenticated = false;
    hasAuthToken.mockReturnValue(false);

    renderProtected();

    expect(
      screen.getByText("Login Page"),
    ).toBeInTheDocument();
  });

  it("renders protected page when Zustand says authenticated", () => {
    authState.isAuthenticated = true;

    renderProtected();

    expect(
      screen.getByText("Protected Profile"),
    ).toBeInTheDocument();
  });

  it("renders protected page when access token exists", () => {
    authState.isAuthenticated = false;
    hasAuthToken.mockReturnValue(true);

    renderProtected();

    expect(
      screen.getByText("Protected Profile"),
    ).toBeInTheDocument();
  });

  it("does not redirect while bootstrapping even without token", () => {
    authState.isBootstrapping = true;
    hasAuthToken.mockReturnValue(false);

    const { container } = renderProtected();

    expect(container).toBeEmptyDOMElement();

    expect(
      screen.queryByText("Login Page"),
    ).not.toBeInTheDocument();
  });

  it("prefers loading state over redirect", () => {
    authState.isBootstrapping = true;
    authState.isAuthenticated = false;
    hasAuthToken.mockReturnValue(false);

    const { container } = renderProtected();

    expect(container).toBeEmptyDOMElement();
  });
});