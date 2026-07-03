// src/test/pages/account/VerifyEmail.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import VerifyEmail from "../../../pages/account/VerifyEmail"
import * as useVerifyEmailPageModule from "../../../hooks/account/useVerifyEmailPage"

vi.mock("../../../hooks/account/useVerifyEmailPage")

vi.mock("../../../components/account/AuthLayout", () => ({
  default: ({ children }) => <div data-testid="auth-layout">{children}</div>,
}))

// ─── Default mock hook return ─────────────────────────────────────────────────

const defaultHookReturn = {
  email: "john@test.com",
  tokenFromUrl: null,
  isVerifying: false,
  isResending: false,
  isVerifySuccess: false,
  verifyErrorMsg: null,
  resendErrorMsg: null,
  resendSuccessMsg: null,
  handleResend: vi.fn(),
}

const renderVerifyEmail = () =>
  render(
    <MemoryRouter>
      <VerifyEmail />
    </MemoryRouter>
  )

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("VerifyEmail page", () => {

  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
      .mockReturnValue(defaultHookReturn)
  })

  // ── Normal state (no token) ───────────────────────────────────────────────

  describe("no token in URL — waiting state", () => {

    it("renders heading", () => {
      renderVerifyEmail()
      expect(screen.getByText("Verify Your Email")).toBeInTheDocument()
    })

    it("shows the registered email address", () => {
      renderVerifyEmail()
      expect(screen.getByText("john@test.com")).toBeInTheDocument()
    })

    it("shows fallback text when email is empty", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({ ...defaultHookReturn, email: "" })

      renderVerifyEmail()
      expect(screen.getByText("your email address")).toBeInTheDocument()
    })

    it("renders resend button", () => {
      renderVerifyEmail()
      expect(
        screen.getByRole("button", { name: /resend email/i })
      ).toBeInTheDocument()
    })

    it("renders back to login link", () => {
      renderVerifyEmail()
      expect(
        screen.getByRole("link", { name: /back to login/i })
      ).toBeInTheDocument()
    })

    it("calls handleResend when resend button clicked", () => {
      const mockHandleResend = vi.fn()
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({ ...defaultHookReturn, handleResend: mockHandleResend })

      renderVerifyEmail()
      fireEvent.click(screen.getByRole("button", { name: /resend email/i }))

      expect(mockHandleResend).toHaveBeenCalledTimes(1)
    })

    it("disables resend button and shows sending text when isResending", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({ ...defaultHookReturn, isResending: true })

      renderVerifyEmail()

      const button = screen.getByRole("button", { name: /sending/i })
      expect(button).toBeDisabled()
    })

    it("shows resend success message", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          resendSuccessMsg: "Verification email sent. Please check your inbox.",
        })

      renderVerifyEmail()

      expect(
        screen.getByRole("status")
      ).toHaveTextContent("Verification email sent. Please check your inbox.")
    })

    it("shows resend error message", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          resendErrorMsg: "No account found with this email.",
        })

      renderVerifyEmail()

      expect(
        screen.getByRole("alert")
      ).toHaveTextContent("No account found with this email.")
    })

  })

  // ── Token in URL state ────────────────────────────────────────────────────

  describe("token in URL — auto verifying state", () => {

    it("shows verifying message when isVerifying is true", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "test-token-123",
          isVerifying: true,
        })

      renderVerifyEmail()

      expect(
        screen.getByText(/verifying your email/i)
      ).toBeInTheDocument()
    })

    it("shows verify error when token is invalid", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "bad-token",
          isVerifying: false,
          verifyErrorMsg: "Invalid or expired token.",
        })

      renderVerifyEmail()

      expect(
        screen.getByText("Invalid or expired token.")
      ).toBeInTheDocument()
    })

    it("does not show resend button when token is in URL", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "test-token-123",
        })

      renderVerifyEmail()

      expect(
        screen.queryByRole("button", { name: /resend email/i })
      ).not.toBeInTheDocument()
    })

  })

})