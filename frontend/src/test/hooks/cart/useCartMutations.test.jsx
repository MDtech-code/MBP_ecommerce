// src/tests/hooks/cart/useCartMutations.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import {
  useAddToCart,
  useUpdateCartItem,
  useRemoveCartItem,
  useClearCart,
} from "../../../hooks/cart/useCartMutations";

import { cartService } from "../../../services/cartService";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../services/cartService", () => ({
  cartService: {
    addToCart: vi.fn(),
    updateCartItem: vi.fn(),
    removeCartItem: vi.fn(),
    clearCart: vi.fn(),
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

const MOCK_UPDATED_CART = {
  data: {
    items: [{ id: 1, product_name: "Oil Filter", quantity: 3 }],
    total_items: 3,
    total_price: "750.00",
    is_empty: false,
  },
  message: "Success.",
};

// ─── useAddToCart ─────────────────────────────────────────────────────────────

describe("useAddToCart", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts in idle state", () => {
    const { result } = renderHook(() => useAddToCart(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isIdle).toBe(true);
  });

  it("calls cartService.addToCart with productId and quantity", async () => {
    cartService.addToCart.mockResolvedValue(MOCK_UPDATED_CART);

    const { result } = renderHook(() => useAddToCart(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ productId: 42, quantity: 2 });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cartService.addToCart).toHaveBeenCalledWith(42, 2);
  });

  it("transitions idle → pending → success", async () => {
    cartService.addToCart.mockResolvedValue(MOCK_UPDATED_CART);

    const { result } = renderHook(() => useAddToCart(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isIdle).toBe(true);

    act(() => {
      result.current.mutate({ productId: 1, quantity: 1 });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it("transitions to isError when cartService.addToCart rejects", async () => {
    cartService.addToCart.mockRejectedValue(new Error("Out of stock"));

    const { result } = renderHook(() => useAddToCart(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ productId: 1, quantity: 1 });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error.message).toBe("Out of stock");
  });
});

// ─── useUpdateCartItem ────────────────────────────────────────────────────────

describe("useUpdateCartItem", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.updateCartItem with itemId and quantity", async () => {
    cartService.updateCartItem.mockResolvedValue(MOCK_UPDATED_CART);

    const { result } = renderHook(() => useUpdateCartItem(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ itemId: 7, quantity: 3 });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cartService.updateCartItem).toHaveBeenCalledWith(7, 3);
  });

  it("allows quantity=0 which triggers server-side auto-delete", async () => {
    cartService.updateCartItem.mockResolvedValue(MOCK_UPDATED_CART);

    const { result } = renderHook(() => useUpdateCartItem(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ itemId: 7, quantity: 0 });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cartService.updateCartItem).toHaveBeenCalledWith(7, 0);
  });

  it("sets isError when service rejects", async () => {
    cartService.updateCartItem.mockRejectedValue(new Error("Update failed"));

    const { result } = renderHook(() => useUpdateCartItem(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ itemId: 7, quantity: 2 });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useRemoveCartItem ────────────────────────────────────────────────────────

describe("useRemoveCartItem", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.removeCartItem with itemId", async () => {
    cartService.removeCartItem.mockResolvedValue(MOCK_UPDATED_CART);

    const { result } = renderHook(() => useRemoveCartItem(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ itemId: 5 });
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cartService.removeCartItem).toHaveBeenCalledWith(5);
  });

  it("sets isError when service rejects", async () => {
    cartService.removeCartItem.mockRejectedValue(new Error("Remove failed"));

    const { result } = renderHook(() => useRemoveCartItem(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate({ itemId: 5 });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useClearCart ─────────────────────────────────────────────────────────────

describe("useClearCart", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.clearCart with no arguments", async () => {
    cartService.clearCart.mockResolvedValue(MOCK_UPDATED_CART);

    const { result } = renderHook(() => useClearCart(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(cartService.clearCart).toHaveBeenCalledWith();
  });

  it("sets isError when service rejects", async () => {
    cartService.clearCart.mockRejectedValue(new Error("Clear failed"));

    const { result } = renderHook(() => useClearCart(), {
      wrapper: makeWrapper(),
    });

    act(() => {
      result.current.mutate();
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});
