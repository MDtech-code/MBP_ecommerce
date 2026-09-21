import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, it, vi } from "vitest";
import FormInput from "./FormInput";

it("exposes a name and associated validation error to assistive technology", () => {
  const { rerender } = render(<FormInput name="email" placeholder="Email address" value="bad" onChange={() => {}} error="Invalid email" />);
  const input = screen.getByRole("textbox", { name: "Email address" });
  expect(input).toHaveAttribute("aria-invalid", "true");
  expect(input).toHaveAccessibleDescription("Invalid email");
  rerender(<FormInput name="email" placeholder="Email address" value="good@example.com" onChange={() => {}} />);
  expect(input).not.toHaveAttribute("aria-describedby");
  expect(input).not.toHaveAttribute("aria-invalid", "true");
});

it("forwards change and blur with the field name", async () => {
  const user = userEvent.setup();
  const change = vi.fn();
  const blur = vi.fn();
  render(<FormInput name="email" placeholder="Email address" onChange={change} onBlur={blur} />);
  await user.type(screen.getByRole("textbox", { name: "Email address" }), "a");
  expect(change.mock.calls[0][0].target.name).toBe("email");
  await user.tab();
  expect(blur).toHaveBeenCalledOnce();
});

it("reveals and hides passwords without submitting the parent form", async () => {
  const user = userEvent.setup();
  const submit = vi.fn((event) => event.preventDefault());
  render(<form onSubmit={submit}><FormInput type="password" name="password" placeholder="Password" /></form>);
  const input = screen.getByLabelText("Password");
  expect(input).toHaveAttribute("type", "password");
  await user.click(screen.getByRole("button", { name: "Show password" }));
  expect(input).toHaveAttribute("type", "text");
  await user.click(screen.getByRole("button", { name: "Hide password" }));
  expect(input).toHaveAttribute("type", "password");
  expect(submit).not.toHaveBeenCalled();
});
