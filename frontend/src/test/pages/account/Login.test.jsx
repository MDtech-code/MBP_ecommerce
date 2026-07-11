// src/test/pages/account/Login.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "../../../pages/account/Login";

// ─── Mocks ────────────────────────────────────────────────────────────────────

const handleChange  = vi.fn();
const handleSubmit  = vi.fn();
const handleResend  = vi.fn();

// Default hook state — includes ALL fields the updated hook returns
let hookState = {
  form:            { email: "", password: "" },
  fieldErrors:     { email: null, password: null },
  formError:       null,
  formErrorCode:   null,    // ← NEW
  isPending:       false,
  isResending:     false,   // ← NEW
  isResendSuccess: false,   // ← NEW
  handleChange,
  handleSubmit,
  handleResend,             // ← NEW
};

vi.mock("../../../hooks/account/useLoginForm", () => ({
  useLoginForm: () => hookState,
}));

vi.mock("../../../components/account/AuthLayout", () => ({
  default: ({ children }) => <div data-testid="auth-layout">{children}</div>,
}));

vi.mock("../../../components/account/SocialLogin", () => ({
  default: () => <div data-testid="social-login">Social Login</div>,
}));

vi.mock("../../../components/common/FormInput", () => ({
  default: ({ name, type, value, onChange, error, placeholder }) => (
    <div>
      <input
        data-testid={name}
        name={name}
        type={type}
        value={value}
        placeholder={placeholder}
        onChange={onChange}
      />
      {error && <span data-testid={`${name}-error`}>{error}</span>}
    </div>
  ),
}));

// Mock ErrorCode so Login.jsx import works
vi.mock("../../../api/transformers", () => ({
  ErrorCode: {
    EMAIL_NOT_VERIFIED: "email_not_verified",
  },
}));

// ─── Helper ───────────────────────────────────────────────────────────────────

function renderPage() {
  return render(<MemoryRouter><Login /></MemoryRouter>);
}

