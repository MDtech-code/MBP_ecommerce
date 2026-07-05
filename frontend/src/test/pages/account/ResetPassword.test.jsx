// src/test/pages/account/ResetPassword.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ResetPassword from "../../../pages/account/ResetPassword";

// ─────────────────────────────────────────────────────────────────────────────
// Mock useResetPasswordForm
// ─────────────────────────────────────────────────────────────────────────────

const handleChange = vi.fn();
const handleSubmit = vi.fn();

let hookState = {
  fields: {
    password: "",
    confirm_password: "",
  },
  isPending: false,
  passwordError: null,
  confirmPasswordError: null,
  formError: null,
  tokenMissing: false,
  handleChange,
  handleSubmit,
};

vi.mock(
  "../../../hooks/account/useResetPasswordForm",
  () => ({
    useResetPasswordForm: () => hookState,
  }),
);

// ─────────────────────────────────────────────────────────────────────────────
// Mock AuthLayout
// ─────────────────────────────────────────────────────────────────────────────

vi.mock(
  "../../../components/account/AuthLayout",
  () => ({
    default: ({ children }) => (
      <div data-testid="auth-layout">{children}</div>
    ),
  }),
);

// ─────────────────────────────────────────────────────────────────────────────
// Helper
// ─────────────────────────────────────────────────────────────────────────────

function renderPage() {
  return render(
    <MemoryRouter>
      <ResetPassword />
    </MemoryRouter>,
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  hookState = {
    fields: {
      password: "",
      confirm_password: "",
    },
    isPending: false,
    passwordError: null,
    confirmPasswordError: null,
    formError: null,
    tokenMissing: false,
    handleChange,
    handleSubmit,
  };
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("ResetPassword Page", () => {
  it("renders heading", () => {
    renderPage();

    expect(
      screen.getByText("Reset Password"),
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

  it("renders submit button with default text", () => {
    renderPage();

    expect(
      screen.getByRole("button", { name: "RESET PASSWORD" }),
    ).toBeInTheDocument();
  });

  it("calls handleChange when password input changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Enter new password"),
      { target: { value: "NewPass123!" } },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("calls handleChange when confirm password input changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Confirm new password"),
      { target: { value: "NewPass123!" } },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("submits the form", () => {
    renderPage();

    fireEvent.submit(
      screen
        .getByRole("button", { name: "RESET PASSWORD" })
        .closest("form"),
    );

    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it("shows pending button text while submitting", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button", { name: "RESETTING..." }),
    ).toBeInTheDocument();
  });

  it("disables button while pending", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button", { name: "RESETTING..." }),
    ).toBeDisabled();
  });

  it("shows form level error banner", () => {
    hookState.formError = "Invalid or expired token.";

    renderPage();

    expect(
      screen.getByText("Invalid or expired token."),
    ).toBeInTheDocument();
  });

  it("shows invalid link screen when token is missing", () => {
    hookState.tokenMissing = true;

    renderPage();

    expect(
      screen.getByText("REQUEST NEW LINK"),
    ).toBeInTheDocument();

    expect(
      screen.getByText(
        "This reset link is invalid or has expired. Please request a new one.",
      ),
    ).toBeInTheDocument();
  });

  it("does not show the form when token is missing", () => {
    hookState.tokenMissing = true;

    renderPage();

    expect(
      screen.queryByPlaceholderText("Enter new password"),
    ).not.toBeInTheDocument();
  });
});