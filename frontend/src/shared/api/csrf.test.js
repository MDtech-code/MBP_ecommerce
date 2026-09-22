import { beforeEach, expect, it, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "@app/config/test/server";

// This low-level helper must not load the shared barrel, which re-exports auth
// stores, React Query and API modules that circle back to CSRF. Keep the real
// cookie reader and HTTP client; this guard fails if that dependency returns.
vi.mock("@shared/lib", () => {
  throw new Error("CSRF must import the cookie utility, not the shared barrel");
});

let ensureCsrfToken;

// A fresh module represents an independent browser session. Complete loading
// BEFORE each test starts: a timed-out test must not resume a dynamic import
// after cookie cleanup and issue HTTP into the next test's MSW handler.
beforeEach(async () => {
  vi.resetModules();
  ({ ensureCsrfToken } = await import("./csrf"));
});

it("does not bootstrap when a CSRF cookie already exists", async () => {
  document.cookie = "csrftoken=existing; Path=/";
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
  const first = ensureCsrfToken();
  const second = ensureCsrfToken();
  try {
    expect(second).toBe(first);
  } finally {
    // Always finish outstanding requests, including when an assertion fails.
    release();
    await Promise.allSettled([first, second]);
  }
  await first;
  await ensureCsrfToken();
  expect(calls).toBe(1);
});

it("retries after shared failure rather than permanently caching rejection", async () => {
  let calls = 0;
  server.use(http.get("https://shop.example.test/api/csrf/", () => {
    calls += 1;
    return calls === 1 ? new HttpResponse(null, { status: 503 }) : HttpResponse.json({ success: true });
  }));
  const first = ensureCsrfToken();
  const second = ensureCsrfToken();
  // Observe both rejections immediately, avoiding unhandled promise failures.
  const results = await Promise.allSettled([first, second]);
  expect(second).toBe(first);
  expect(results).toEqual([
    expect.objectContaining({ status: "rejected", reason: expect.objectContaining({ response: expect.objectContaining({ status: 503 }) }) }),
    expect.objectContaining({ status: "rejected", reason: expect.objectContaining({ response: expect.objectContaining({ status: 503 }) }) }),
  ]);
  expect(calls).toBe(1);
  await expect(ensureCsrfToken()).resolves.toBeDefined();
  expect(calls).toBe(2);
});