// ─── Reset ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  hookState = {
    form:            { email: "", password: "" },
    fieldErrors:     { email: null, password: null },
    formError:       null,
    formErrorCode:   null,
    isPending:       false,
    isResending:     false,
    isResendSuccess: false,
    handleChange,
    handleSubmit,
    handleResend,
  };
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Login Page", () => {

  // ── Renders ────────────────────────────────────────────────────────────────

  it("renders login heading", () => {
    renderPage();
    expect(screen.getByText("Welcome Back")).toBeInTheDocument();
  });

  it("renders email input", () => {
    renderPage();
    expect(screen.getByTestId("email")).toBeInTheDocument();
  });

  it("renders password input", () => {
    renderPage();
    expect(screen.getByTestId("password")).toBeInTheDocument();
  });

  it("renders social login section", () => {
    renderPage();
    expect(screen.getByTestId("social-login")).toBeInTheDocument();
  });

  it("renders login button", () => {
    renderPage();
    expect(screen.getByRole("button", { name: "LOGIN" })).toBeInTheDocument();
  });

  it("renders forgot password link", () => {
    renderPage();
    expect(screen.getByText("Forgot Password?")).toBeInTheDocument();
  });

  it("renders register link", () => {
    renderPage();
    expect(screen.getByText("Create Account")).toBeInTheDocument();
  });

  // ── Interactions ───────────────────────────────────────────────────────────

  it("calls handleChange when email changes", () => {
    renderPage();
    fireEvent.change(screen.getByTestId("email"), { target: { value: "john@test.com" } });
    expect(handleChange).toHaveBeenCalled();
  });

  it("calls handleChange when password changes", () => {
    renderPage();
    fireEvent.change(screen.getByTestId("password"), { target: { value: "password123" } });
    expect(handleChange).toHaveBeenCalled();
  });

  it("submits the form", () => {
    renderPage();
    fireEvent.submit(screen.getByRole("button", { name: "LOGIN" }).closest("form"));
    expect(handleSubmit).toHaveBeenCalledTimes(1);
  });

  // ── Loading state ──────────────────────────────────────────────────────────

  it("shows pending button text", () => {
    hookState.isPending = true;
    renderPage();
    expect(screen.getByRole("button", { name: /logging in/i })).toBeInTheDocument();
  });

  it("disables button while pending", () => {
    hookState.isPending = true;
    renderPage();
    expect(screen.getByRole("button", { name: /logging in/i })).toBeDisabled();
  });

  // ── Error banner ───────────────────────────────────────────────────────────

  it("shows form level error banner", () => {
    hookState.formError = "Invalid email or password.";
    renderPage();
    expect(screen.getByRole("alert")).toHaveTextContent("Invalid email or password.");
  });

  it("does not show error banner when formError is null", () => {
    renderPage();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows field email error", () => {
    hookState.fieldErrors.email = "Email is required.";
    renderPage();
    expect(screen.getByTestId("email-error")).toHaveTextContent("Email is required.");
  });

  it("shows field password error", () => {
    hookState.fieldErrors.password = "Password is required.";
    renderPage();
    expect(screen.getByTestId("password-error")).toHaveTextContent("Password is required.");
  });

  // ── Resend button — email_not_verified ─────────────────────────────────────

  it("shows resend button when formErrorCode is email_not_verified", () => {
    hookState.formError     = "Please verify your email address before logging in.";
    hookState.formErrorCode = "email_not_verified";
    renderPage();
    expect(screen.getByRole("button", { name: /resend verification email/i }))
      .toBeInTheDocument();
  });

  it("does not show resend button for other error codes", () => {
    hookState.formError     = "Invalid email or password.";
    hookState.formErrorCode = "invalid_credentials";
    renderPage();
    expect(screen.queryByRole("button", { name: /resend/i })).not.toBeInTheDocument();
  });

  it("calls handleResend when resend button clicked", () => {
    hookState.formError     = "Please verify your email.";
    hookState.formErrorCode = "email_not_verified";
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: /resend verification email/i }));
    expect(handleResend).toHaveBeenCalledTimes(1);
  });

  it("disables resend button while isResending", () => {
    hookState.formError     = "Please verify your email.";
    hookState.formErrorCode = "email_not_verified";
    hookState.isResending   = true;
    renderPage();
    expect(screen.getByRole("button", { name: /sending/i })).toBeDisabled();
  });

  it("shows success status and hides error banner after resend success", () => {
    /**
     * After successful resend:
     * - Error banner (role=alert) must be gone
     * - Success banner (role=status) must appear
     * - formError text must not be visible
     */
    hookState.formError      = "Please verify your email.";
    hookState.formErrorCode  = "email_not_verified";
    hookState.isResendSuccess = true;
    renderPage();

    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent(
      "Verification email sent. Please check your inbox."
    );
  });
});
// // src/test/pages/account/Login.test.jsx

// import { describe, it, expect, vi, beforeEach } from "vitest";
// import { render, screen, fireEvent } from "@testing-library/react";
// import { MemoryRouter } from "react-router-dom";
// import Login from "../../../pages/account/Login";

// // ─────────────────────────────────────────────────────────────
// // Mock useLoginForm
// // ─────────────────────────────────────────────────────────────

// const handleChange = vi.fn();
// const handleSubmit = vi.fn();

// let hookState = {
//   form: {
//     email: "",
//     password: "",
//   },
//   fieldErrors: {
//     email: null,
//     password: null,
//   },
//   formError: null,
//   isPending: false,
//   handleChange,
//   handleSubmit,
// };

// vi.mock("../../../hooks/account/useLoginForm", () => ({
//   useLoginForm: () => hookState,
// }));

// // ─────────────────────────────────────────────────────────────
// // Mock AuthLayout
// // ─────────────────────────────────────────────────────────────

// vi.mock("../../../components/account/AuthLayout", () => ({
//   default: ({ children }) => (
//     <div data-testid="auth-layout">{children}</div>
//   ),
// }));

// // ─────────────────────────────────────────────────────────────
// // Mock SocialLogin
// // ─────────────────────────────────────────────────────────────

// vi.mock("../../../components/account/SocialLogin", () => ({
//   default: () => (
//     <div data-testid="social-login">
//       Social Login
//     </div>
//   ),
// }));

// // ─────────────────────────────────────────────────────────────
// // Mock FormInput
// // ─────────────────────────────────────────────────────────────

// vi.mock("../../../components/common/FormInput", () => ({
//   default: ({
//     name,
//     type,
//     value,
//     onChange,
//     error,
//     placeholder,
//   }) => (
//     <div>
//       <input
//         data-testid={name}
//         name={name}
//         type={type}
//         value={value}
//         placeholder={placeholder}
//         onChange={onChange}
//       />

