import { expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@app/config/test/server";
import { accountService } from "./accountService";
import { api } from "../client";

it("posts the registration payload with CSRF and credentials and unwraps null data", async () => {
  const payload = { full_name: "MD Khan", email: "md@example.com", password: "Distinctive593!", confirm_password: "Distinctive593!" };
  document.cookie = "csrftoken=test-csrf; Path=/";
  const spy = vi.spyOn(api, "post"); // Calls through; MSW owns the network boundary.
  let received;
  server.use(http.post("https://shop.example.test/api/accounts/register/", async ({ request }) => {
    received = { payload: await request.json(), csrf: request.headers.get("X-CSRFToken") };
    return HttpResponse.json({ success: true, data: null, errors: null, message: "Please verify", meta: { request_id: "r1" } }, { status: 201 });
  }));
  await expect(accountService.register(payload)).resolves.toEqual({ data: null, message: "Please verify", meta: { request_id: "r1" } });
  expect(received).toEqual({ payload, csrf: "test-csrf" });
  expect(spy).toHaveBeenCalledWith("/api/accounts/register/", payload, {
    withCredentials: true, headers: { "X-CSRFToken": "test-csrf" },
  });
});

it.each([
  ["verifyEmail", "/verify-email/", { token: "token-value" }],
  ["resendVerification", "/resend-verification/", { email: "md@example.com" }],
])("%s uses its endpoint without altering the payload", async (method, path, payload) => {
  let received;
  server.use(http.post(`https://shop.example.test/api/accounts${path}`, async ({ request }) => {
    received = await request.json();
    return HttpResponse.json({ success: true, data: null, message: "OK", meta: null });
  }));
  await expect(accountService[method](payload)).resolves.toEqual({ data: null, message: "OK", meta: null });
  expect(received).toEqual(payload);
});

it.each([400, 409, 429, 500])("preserves HTTP %i for the shared normalizer", async (status) => {
  const envelope = { success: false, errors: { code: "example_error" }, meta: { request_id: "r2" } };
  server.use(http.post("https://shop.example.test/api/accounts/register/", () => HttpResponse.json(envelope, { status })));
  await expect(accountService.register({})).rejects.toMatchObject({ response: { status, data: envelope } });
});
