// src/tests/hooks/cart/useCartQueries.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import {
  useCartQuery,
  CART_QUERY_KEY,
} from "../../../hooks/cart/useCartQueries";

import { cartService } from "../../../services/cartService";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../services/cartService", () => ({
  cartService: {
    getCart: vi.fn(),
  },
}));

// ─── Wrapper ──────────────────────────────────────────────────────────────────

const makeWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Matches the shape extractResponse returns.
 * select() in useCartQuery reads result.data ?? null
 */
const makeServiceResult = (data) => ({
  data,
  message: "Success.",
  meta: { request_id: "test-123" },
});

// ─── CART_QUERY_KEY ───────────────────────────────────────────────────────────

describe("CART_QUERY_KEY", () => {
  it("is ['cart']", () => {
    expect(CART_QUERY_KEY).toEqual(["cart"]);
  });
});

// ─── useCartQuery ─────────────────────────────────────────────────────────────

describe("useCartQuery", () => {
  beforeEach(() => vi.clearAllMocks());

  it("is in loading state on mount before service resolves", () => {
    // never resolves — keep loading state frozen
    cartService.getCart.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useCartQuery(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("calls cartService.getCart on mount", async () => {
    const MOCK_CART = {
      items: [],
      total_items: 0,
      total_price: "0.00",
      is_empty: true,
    };
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    renderHook(() => useCartQuery(), { wrapper: makeWrapper() });

    await waitFor(() => expect(cartService.getCart).toHaveBeenCalledTimes(1));
  });

  it("returns cart data via select(result.data) on success", async () => {
    const MOCK_CART = {
      items: [{ id: 1, product_name: "Oil Filter", quantity: 2 }],
      total_items: 2,
      total_price: "500.00",
      is_empty: false,
    };
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCartQuery(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // select() extracts result.data — so we get MOCK_CART directly
    expect(result.current.data).toEqual(MOCK_CART);
  });

  it("returns null via select when data is null", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(null));

    const { result } = renderHook(() => useCartQuery(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
  });

  it("sets isError true when cartService.getCart rejects", async () => {
    cartService.getCart.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useCartQuery(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error.message).toBe("Network error");
  });
});