//       {error && (
//         <span data-testid={`${name}-error`}>
//           {error}
//         </span>
//       )}
//     </div>
//   ),
// }));

// // ─────────────────────────────────────────────────────────────
// // Helper
// // ─────────────────────────────────────────────────────────────

// function renderPage() {
//   return render(
//     <MemoryRouter>
//       <Login />
//     </MemoryRouter>,
//   );
// }

// // ─────────────────────────────────────────────────────────────
// // Reset
// // ─────────────────────────────────────────────────────────────

// beforeEach(() => {
//   vi.clearAllMocks();

//   hookState = {
//     form: {
//       email: "",
//       password: "",
//     },
//     fieldErrors: {
//       email: null,
//       password: null,
//     },
//     formError: null,
//     isPending: false,
//     handleChange,
//     handleSubmit,
//   };
// });

// // ─────────────────────────────────────────────────────────────
// // Tests
// // ─────────────────────────────────────────────────────────────

// describe("Login Page", () => {
//   it("renders login heading", () => {
//     renderPage();

//     expect(
//       screen.getByText("Welcome Back"),
//     ).toBeInTheDocument();
//   });

//   it("renders email input", () => {
//     renderPage();

//     expect(
//       screen.getByTestId("email"),
//     ).toBeInTheDocument();
//   });

//   it("renders password input", () => {
//     renderPage();

//     expect(
//       screen.getByTestId("password"),
//     ).toBeInTheDocument();
//   });

//   it("renders social login section", () => {
//     renderPage();

//     expect(
//       screen.getByTestId("social-login"),
//     ).toBeInTheDocument();
//   });

//   it("renders login button", () => {
//     renderPage();

//     expect(
//       screen.getByRole("button", {
//         name: "LOGIN",
//       }),
//     ).toBeInTheDocument();
//   });

//   it("calls handleChange when email changes", () => {
//     renderPage();

//     fireEvent.change(
//       screen.getByTestId("email"),
//       {
//         target: {
//           value: "john@test.com",
//         },
//       },
//     );

//     expect(handleChange).toHaveBeenCalled();
//   });

//   it("calls handleChange when password changes", () => {
//     renderPage();

//     fireEvent.change(
//       screen.getByTestId("password"),
//       {
//         target: {
//           value: "password123",
//         },
//       },
//     );

//     expect(handleChange).toHaveBeenCalled();
//   });

//   it("submits the form", () => {
//     renderPage();

//     fireEvent.submit(
//       screen.getByRole("button", {
//         name: "LOGIN",
//       }).closest("form"),
//     );

//     expect(handleSubmit).toHaveBeenCalledTimes(1);
//   });

//   it("shows pending button text", () => {
//     hookState.isPending = true;

//     renderPage();

//     expect(
//       screen.getByRole("button"),
//     ).toHaveTextContent(
//       "LOGGING IN...",
//     );
//   });

//   it("disables button while pending", () => {
//     hookState.isPending = true;

//     renderPage();

//     expect(
//       screen.getByRole("button"),
//     ).toBeDisabled();
//   });

//   it("shows form level error", () => {
//     hookState.formError =
//       "Invalid email or password.";

//     renderPage();

//     expect(
//       screen.getByRole("alert"),
//     ).toHaveTextContent(
//       "Invalid email or password.",
//     );
//   });

//   it("shows email validation error", () => {
//     hookState.fieldErrors.email =
//       "Email is required.";

//     renderPage();

//     expect(
//       screen.getByTestId("email-error"),
//     ).toHaveTextContent(
//       "Email is required.",
//     );
//   });

//   it("shows password validation error", () => {
//     hookState.fieldErrors.password =
//       "Password is required.";

//     renderPage();

//     expect(
//       screen.getByTestId("password-error"),
//     ).toHaveTextContent(
//       "Password is required.",
//     );
//   });

//   it("renders forgot password link", () => {
//     renderPage();

//     expect(
//       screen.getByText(
//         "Forgot Password?",
//       ),
//     ).toBeInTheDocument();
//   });

//   it("renders register link", () => {
//     renderPage();

//     expect(
//       screen.getByText(
//         "Create Account",
//       ),
//     ).toBeInTheDocument();
//   });
// });