// src/test/hooks/account/useVerifyEmailPage.test.jsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useVerifyEmailPage } from "../../../hooks/account/useVerifyEmailPage"
import { accountService } from "../../../services/accountService"

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../services/accountService", () => ({
  accountService: {
    verifyEmail: vi.fn(),
    resendVerification: vi.fn(),
  },
}))

const mockNavigate = vi.fn()

vi.mock("react-router-dom", () => ({
  useNavigate: () => mockNavigate,
  useSearchParams: vi.fn(),
}))

import { useSearchParams } from "react-router-dom"

// ─── Helpers ──────────────────────────────────────────────────────────────────

const makeWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  })
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  )
}

// Helper — mock URL with no token (normal page load after register)
const mockNoToken = () => {
  useSearchParams.mockReturnValue([
    { get: () => null },
  ])
}

// Helper — mock URL with token (user clicked email link)
const mockWithToken = (token = "test-token-123") => {
  useSearchParams.mockReturnValue([
    { get: (key) => key === "token" ? token : null },
  ])
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("useVerifyEmailPage", () => {

  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
  })

  afterEach(() => {
    sessionStorage.clear()
  })

  // ── Email from sessionStorage ─────────────────────────────────────────────

  describe("email from sessionStorage", () => {

    it("reads email from sessionStorage on mount", () => {
      mockNoToken()
      sessionStorage.setItem("pending_verification_email", "john@test.com")

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.email).toBe("john@test.com")
    })

    it("returns empty string when sessionStorage has no email", () => {
      mockNoToken()

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.email).toBe("")
    })

  })

  // ── No token in URL ───────────────────────────────────────────────────────

  describe("no token in URL (arrived from register)", () => {

    it("does not call verifyEmail on mount when no token", async () => {
      mockNoToken()

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await new Promise((r) => setTimeout(r, 50))

      expect(accountService.verifyEmail).not.toHaveBeenCalled()
    })

    it("tokenFromUrl is null when no token in URL", () => {
      mockNoToken()

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.tokenFromUrl).toBeNull()
    })

    it("isVerifying is false when no token in URL", () => {
      mockNoToken()

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.isVerifying).toBe(false)
    })

  })

  // ── Token in URL ──────────────────────────────────────────────────────────

  describe("token in URL (user clicked email link)", () => {

    it("tokenFromUrl contains the token value", () => {
      mockWithToken("abc-123")

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.tokenFromUrl).toBe("abc-123")
    })

    it("calls verifyEmail with correct token key on mount", async () => {
      mockWithToken("test-token-123")

      accountService.verifyEmail.mockResolvedValue({
        data: null,
        message: "Email verified.",
        meta: null,
      })

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(accountService.verifyEmail).toHaveBeenCalledWith(
          { token: "test-token-123" },  // ← key must be "token" not "tokenFromUrl"
          expect.anything()
        )
      })
    })

    it("navigates to /login on successful verification", async () => {
      mockWithToken("test-token-123")

      accountService.verifyEmail.mockResolvedValue({
        data: null,
        message: "Email verified.",
        meta: null,
      })

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/login", {
          state: { message: "Email verified. You can now log in." },
        })
      })
    })

    it("removes email from sessionStorage on successful verification", async () => {
      mockWithToken("test-token-123")
      sessionStorage.setItem("pending_verification_email", "john@test.com")

      accountService.verifyEmail.mockResolvedValue({
        data: null,
        message: "Email verified.",
        meta: null,
      })

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(sessionStorage.getItem("pending_verification_email")).toBeNull()
      })
    })

    it("exposes verifyErrorMsg when token is invalid", async () => {
      mockWithToken("bad-token")

      const mockError = new Error("Invalid token")
      mockError.response = {
        status: 400,
        data: {
          message: "Invalid or expired token.",
          errors: { non_field_errors: ["Invalid or expired token."] },
          meta: null,
        },
      }

      accountService.verifyEmail.mockRejectedValue(mockError)

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(result.current.verifyErrorMsg).toBe("Invalid or expired token.")
      })
    })

    it("does not navigate on failed verification", async () => {
      mockWithToken("bad-token")

      const mockError = new Error("Invalid token")
      mockError.response = {
        status: 400,
        data: {
          message: "Invalid or expired token.",
          errors: { non_field_errors: ["Invalid or expired token."] },
          meta: null,
        },
      }

      accountService.verifyEmail.mockRejectedValue(mockError)

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(result.current.verifyErrorMsg).toBeTruthy()
      })

      expect(mockNavigate).not.toHaveBeenCalled()
    })

  })

  // ── Resend ────────────────────────────────────────────────────────────────

  describe("handleResend", () => {

    it("calls resendVerification with email from sessionStorage", async () => {
      mockNoToken()
      sessionStorage.setItem("pending_verification_email", "john@test.com")

      accountService.resendVerification.mockResolvedValue({
        data: null,
        message: "Verification email sent.",
        meta: null,
      })

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      act(() => {
        result.current.handleResend()
      })

      await waitFor(() => {
        expect(accountService.resendVerification).toHaveBeenCalledWith(
          { email: "john@test.com" },expect.anything()
        )
      })
    })

    it("does not call resendVerification when email is empty", async () => {
      mockNoToken()
      // sessionStorage is empty — no email

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      act(() => {
        result.current.handleResend()
      })

      await new Promise((r) => setTimeout(r, 50))

      expect(accountService.resendVerification).not.toHaveBeenCalled()
    })

    it("exposes resendSuccessMsg on successful resend", async () => {
      mockNoToken()
      sessionStorage.setItem("pending_verification_email", "john@test.com")

      accountService.resendVerification.mockResolvedValue({
        data: null,
        message: "Sent.",
        meta: null,
      })

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      act(() => {
        result.current.handleResend()
      })

      await waitFor(() => {
        expect(result.current.resendSuccessMsg).toBe(
          "Verification email sent. Please check your inbox."
        )
      })
    })

    it("exposes resendErrorMsg on failed resend", async () => {
      mockNoToken()
      sessionStorage.setItem("pending_verification_email", "ghost@test.com")

      const mockError = new Error("Not found")
      mockError.response = {
        status: 404,
        data: {
          message: "No account found with this email.",
          errors: null,
          meta: null,
        },
      }

      accountService.resendVerification.mockRejectedValue(mockError)

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      act(() => {
        result.current.handleResend()
      })

      await waitFor(() => {
        expect(result.current.resendErrorMsg).toBe(
          "No account found with this email."
        )
      })
    })

  })

})