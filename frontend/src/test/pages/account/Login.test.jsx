// src/test/pages/account/Login.test.jsx

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "../../../pages/account/Login";

// ─────────────────────────────────────────────────────────────
// Mock useLoginForm
// ─────────────────────────────────────────────────────────────

const handleChange = vi.fn();
const handleSubmit = vi.fn();

let hookState = {
  form: {
    email: "",
    password: "",
  },
  fieldErrors: {
    email: null,
    password: null,
  },
  formError: null,
  isPending: false,
  handleChange,
  handleSubmit,
};

vi.mock("../../../hooks/account/useLoginForm", () => ({
  useLoginForm: () => hookState,
}));

// ─────────────────────────────────────────────────────────────
// Mock AuthLayout
// ─────────────────────────────────────────────────────────────

vi.mock("../../../components/account/AuthLayout", () => ({
  default: ({ children }) => (
    <div data-testid="auth-layout">{children}</div>
  ),
}));

// ─────────────────────────────────────────────────────────────
// Mock SocialLogin
// ─────────────────────────────────────────────────────────────

vi.mock("../../../components/account/SocialLogin", () => ({
  default: () => (
    <div data-testid="social-login">
      Social Login
    </div>
  ),
}));

// ─────────────────────────────────────────────────────────────
// Mock FormInput
// ─────────────────────────────────────────────────────────────

vi.mock("../../../components/common/FormInput", () => ({
  default: ({
    name,
    type,
    value,
    onChange,
    error,
    placeholder,
  }) => (
    <div>
      <input
        data-testid={name}
        name={name}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
      />

      {error && (
        <span data-testid={`${name}-error`}>
          {error}
        </span>
      )}
    </div>
  ),
}));

// ─────────────────────────────────────────────────────────────
// Helper
// ─────────────────────────────────────────────────────────────

function renderPage() {
  return render(
    <MemoryRouter>
      <Login />
    </MemoryRouter>,
  );
}

// ─────────────────────────────────────────────────────────────
// Reset
// ─────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  hookState = {
    form: {
      email: "",
      password: "",
    },
    fieldErrors: {
      email: null,
      password: null,
    },
    formError: null,
    isPending: false,
    handleChange,
    handleSubmit,
  };
});

// ─────────────────────────────────────────────────────────────
// Tests
// ─────────────────────────────────────────────────────────────

describe("Login Page", () => {
  it("renders login heading", () => {
    renderPage();

    expect(
      screen.getByText("Welcome Back"),
    ).toBeInTheDocument();
  });

  it("renders email input", () => {
    renderPage();

    expect(
      screen.getByTestId("email"),
    ).toBeInTheDocument();
  });

  it("renders password input", () => {
    renderPage();

    expect(
      screen.getByTestId("password"),
    ).toBeInTheDocument();
  });

  it("renders social login section", () => {
    renderPage();

    expect(
      screen.getByTestId("social-login"),
    ).toBeInTheDocument();
  });

  it("renders login button", () => {
    renderPage();

    expect(
      screen.getByRole("button", {
        name: "LOGIN",
      }),
    ).toBeInTheDocument();
  });

  it("calls handleChange when email changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByTestId("email"),
      {
        target: {
          value: "john@test.com",
        },
      },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("calls handleChange when password changes", () => {
    renderPage();

    fireEvent.change(
      screen.getByTestId("password"),
      {
        target: {
          value: "password123",
        },
      },
    );

    expect(handleChange).toHaveBeenCalled();
  });

  it("submits the form", () => {
    renderPage();

    fireEvent.submit(
      screen.getByRole("button", {
        name: "LOGIN",
      }).closest("form"),
    );

    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  it("shows pending button text", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button"),
    ).toHaveTextContent(
      "LOGGING IN...",
    );
  });

  it("disables button while pending", () => {
    hookState.isPending = true;

    renderPage();

    expect(
      screen.getByRole("button"),
    ).toBeDisabled();
  });

  it("shows form level error", () => {
    hookState.formError =
      "Invalid email or password.";

    renderPage();

    expect(
      screen.getByRole("alert"),
    ).toHaveTextContent(
      "Invalid email or password.",
    );
  });

  it("shows email validation error", () => {
    hookState.fieldErrors.email =
      "Email is required.";

    renderPage();

    expect(
      screen.getByTestId("email-error"),
    ).toHaveTextContent(
      "Email is required.",
    );
  });

  it("shows password validation error", () => {
    hookState.fieldErrors.password =
      "Password is required.";

    renderPage();

    expect(
      screen.getByTestId("password-error"),
    ).toHaveTextContent(
      "Password is required.",
    );
  });

  it("renders forgot password link", () => {
    renderPage();

    expect(
      screen.getByText(
        "Forgot Password?",
      ),
    ).toBeInTheDocument();
  });

  it("renders register link", () => {
    renderPage();

    expect(
      screen.getByText(
        "Create Account",
      ),
    ).toBeInTheDocument();
  });
});