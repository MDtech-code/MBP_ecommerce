// src/test/hooks/account/useVerifyEmailPage.test.jsx
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, act, waitFor } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
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

const mockNoToken = () => {
  useSearchParams.mockReturnValue([{ get: () => null }])
}

const mockWithToken = (token = "test-token-123") => {
  useSearchParams.mockReturnValue([
    { get: (key) => (key === "token" ? token : null) },
  ])
}

// ─── Module cache reset between tests ────────────────────────────────────────
// Module-level variables in useVerifyEmailPage persist across tests
// We must reset them by re-importing the module fresh each time

const resetModuleCache = async () => {
  vi.resetModules()
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("useVerifyEmailPage", () => {

  beforeEach(async () => {
    vi.clearAllMocks()
    localStorage.clear()
    sessionStorage.clear()
    await resetModuleCache()
  })

  afterEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  // ── Email from storage ────────────────────────────────────────────────────

  describe("email from localStorage", () => {

    it("reads email from localStorage on mount", async () => {
      mockNoToken()
      localStorage.setItem("pending_verification_email", "john@test.com")

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.email).toBe("john@test.com")
    })

    it("returns empty string when storage has no email", async () => {
      mockNoToken()

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.email).toBe("")
    })

  })

  // ── No token in URL ───────────────────────────────────────────────────────

  describe("no token in URL", () => {

    it("tokenFromUrl is null", async () => {
      mockNoToken()

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.tokenFromUrl).toBeNull()
    })

    it("does not call verifyEmail on mount", async () => {
      mockNoToken()

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await new Promise((r) => setTimeout(r, 100))

      expect(accountService.verifyEmail).not.toHaveBeenCalled()
    })

    it("isVerifying is false", async () => {
      mockNoToken()

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      expect(result.current.isVerifying).toBe(false)
    })

  })

  // ── Token in URL — success ────────────────────────────────────────────────

  describe("token in URL — successful verification", () => {

    it("calls verifyEmail with correct token key", async () => {
      mockWithToken("good-token-123")

      accountService.verifyEmail.mockResolvedValue({
        data: null,
        message: "Email verified.",
        meta: null,
      })

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(accountService.verifyEmail).toHaveBeenCalledWith(
          { token: "good-token-123" },
          expect.anything()
        )
      })
    })

    it("navigates to /login with success message on verified", async () => {
      mockWithToken("good-token-123")

      accountService.verifyEmail.mockResolvedValue({
        data: null,
        message: "Email verified.",
        meta: null,
      })

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(mockNavigate).toHaveBeenCalledWith("/login", {
          state: { message: "Email verified. You can now log in." },
        })
      })
    })

    it("clears email from localStorage on success", async () => {
      mockWithToken("good-token-123")
      localStorage.setItem("pending_verification_email", "john@test.com")

      accountService.verifyEmail.mockResolvedValue({
        data: null,
        message: "Email verified.",
        meta: null,
      })

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(
          localStorage.getItem("pending_verification_email")
        ).toBeNull()
      })
    })

  })

  // ── Token in URL — failure ────────────────────────────────────────────────

  describe("token in URL — failed verification", () => {

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

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      await waitFor(() => {
        expect(result.current.verifyErrorMsg).toBe(
          "Invalid or expired token."
        )
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

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

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

    it("calls resendVerification with email", async () => {
      mockNoToken()
      localStorage.setItem("pending_verification_email", "john@test.com")

      accountService.resendVerification.mockResolvedValue({
        data: null,
        message: "Verification email sent.",
        meta: null,
      })

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      act(() => {
        result.current.handleResend()
      })

      await waitFor(() => {
        expect(accountService.resendVerification).toHaveBeenCalledWith(
          { email: "john@test.com" },
          expect.anything()
        )
      })
    })

    it("does not call resendVerification when email is empty", async () => {
      mockNoToken()

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

      const { result } = renderHook(() => useVerifyEmailPage(), {
        wrapper: makeWrapper(),
      })

      act(() => {
        result.current.handleResend()
      })

      await new Promise((r) => setTimeout(r, 100))

      expect(accountService.resendVerification).not.toHaveBeenCalled()
    })

    it("exposes resendSuccessMsg on success", async () => {
      mockNoToken()
      localStorage.setItem("pending_verification_email", "john@test.com")

      accountService.resendVerification.mockResolvedValue({
        data: null,
        message: "Sent.",
        meta: null,
      })

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

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

    it("exposes resendErrorMsg on failure", async () => {
      mockNoToken()
      localStorage.setItem("pending_verification_email", "ghost@test.com")

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

      const { useVerifyEmailPage } = await import(
        "../../../hooks/account/useVerifyEmailPage"
      )

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