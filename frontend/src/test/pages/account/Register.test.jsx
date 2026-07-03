// src/test/pages/account/Register.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import Register from "../../../pages/account/Register"
import * as useRegisterFormModule from "../../../hooks/account/useRegisterForm"

// Mock the entire form hook — page tests only care about UI behavior
vi.mock("../../../hooks/account/useRegisterForm")

// Mock AuthLayout — we test Register logic, not AuthLayout
vi.mock("../../../components/account/AuthLayout", () => ({
  default: ({ children }) => <div data-testid="auth-layout">{children}</div>,
}))

// ─── Default mock hook return ─────────────────────────────────────────────────

const defaultHookReturn = {
  form: {
    full_name: "",
    email: "",
    password: "",
    confirm_password: "",
  },
  fieldErrors: {
    full_name: null,
    email: null,
    password: null,
    confirm_password: null,
  },
  formError: null,
  isPending: false,
  handleChange: vi.fn(),
  handleSubmit: vi.fn(),
}

const renderRegister = () =>
  render(
    <MemoryRouter>
      <Register />
    </MemoryRouter>
  )

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Register page", () => {

  beforeEach(() => {
    vi.clearAllMocks()
    vi.spyOn(useRegisterFormModule, "useRegisterForm")
      .mockReturnValue(defaultHookReturn)
  })

  // ── Renders correctly ─────────────────────────────────────────────────────

  it("renders heading and subheading", () => {
    renderRegister()

    expect(screen.getByText("Create Account")).toBeInTheDocument()
    expect(screen.getByText("Join BikeExpress today")).toBeInTheDocument()
  })

  it("renders all four input fields", () => {
    renderRegister()

    expect(screen.getByPlaceholderText("Full name")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Email address")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Password")).toBeInTheDocument()
    expect(screen.getByPlaceholderText("Confirm password")).toBeInTheDocument()
  })

  it("renders submit button with correct default text", () => {
    renderRegister()
    expect(screen.getByRole("button", { name: /create account/i })).toBeInTheDocument()
  })

  it("renders login link", () => {
    renderRegister()
    expect(screen.getByRole("link", { name: /login/i })).toBeInTheDocument()
  })

  // ── Loading state ─────────────────────────────────────────────────────────

  it("shows loading text and disables button when isPending", () => {
    vi.spyOn(useRegisterFormModule, "useRegisterForm")
      .mockReturnValue({ ...defaultHookReturn, isPending: true })

    renderRegister()

    const button = screen.getByRole("button", { name: /creating account/i })
    expect(button).toBeDisabled()
  })

  // ── Field errors ──────────────────────────────────────────────────────────

  it("shows field error under correct input", () => {
    vi.spyOn(useRegisterFormModule, "useRegisterForm")
      .mockReturnValue({
        ...defaultHookReturn,
        fieldErrors: {
          full_name: "This field is required.",
          email: null,
          password: "Password must be at least 8 characters.",
          confirm_password: null,
        },
      })

    renderRegister()

    expect(screen.getByText("This field is required.")).toBeInTheDocument()
    expect(
      screen.getByText("Password must be at least 8 characters.")
    ).toBeInTheDocument()
  })

  // ── Form error banner ─────────────────────────────────────────────────────

  it("shows form error banner when formError is present", () => {
    vi.spyOn(useRegisterFormModule, "useRegisterForm")
      .mockReturnValue({
        ...defaultHookReturn,
        formError: "An account already exists with this email.",
      })

    renderRegister()

    expect(
      screen.getByRole("alert")
    ).toHaveTextContent("An account already exists with this email.")
  })

  it("does not show error banner when formError is null", () => {
    renderRegister()
    expect(screen.queryByRole("alert")).not.toBeInTheDocument()
  })

  // ── Interactions ──────────────────────────────────────────────────────────

  it("calls handleSubmit when form is submitted", () => {
    const mockHandleSubmit = vi.fn((e) => e.preventDefault())

    vi.spyOn(useRegisterFormModule, "useRegisterForm")
      .mockReturnValue({ ...defaultHookReturn, handleSubmit: mockHandleSubmit })

    renderRegister()

    fireEvent.submit(screen.getByRole("button", { name: /create account/i }).closest("form"))

    expect(mockHandleSubmit).toHaveBeenCalledTimes(1)
  })

  it("calls handleChange when input value changes", () => {
    const mockHandleChange = vi.fn()

    vi.spyOn(useRegisterFormModule, "useRegisterForm")
      .mockReturnValue({ ...defaultHookReturn, handleChange: mockHandleChange })

    renderRegister()

    fireEvent.change(screen.getByPlaceholderText("Full name"), {
      target: { name: "full_name", value: "John" },
    })

    expect(mockHandleChange).toHaveBeenCalledTimes(1)
  })

})