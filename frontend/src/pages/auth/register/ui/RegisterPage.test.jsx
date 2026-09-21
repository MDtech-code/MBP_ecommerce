import { act, fireEvent, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Routes, Route } from "react-router-dom";
import { http, HttpResponse } from "msw";
import { expect, it } from "vitest";
import { server } from "@app/config/test/server";
import { renderWithProviders } from "@app/config/test/renderWithProviders";
import RegisterPage from "./RegisterPage";

const endpoint = "https://shop.example.test/api/accounts/register/";
const valid = { full_name: "MD Khan", email: "md@example.com", password: "Distinctive593!", confirm_password: "Distinctive593!" };
const success = { success: true, message: "Please verify your email", data: null, errors: null, meta: { request_id: "r1" } };
const failure = (errors, meta = null) => ({ success: false, message: "Registration failed", data: null, errors, meta });

function renderRegistration() {
  return renderWithProviders(<Routes>
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/verify-email" element={<h1>Check your email</h1>} />
    <Route path="/login" element={<h1>Login destination</h1>} />
  </Routes>);
}

function fillForm() {
  // Rule permutations are owned by validator tests. Here we exercise real
  // onChange wiring, refs, mutation, axios and HTTP with one representative form.
  for (const [label, name] of [["Full name", "full_name"], ["Email address", "email"], ["Password", "password"], ["Confirm password", "confirm_password"]]) {
    fireEvent.change(screen.getByLabelText(label), { target: { value: valid[name] } });
  }
}

it("does not show errors on initial blur; invalid submit never calls HTTP", async () => {
  const user = userEvent.setup();
  renderRegistration();
  const fullName = screen.getByRole("textbox", { name: "Full name" });
  fireEvent.blur(fullName);
  expect(screen.queryByText("This field is required.")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(screen.getAllByText("This field is required.")).toHaveLength(4);
  fireEvent.change(fullName, { target: { value: "MD" } });
  fireEvent.blur(fullName);
  expect(screen.getByText(/first and last name/)).toBeVisible();
});

it("posts the latest form values and navigates only after 201", async () => {
  const user = userEvent.setup();
  let received;
  server.use(http.post(endpoint, async ({ request }) => {
    received = await request.json();
    return HttpResponse.json(success, { status: 201 });
  }));
  renderRegistration();
  fillForm();
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByRole("heading", { name: "Check your email" })).toBeVisible();
  expect(received).toEqual(valid);
});

it("displays server-only password validation without navigating", async () => {
  server.use(http.post(endpoint, () => HttpResponse.json(failure({ code: "validation_error", fields: {
    password: { code: "password_too_weak", message: "This password is too common." },
  }, non_fields: null }), { status: 400 })));
  renderRegistration();
  fillForm();
  fireEvent.submit(screen.getByRole("button", { name: "Create account" }).closest("form"));
  expect(await screen.findByText("This password is too common.")).toBeVisible();
  expect(screen.queryByRole("heading", { name: "Check your email" })).not.toBeInTheDocument();
});

it("shows a duplicate-email domain error and allows correction and retry", async () => {
  const user = userEvent.setup();
  let calls = 0;
  server.use(http.post(endpoint, () => {
    calls += 1;
    return calls === 1 ? HttpResponse.json(failure({ code: "conflict_error", fields: null,
      non_fields: { category: "domain", code: "conflict_error", message: "An account with this email already exists.", extra: null },
    }), { status: 409 }) : HttpResponse.json(success, { status: 201 });
  }));
  renderRegistration();
  fillForm();
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(/already exists/);
  await user.clear(screen.getByLabelText("Email address"));
  await user.type(screen.getByLabelText("Email address"), "other@example.com");
  await user.click(screen.getByRole("button", { name: "Create account" }));
  expect(await screen.findByRole("heading", { name: "Check your email" })).toBeVisible();
  expect(calls).toBe(2);
});

it.each(["network", "server"])("shows an actionable %s failure", async (kind) => {
  server.use(http.post(endpoint, () => kind === "network" ? HttpResponse.error() : new HttpResponse("proxy down", { status: 500 })));
  renderRegistration();
  fillForm();
  fireEvent.submit(screen.getByRole("button", { name: "Create account" }).closest("form"));
  expect(await screen.findByRole("alert")).toHaveTextContent(kind === "network" ? /Network error/ : /unexpected error/i);
  expect(screen.getByRole("button", { name: "Create account" })).toBeEnabled();
});

it("disables submit and displays server-derived rate-limit countdown", async () => {
  let calls = 0;
  server.use(http.post(endpoint, () => {
    calls += 1;
    return HttpResponse.json(failure({
    code: "rate_limit_exceeded", fields: null,
    non_fields: { message: "Too many requests.", code: "throttled", category: "validation", extra: null },
  }, { rateLimit: { limit: 2, remaining: 0, resetAt: new Date(Date.now() + 60000).toISOString() } }), { status: 429 });
  }));
  renderRegistration();
  fillForm();
  fireEvent.submit(screen.getByRole("button", { name: "Create account" }).closest("form"));
  const button = await screen.findByRole("button", { name: /Try again in/ });
  expect(button).toBeDisabled();
  // Keyboard/programmatic submission must obey the same guard as the button.
  fireEvent.submit(button.closest("form"));
  expect(button).toBeDisabled();
  expect(calls).toBe(1);
});

it("prevents duplicate submits while the request is in flight", async () => {
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  let calls = 0;
  server.use(http.post(endpoint, async () => {
    calls += 1;
    await gate;
    return HttpResponse.json(success, { status: 201 });
  }));
  renderRegistration();
  fillForm();
  const form = screen.getByRole("button", { name: "Create account" }).closest("form");
  act(() => {
    fireEvent.submit(form);
    fireEvent.submit(form);
  });
  try {
    await waitFor(() => expect(calls).toBeGreaterThan(0));
    expect(screen.getByRole("button", { name: "CREATING ACCOUNT..." })).toBeDisabled();
  } finally {
    release();
  }
  await screen.findByRole("heading", { name: "Check your email" });
  expect(calls).toBe(1);
});
