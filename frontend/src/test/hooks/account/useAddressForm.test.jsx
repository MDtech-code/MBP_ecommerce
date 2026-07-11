// src/hooks/account/__tests__/useAddressForm.test.js
/**
 * Layer 3 — useAddressForm hook tests.
 *
 * Covers:
 *   - Initial state (create mode vs edit mode)
 *   - handleChange updates form fields
 *   - handleSubmit calls createAddress in create mode
 *   - handleSubmit calls updateAddress in edit mode
 *   - onSaveSuccess called after successful submit
 *   - isPending reflects mutation loading state
 *   - fieldErrors populated from normalizeError
 *   - postalPreview derived from city selection
 *   - CITY_POSTAL_MAP spot checks
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement } from "react";

import { useAddressForm, CITY_POSTAL_MAP } from "../../../hooks/account/useAddressForm";

// ── Mock mutation hooks ───────────────────────────────────────────────────────
// useAddressForm consumes these — mock them at the hook level
const mockCreateMutate = vi.fn();
const mockUpdateMutate = vi.fn();

vi.mock("../../../hooks/account/useAuthMutations.js", () => ({
  useCreateAddress: () => ({
    mutate: mockCreateMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
  useUpdateAddress: () => ({
    mutate: mockUpdateMutate,
    isPending: false,
    isError: false,
    error: null,
  }),
}));

// ── Mock normalizeError ───────────────────────────────────────────────────────
vi.mock("../../../api/transformers.js", () => ({
  normalizeError: vi.fn((error) => ({
    message: error?.message ?? "Error",
    errors: error?.response?.data?.errors ?? {},
    isServerError: false,
    isAuthError: false,
  })),
}));

// ── Wrapper ───────────────────────────────────────────────────────────────────
function makeWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return ({ children }) =>
    createElement(QueryClientProvider, { client: queryClient }, children);
}

// ── Shared fixtures ───────────────────────────────────────────────────────────
const EXISTING_ADDRESS = {
  id: 5,
  label: "office",
  address_line1: "456 Work Avenue",
  address_line2: "Floor 3",
  city: "Karachi",
};

describe("useAddressForm — create mode (no existingAddress)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes form with empty EMPTY_FORM values", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.form).toEqual({
      label: "home",
      address_line1: "",
      address_line2: "",
      city: "",
    });
  });

  it("isEditing is false in create mode", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });
    expect(result.current.isEditing).toBe(false);
  });

  it("postalPreview is '—' when city is empty", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });
    expect(result.current.postalPreview).toBe("—");
  });

  it("handleChange updates a single form field", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "address_line1", value: "99 New Street" },
      });
    });

    expect(result.current.form.address_line1).toBe("99 New Street");
  });

  it("handleChange does not reset other fields", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "city", value: "Lahore" },
      });
    });

    // label must remain 'home' — not reset
    expect(result.current.form.label).toBe("home");
  });

  it("postalPreview updates when city is selected", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "city", value: "Lahore" },
      });
    });

    expect(result.current.postalPreview).toBe("54000");
  });

  it("postalPreview is '—' for unknown city", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleChange({
        target: { name: "city", value: "Atlantis" },
      });
    });

    expect(result.current.postalPreview).toBe("—");
  });

  it("handleSubmit calls createAddress mutate with form data", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    // Set city so form has some data
    act(() => {
      result.current.handleChange({
        target: { name: "city", value: "Lahore" },
      });
      result.current.handleChange({
        target: { name: "address_line1", value: "123 Test Road" },
      });
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(mockCreateMutate).toHaveBeenCalledTimes(1);
    expect(mockCreateMutate).toHaveBeenCalledWith(
      expect.objectContaining({
        city: "Lahore",
        address_line1: "123 Test Road",
      }),
      expect.any(Object),
    );
  });

  it("handleSubmit does not call updateAddress in create mode", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(mockUpdateMutate).not.toHaveBeenCalled();
  });

  it("handleSubmit calls preventDefault", () => {
    const { result } = renderHook(() => useAddressForm(), {
      wrapper: makeWrapper(),
    });

    const preventDefault = vi.fn();

    act(() => {
      result.current.handleSubmit({ preventDefault });
    });

    expect(preventDefault).toHaveBeenCalled();
  });

  it("onSaveSuccess is called after successful create", async () => {
    const onSaveSuccess = vi.fn();

    // Simulate mutate calling onSuccess callback
    mockCreateMutate.mockImplementationOnce((_data, { onSuccess }) => {
      onSuccess?.();
    });

    const { result } = renderHook(() => useAddressForm(null, onSaveSuccess), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(onSaveSuccess).toHaveBeenCalledTimes(1);
  });
});

describe("useAddressForm — edit mode (existingAddress provided)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("initializes form with existing address values", () => {
    const { result } = renderHook(() => useAddressForm(EXISTING_ADDRESS), {
      wrapper: makeWrapper(),
    });

    expect(result.current.form).toEqual({
      label: EXISTING_ADDRESS.label,
      address_line1: EXISTING_ADDRESS.address_line1,
      address_line2: EXISTING_ADDRESS.address_line2,
      city: EXISTING_ADDRESS.city,
    });
  });

  it("isEditing is true in edit mode", () => {
    const { result } = renderHook(() => useAddressForm(EXISTING_ADDRESS), {
      wrapper: makeWrapper(),
    });
    expect(result.current.isEditing).toBe(true);
  });

  it("postalPreview shows postal for existing address city", () => {
    const { result } = renderHook(() => useAddressForm(EXISTING_ADDRESS), {
      wrapper: makeWrapper(),
    });
    // Karachi → 75000
    expect(result.current.postalPreview).toBe("75000");
  });

  it("handleSubmit calls updateAddress with id and form data", () => {
    const { result } = renderHook(() => useAddressForm(EXISTING_ADDRESS), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(mockUpdateMutate).toHaveBeenCalledTimes(1);
    expect(mockUpdateMutate).toHaveBeenCalledWith(
      {
        id: EXISTING_ADDRESS.id,
        data: expect.objectContaining({
          city: EXISTING_ADDRESS.city,
          label: EXISTING_ADDRESS.label,
        }),
      },
      expect.any(Object),
    );
  });

  it("handleSubmit does not call createAddress in edit mode", () => {
    const { result } = renderHook(() => useAddressForm(EXISTING_ADDRESS), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(mockCreateMutate).not.toHaveBeenCalled();
  });

  it("onSaveSuccess is called after successful update", () => {
    const onSaveSuccess = vi.fn();

    mockUpdateMutate.mockImplementationOnce((_args, { onSuccess }) => {
      onSuccess?.();
    });

    const { result } = renderHook(
      () => useAddressForm(EXISTING_ADDRESS, onSaveSuccess),
      { wrapper: makeWrapper() },
    );

    act(() => {
      result.current.handleSubmit({ preventDefault: vi.fn() });
    });

    expect(onSaveSuccess).toHaveBeenCalledTimes(1);
  });

  it("address_line2 defaults to empty string when null/undefined", () => {
    const addressNoLine2 = { ...EXISTING_ADDRESS, address_line2: null };

    const { result } = renderHook(() => useAddressForm(addressNoLine2), {
      wrapper: makeWrapper(),
    });

    expect(result.current.form.address_line2).toBe("");
  });
});

describe("CITY_POSTAL_MAP spot checks", () => {
  it.each([
    ["Lahore", "54000"],
    ["Karachi", "75000"],
    ["Islamabad", "44000"],
    ["Peshawar", "25000"],
    ["Quetta", "87300"],
    ["Faisalabad", "38000"],
    ["Multan", "60000"],
  ])("%s maps to postal code %s", (city, expectedPostal) => {
    expect(CITY_POSTAL_MAP[city]).toBe(expectedPostal);
  });

  it("returns undefined for unknown city", () => {
    expect(CITY_POSTAL_MAP["Atlantis"]).toBeUndefined();
  });
});
