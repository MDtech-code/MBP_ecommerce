import { expect, it, vi } from "vitest";
import { run, hasErrors } from "./validate";
import { registerSchema, loginSchema, phoneSchema } from "./schemas";

it("short-circuits each field independently at its first error", () => {
  const neverCalled = vi.fn();
  const pass = vi.fn(() => null);
  const values = Object.freeze({ first: "bad", second: "good" });
  const result = run({ first: [() => "First error", neverCalled], second: [pass] }, values);
  expect(result).toEqual({ first: { message: "First error", code: null } });
  expect(neverCalled).not.toHaveBeenCalled();
  expect(pass).toHaveBeenCalledWith("good");
  expect(hasErrors(result)).toBe(true);
});

it("supports empty schemas, empty rule arrays and missing values", () => {
  expect(run({}, {})).toEqual({});
  expect(run({ field: [] }, {})).toEqual({});
  expect(hasErrors({})).toBe(false);
  expect(Object.keys(run(registerSchema({}), {}))).toEqual([
    "full_name", "email", "password", "confirm_password",
  ]);
});

it("binds confirmation against the latest form password without mutating input", () => {
  const form = Object.freeze({ full_name: "MD Khan", email: "md@example.com", password: "Distinctive593!", confirm_password: "Distinctive593!" });
  expect(run(registerSchema(form), form)).toEqual({});
  const changed = { ...form, password: "Different593!" };
  expect(run(registerSchema(changed), changed)).toEqual({
    confirm_password: { message: "Passwords do not match.", code: null },
  });
});

it("composes required rules before optional format rules", () => {
  expect(run(loginSchema, {})).toEqual({
    email: { message: "This field is required.", code: null },
    password: { message: "This field is required.", code: null },
  });
  expect(run(phoneSchema, { phone: " " }).phone.message).toBe("This field is required.");
});
