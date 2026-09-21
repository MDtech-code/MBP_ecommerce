import { beforeEach, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@app/config/test/server";

// Reset the module only BETWEEN independent browser sessions. Concurrent calls
// within a test share the real module/promise and the real axios client.
beforeEach(() => vi.resetModules());

it("does not bootstrap when a CSRF cookie already exists", async () => {
  document.cookie = "csrftoken=existing; Path=/";
  const { ensureCsrfToken } = await import("./csrf");
  await expect(ensureCsrfToken()).resolves.toBeUndefined();
  // Any HTTP call would fail via the global unhandled-request policy.
});

it("shares one in-flight bootstrap and the resolved result", async () => {
  let release;
  const gate = new Promise((resolve) => { release = resolve; });
  let calls = 0;
  server.use(http.get("https://shop.example.test/api/csrf/", async () => {
    calls += 1;
    await gate;
    return HttpResponse.json({ success: true });
  }));
  const { ensureCsrfToken } = await import("./csrf");
  const first = ensureCsrfToken();
  const second = ensureCsrfToken();
  expect(second).toBe(first);
  release();
  await first;
  await ensureCsrfToken();
  expect(calls).toBe(1);
});

it("retries after failure rather than permanently caching rejection", async () => {
  let calls = 0;
  server.use(http.get("https://shop.example.test/api/csrf/", () => {
    calls += 1;
    return calls === 1 ? new HttpResponse(null, { status: 503 }) : HttpResponse.json({ success: true });
  }));
  const { ensureCsrfToken } = await import("./csrf");
  await expect(ensureCsrfToken()).rejects.toMatchObject({ response: { status: 503 } });
  await expect(ensureCsrfToken()).resolves.toBeDefined();
  expect(calls).toBe(2);
});
