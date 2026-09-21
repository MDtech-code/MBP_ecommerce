import { expect, it } from "vitest";
import { getCookie, setCookie, clearCookie } from "./cookies";

it("matches a complete name, not a prefix/suffix", () => {
  document.cookie = "other_csrftoken=wrong; Path=/";
  document.cookie = "csrftoken_suffix=wrong; Path=/";
  expect(getCookie("csrftoken")).toBeNull();
  document.cookie = "csrftoken=right; Path=/";
  expect(getCookie("csrftoken")).toBe("right");
});

it.each(["md+shop@example.com", { email: "md@example.com" }, [1, 2], false, 0])("roundtrips supported cookie value %j", (value) => {
  setCookie("pending", value, { path: "/", secure: true, sameSite: "Lax", maxAge: 900 });
  expect(getCookie("pending")).toEqual(value);
  clearCookie("pending");
  expect(getCookie("pending")).toBeNull();
});

it("supports absent options", () => {
  setCookie("simple", "value");
  expect(getCookie("simple")).toBe("value");
});

it("does not crash the form on malformed percent-encoding", () => {
  document.cookie = "pending=%E0%A4%A; Path=/";
  expect(() => getCookie("pending")).not.toThrow();
  expect(getCookie("pending")).toBeNull();
});
