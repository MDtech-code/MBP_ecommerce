import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useLoginForm } from "../../../hooks/account/useLoginForm";



const navigate = vi.fn();
const mutate = vi.fn();

let hookState = {
  isPending: false,
  isError: false,
  error: null,
};

vi.mock("react-router-dom", () => ({
  useNavigate: () => navigate,
}));

vi.mock("../../../hooks/account/useAuthMutations", () => ({
  useLogin: () => ({
    mutate,
    ...hookState,
  }),
}));

vi.mock("../../../api/transformers", () => ({
  normalizeError: vi.fn((error) => error),
}));


beforeEach(() => {
  vi.clearAllMocks();

  hookState = {
    isPending: false,
    isError: false,
    error: null,
  };
});


describe("useLoginForm", () => {
  it("starts with empty form", () => {
    const { result } = renderHook(() => useLoginForm());

    expect(result.current.form).toEqual({
      email: "",
      password: "",
    });

    expect(result.current.formError).toBeNull();

    expect(result.current.fieldErrors).toEqual({
      email: null,
      password: null,
    });

    expect(result.current.isPending).toBe(false);
  });
});



it("updates email field", () => {
  const { result } = renderHook(() => useLoginForm());

  act(() => {
    result.current.handleChange({
      target: {
        name: "email",
        value: "john@test.com",
      },
    });
  });

  expect(result.current.form.email).toBe("john@test.com");
});


it("updates password field", () => {
  const { result } = renderHook(() => useLoginForm());

  act(() => {
    result.current.handleChange({
      target: {
        name: "password",
        value: "secret123",
      },
    });
  });

  expect(result.current.form.password).toBe("secret123");
});



it("submits current form values", () => {
  const { result } = renderHook(() => useLoginForm());

  act(() => {
    result.current.handleChange({
      target: {
        name: "email",
        value: "john@test.com",
      },
    });

    result.current.handleChange({
      target: {
        name: "password",
        value: "password123",
      },
    });
  });

  act(() => {
    result.current.handleSubmit({
      preventDefault: vi.fn(),
    });
  });

  expect(mutate).toHaveBeenCalledTimes(1);

  expect(mutate).toHaveBeenCalledWith(
    {
      email: "john@test.com",
      password: "password123",
    },
    expect.objectContaining({
      onSuccess: expect.any(Function),
    })
  );
});


it("navigates to profile after successful login", () => {
  const { result } = renderHook(() => useLoginForm());

  act(() => {
    result.current.handleSubmit({
      preventDefault: vi.fn(),
    });
  });

  const options = mutate.mock.calls[0][1];

  act(() => {
    options.onSuccess();
  });

  expect(navigate).toHaveBeenCalledWith("/profile");
});


it("exposes pending state", () => {
  hookState.isPending = true;

  const { result } = renderHook(() => useLoginForm());

  expect(result.current.isPending).toBe(true);
});


it("maps non_field_errors into formError", () => {
  hookState.isError = true;

  hookState.error = {
    errors: {
      non_field_errors: ["Invalid email or password."],
    },
  };

  const { result } = renderHook(() => useLoginForm());

  expect(result.current.formError).toBe(
    "Invalid email or password."
  );
});


it("maps email validation error", () => {
  hookState.isError = true;

  hookState.error = {
    errors: {
      email: ["Invalid email"],
    },
  };

  const { result } = renderHook(() => useLoginForm());

  expect(result.current.fieldErrors.email).toBe(
    "Invalid email"
  );
});


it("maps email validation error", () => {
  hookState.isError = true;

  hookState.error = {
    errors: {
      email: ["Invalid email"],
    },
  };

  const { result } = renderHook(() => useLoginForm());

  expect(result.current.fieldErrors.email).toBe(
    "Invalid email"
  );
});