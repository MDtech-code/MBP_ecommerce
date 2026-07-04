// src/test/pages/account/VerifyEmail.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import VerifyEmail from "../../../pages/account/VerifyEmail"
import * as useVerifyEmailPageModule from "../../../hooks/account/useVerifyEmailPage"

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../hooks/account/useVerifyEmailPage")

vi.mock("../../../components/account/AuthLayout", () => ({
  default: ({ children }) => (
    <div data-testid="auth-layout">{children}</div>
  ),
}))

// ─── Default hook return ──────────────────────────────────────────────────────

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

const renderPage = () =>
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

  // ── Static elements always present ───────────────────────────────────────

  it("always renders the heading", () => {
    renderPage()
    expect(screen.getByText("Verify Your Email")).toBeInTheDocument()
  })

  // ── No token — normal waiting state ──────────────────────────────────────

  describe("no token in URL — waiting state", () => {

    it("shows registered email address", () => {
      renderPage()
      expect(screen.getByText("john@test.com")).toBeInTheDocument()
    })

    it("shows fallback text when email is empty string", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({ ...defaultHookReturn, email: "" })

      renderPage()
      expect(screen.getByText("your email address")).toBeInTheDocument()
    })

    it("renders resend button", () => {
      renderPage()
      expect(
        screen.getByRole("button", { name: /resend email/i })
      ).toBeInTheDocument()
    })

    it("renders back to login link", () => {
      renderPage()
      expect(
        screen.getByRole("link", { name: /back to login/i })
      ).toBeInTheDocument()
    })

    it("calls handleResend when button clicked", () => {
      const mockHandleResend = vi.fn()
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({ ...defaultHookReturn, handleResend: mockHandleResend })

      renderPage()
      fireEvent.click(screen.getByRole("button", { name: /resend email/i }))

      expect(mockHandleResend).toHaveBeenCalledTimes(1)
    })

    it("disables resend button and shows sending text when isResending", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({ ...defaultHookReturn, isResending: true })

      renderPage()

      const button = screen.getByRole("button", { name: /sending/i })
      expect(button).toBeDisabled()
    })

    it("shows resend success message with role status", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          resendSuccessMsg: "Verification email sent. Please check your inbox.",
        })

      renderPage()

      expect(screen.getByRole("status")).toHaveTextContent(
        "Verification email sent. Please check your inbox."
      )
    })

    it("shows resend error message with role alert", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          resendErrorMsg: "No account found with this email.",
        })

      renderPage()

      expect(screen.getByRole("alert")).toHaveTextContent(
        "No account found with this email."
      )
    })

    it("does not show resend or back to login when token is in URL and no error", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "valid-token",
          verifyErrorMsg: null,
        })

      renderPage()

      expect(
        screen.queryByRole("button", { name: /resend email/i })
      ).not.toBeInTheDocument()

      expect(
        screen.queryByRole("link", { name: /back to login/i })
      ).not.toBeInTheDocument()
    })

  })

  // ── Token in URL — verifying state ───────────────────────────────────────

  describe("token in URL — verifying state", () => {

    it("shows verifying message when isVerifying true and no error", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "valid-token",
          isVerifying: true,
          verifyErrorMsg: null,
        })

      renderPage()

      expect(
        screen.getByText(/verifying your email/i)
      ).toBeInTheDocument()
    })

    it("shows redirecting text when verified and not verifying", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "valid-token",
          isVerifying: false,
          isVerifySuccess: true,
          verifyErrorMsg: null,
        })

      renderPage()

      expect(
        screen.getByText(/redirecting/i)
      ).toBeInTheDocument()
    })

  })

  // ── Token in URL — error state ────────────────────────────────────────────

  describe("token in URL — error state", () => {

    it("shows verify error and falls back to waiting UI", () => {
      vi.spyOn(useVerifyEmailPageModule, "useVerifyEmailPage")
        .mockReturnValue({
          ...defaultHookReturn,
          tokenFromUrl: "bad-token",
          isVerifying: false,
          verifyErrorMsg: "Invalid or expired token.",
        })

      renderPage()

      // Error banner shown
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Invalid or expired token."
      )

      // Resend button shown so user can request a new link
      expect(
        screen.getByRole("button", { name: /resend email/i })
      ).toBeInTheDocument()
    })

  })

})