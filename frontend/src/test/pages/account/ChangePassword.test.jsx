// src/test/pages/account/ChangePassword.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

// ─────────────────────────────────────────────────────────────────────────────
// Mock useChangePasswordForm
// Must be mocked BEFORE the component is imported so the real hook
// (which calls useMutation and needs QueryClientProvider) never runs
// ─────────────────────────────────────────────────────────────────────────────

const handleChange = vi.fn();
const handleSubmit = vi.fn();

let hookState = {
  fields: {
    current_password: "",
    new_password: "",
    confirm_new_password: "",
  },
  isPending: false,
  isSuccess: false,
  currentPasswordError: null,
  newPasswordError: null,
  confirmNewPasswordError: null,
  formError: null,
  handleChange,
  handleSubmit,
};

vi.mock(
  "../../../hooks/account/useChangePasswordForm",
  () => ({
    useChangePasswordForm: () => hookState,
  }),
);

// ─────────────────────────────────────────────────────────────────────────────
// Mock DashboardLayout
// ─────────────────────────────────────────────────────────────────────────────

vi.mock(
  "../../../components/account/DashboardLayout",
  () => ({
    default: ({ children }) => (
      <div data-testid="dashboard-layout">{children}</div>
    ),
  }),
);

// ─────────────────────────────────────────────────────────────────────────────
// Mock PasswordStrength
// ─────────────────────────────────────────────────────────────────────────────

vi.mock(
  "../../../components/account/security/PasswordStrength",
  () => ({
    default: ({ password }) => (
      <div data-testid="password-strength">
        strength-for:{password}
      </div>
    ),
  }),
);

// ─────────────────────────────────────────────────────────────────────────────
// Import component AFTER mocks are registered
// ─────────────────────────────────────────────────────────────────────────────

import ChangePassword from "../../../pages/account/security/ChangePassword";

// ─────────────────────────────────────────────────────────────────────────────
// Helper — QueryClientProvider included as safety net
// ─────────────────────────────────────────────────────────────────────────────

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ChangePassword />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  hookState = {
    fields: {
      current_password: "",
      new_password: "",
      confirm_new_password: "",
    },
    isPending: false,
    isSuccess: false,
    currentPasswordError: null,
    newPasswordError: null,
    confirmNewPasswordError: null,
    formError: null,
    handleChange,
    handleSubmit,
  };
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("ChangePassword Page", () => {
  it("renders inside dashboard layout", () => {
    renderPage();

    expect(
      screen.getByTestId("dashboard-layout"),
    ).toBeInTheDocument();
  });

  it("renders heading", () => {
    renderPage();

    expect(
      screen.getByText("Change Password"),
    ).toBeInTheDocument();
  });

  it("renders current password input", () => {
    renderPage();

    expect(
      screen.getByPlaceholderText("Enter current password"),
    ).toBeInTheDocument();
  });

  it("renders new password input", () => {
    renderPage();

    expect(
      screen.getByPlaceholderText("Enter new password"),
    ).toBeInTheDocument();
  });

  it("renders confirm password input", () => {
    renderPage();

    expect(
      screen.getByPlaceholderText("Confirm new password"),
    ).toBeInTheDocument();
  });

  it("renders password strength component", () => {
    renderPage();

    expect(
      screen.getByTestId("password-strength"),
    ).toBeInTheDocument();
  });

  it("passes new_password value to PasswordStrength", () => {
    hookState.fields.new_password = "TypedPass1!";

    renderPage();

    expect(
      screen.getByTestId("password-strength"),
    ).toHaveTextContent("strength-for:TypedPass1!");
  });

  it("renders update password button", () => {
    renderPage();

    expect(
      screen.getByRole("button", { name: "Update Password" }),
    ).toBeInTheDocument();
  });

  it("calls handleChange when current password changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Enter current password"),
      { target: { value: "OldPass123!" } },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("calls handleChange when new password changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Enter new password"),
      { target: { value: "NewPass456!" } },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("calls handleChange when confirm password changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Confirm new password"),
      { target: { value: "NewPass456!" } },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("submits the form when update button clicked", () => {
    renderPage();

    fireEvent.submit(
      screen
        .getByRole("button", { name: "Update Password" })
        .closest("form"),
    );

    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it("shows pending button text while submitting", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button", { name: "Updating..." }),
    ).toBeInTheDocument();
  });

  it("disables update button while pending", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button", { name: "Updating..." }),
    ).toBeDisabled();
  });

  it("shows form level error banner", () => {
    hookState.formError = "Current password is incorrect.";

    renderPage();

    expect(
      screen.getByText("Current password is incorrect."),
    ).toBeInTheDocument();
  });

  it("does not show error banner when no error", () => {
    renderPage();

    expect(
      screen.queryByText("Current password is incorrect."),
    ).not.toBeInTheDocument();
  });

  it("shows current password field error", () => {
    hookState.currentPasswordError =
      "Current password is incorrect.";

    renderPage();

    expect(
      screen.getByText("Current password is incorrect."),
    ).toBeInTheDocument();
  });

  it("shows new password field error", () => {
    hookState.newPasswordError =
      "Password must be at least 8 characters.";

    renderPage();

    expect(
      screen.getByText(
        "Password must be at least 8 characters.",
      ),
    ).toBeInTheDocument();
  });

  it("shows confirm new password field error", () => {
    hookState.confirmNewPasswordError =
      "Passwords do not match.";

    renderPage();

    expect(
      screen.getByText("Passwords do not match."),
    ).toBeInTheDocument();
  });
});