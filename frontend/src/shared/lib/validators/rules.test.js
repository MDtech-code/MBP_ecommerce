import { describe, expect, it } from "vitest";
import {
  required, emailFormat, fullName, strongPassword, matchesField,
  pakistaniPhone, imageMaxSize, imageAllowedType,
} from "./rules";

// A rule returns null on success; errors are owned by the first failing rule.
describe("registration rules", () => {
  it.each([undefined, null, "", " \t\n"])("requires a nonblank value: %s", (value) => {
    expect(required(value)).toBe("This field is required.");
  });
  it.each(["MD", " MD "])("accepts present input: %s", (value) => expect(required(value)).toBeNull());
  it.each(["MD@EXAMPLE.COM", " md+shop@example.co.uk "])("accepts email: %s", (value) => {
    expect(emailFormat(value)).toBeNull();
  });
  it.each(["not-an-email", "a@b", "@example.com", "a b@example.com"])("rejects email: %s", (value) => {
    expect(emailFormat(value)).toBe("Enter a valid email address.");
  });
  it.each([emailFormat, fullName, strongPassword, matchesField("pass")])("leaves required checking to required", (rule) => {
    expect(rule("")).toBeNull();
  });
  it.each(["MD Khan", " MD\t Hassan\nKhan "])("accepts normalized full name: %s", (value) => {
    expect(fullName(value)).toBeNull();
  });
  it.each(["MD", "   "])("rejects a single-word name: %s", (value) => {
    expect(fullName(value)).toMatch(/first and last name/);
  });
  it("checks password length before numeric content", () => {
    expect(strongPassword("1234567")).toMatch(/at least 8/);
    expect(strongPassword("12345678")).toMatch(/entirely numeric/);
    expect(strongPassword("Abcd123!")).toBeNull();
  });
  it("compares confirmation exactly, including case and whitespace", () => {
    const rule = matchesField("Abcd123!");
    expect(rule("Abcd123!")).toBeNull();
    expect(rule("abcd123!")).toBe("Passwords do not match.");
    expect(rule("Abcd123! ")).toBe("Passwords do not match.");
  });
});

describe("other exported shared rules", () => {
  it.each(["", " ", null, "03001234567", "+923001234567", "923001234567"])("accepts optional/Pakistani phone: %s", (value) => {
    expect(pakistaniPhone(value)).toBeNull();
  });
  it.each(["123", "+123001234567", "030012345678"])("rejects invalid phone: %s", (value) => {
    expect(pakistaniPhone(value)).toMatch(/Pakistani phone/);
  });
  it("allows the exact image size boundary", () => {
    expect(imageMaxSize(null)).toBeNull();
    expect(imageMaxSize({ size: 2 * 1024 * 1024 })).toBeNull();
    expect(imageMaxSize({ size: 2 * 1024 * 1024 + 1 })).toMatch(/2MB/);
  });
  it.each(["image/jpeg", "image/png", "image/webp"])("accepts supported image type: %s", (type) => {
    expect(imageAllowedType({ type })).toBeNull();
  });
  it("rejects unsupported type but allows absent optional upload", () => {
    expect(imageAllowedType(null)).toBeNull();
    expect(imageAllowedType({ type: "image/svg+xml" })).toMatch(/JPEG, PNG and WebP/);
  });
});
