// src/test/pages/account/ForgotPassword.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ForgotPassword from "../../../pages/account/ForgotPassword";

// ─────────────────────────────────────────────────────────────────────────────
// Mock useForgotPasswordForm
// ─────────────────────────────────────────────────────────────────────────────

const handleEmailChange = vi.fn();
const handleSubmit = vi.fn();

let hookState = {
  email: "",
  isPending: false,
  isError: false,
  emailError: null,
  formError: null,
  handleEmailChange,
  handleSubmit,
};

vi.mock(
  "../../../hooks/account/useForgotPasswordForm",
  () => ({
    useForgotPasswordForm: () => hookState,
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
      <ForgotPassword />
    </MemoryRouter>,
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  hookState = {
    email: "",
    isPending: false,
    isError: false,
    emailError: null,
    formError: null,
    handleEmailChange,
    handleSubmit,
  };
});

// ─────────────────────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────────────────────

describe("ForgotPassword Page", () => {
  it("renders heading", () => {
    renderPage();

    expect(
      screen.getByText("Forgot Password?"),
    ).toBeInTheDocument();
  });

  it("renders email input", () => {
    renderPage();

    expect(
      screen.getByPlaceholderText("Enter your email"),
    ).toBeInTheDocument();
  });

  it("renders submit button with default text", () => {
    renderPage();

    expect(
      screen.getByRole("button", {
        name: "SEND RESET LINK",
      }),
    ).toBeInTheDocument();
  });

  it("renders back to login link", () => {
    renderPage();

    expect(
      screen.getByText("Back to Login"),
    ).toBeInTheDocument();
  });

  it("calls handleEmailChange when email input changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByPlaceholderText("Enter your email"),
      { target: { value: "john@test.com" } },
    );

    expect(handleEmailChange).toHaveBeenCalled();
  });

  it("submits the form", () => {
    renderPage();

    fireEvent.submit(
      screen
        .getByRole("button", { name: "SEND RESET LINK" })
        .closest("form"),
    );

    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it("shows pending button text while submitting", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button"),
    ).toHaveTextContent("SENDING...");
  });

  it("disables button while pending", () => {
    hookState.isPending = true;

    renderPage();

    expect(screen.getByRole("button")).toBeDisabled();
  });

  it("shows form level error banner", () => {
    hookState.formError =
      "Too many requests. Try again later.";

    renderPage();

    expect(
      screen.getByText(
        "Too many requests. Try again later.",
      ),
    ).toBeInTheDocument();
  });

  it("does not show error banner when no error", () => {
    renderPage();

    expect(
      screen.queryByText(
        "Too many requests. Try again later.",
      ),
    ).not.toBeInTheDocument();
  });
});