// src/tests/hooks/cart/useCart.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { useCart } from "../../../hooks/cart/useCart";
import { cartService } from "../../../services/cartService";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../services/cartService", () => ({
  cartService: {
    getCart: vi.fn(),
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

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const MOCK_CART = {
  items: [
    {
      id: 1,
      product_name: "Oil Filter",
      product_slug: "oil-filter",
      product_price: "250.00",
      product_image: null,
      is_in_stock: true,
      quantity: 2,
      subtotal: "500.00",
    },
  ],
  total_items: 2,
  total_price: "500.00",
  is_empty: false,
};

// Shape extractResponse returns — select() reads .data
const makeServiceResult = (data) => ({
  data,
  message: "Success.",
  meta: { request_id: "test-123" },
});

const MOCK_MUTATION_RESULT = makeServiceResult({
  ...MOCK_CART,
  total_items: 3,
});

// ─── Derived data ─────────────────────────────────────────────────────────────

describe("useCart — derived data from backend cart", () => {
  beforeEach(() => vi.clearAllMocks());

  it("exposes items array from cart.items", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.items).toEqual(MOCK_CART.items);
  });

  it("exposes totalItems from cart.total_items", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.totalItems).toBe(2);
  });

  it("exposes totalPrice from cart.total_price", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.totalPrice).toBe("500.00");
  });

  it("exposes isEmpty from cart.is_empty", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isEmpty).toBe(false);
  });
});

// ─── Safe defaults while loading ──────────────────────────────────────────────

describe("useCart — safe defaults before cart loads", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns empty array for items", () => {
    // never resolves — frozen in loading
    cartService.getCart.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.items).toEqual([]);
  });

  it("returns 0 for totalItems", () => {
    cartService.getCart.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.totalItems).toBe(0);
  });

  it("returns '0.00' for totalPrice", () => {
    cartService.getCart.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.totalPrice).toBe("0.00");
  });

  it("returns true for isEmpty", () => {
    cartService.getCart.mockReturnValue(new Promise(() => {}));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isEmpty).toBe(true);
  });
});

// ─── Error state ──────────────────────────────────────────────────────────────

describe("useCart — error state", () => {
  beforeEach(() => vi.clearAllMocks());

  it("sets isError true when getCart fails", async () => {
    cartService.getCart.mockRejectedValue(new Error("Fetch failed"));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });

  it("returns non-null errorMessage when getCart fails", async () => {
    cartService.getCart.mockRejectedValue(new Error("Fetch failed"));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));

    // normalizeError always produces a message string
    expect(result.current.errorMessage).not.toBeNull();
    expect(typeof result.current.errorMessage).toBe("string");
  });

  it("errorMessage is null when cart loads successfully", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.errorMessage).toBeNull();
  });
});

// ─── handleIncrease ───────────────────────────────────────────────────────────

describe("useCart — handleIncrease", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.updateCartItem with quantity + 1", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));
    cartService.updateCartItem.mockResolvedValue(MOCK_MUTATION_RESULT);

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.handleIncrease(1, 2); // itemId=1, currentQty=2
    });

    await waitFor(() =>
      expect(cartService.updateCartItem).toHaveBeenCalledWith(1, 3),
    );
  });
});

// ─── handleDecrease ───────────────────────────────────────────────────────────

describe("useCart — handleDecrease", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.updateCartItem with quantity - 1", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));
    cartService.updateCartItem.mockResolvedValue(MOCK_MUTATION_RESULT);

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.handleDecrease(1, 2); // itemId=1, currentQty=2
    });

    await waitFor(() =>
      expect(cartService.updateCartItem).toHaveBeenCalledWith(1, 1),
    );
  });

  it("sends quantity=0 when decreasing from 1 — triggers server-side delete", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));
    cartService.updateCartItem.mockResolvedValue(MOCK_MUTATION_RESULT);

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.handleDecrease(1, 1); // qty=1 → sends 0
    });

    await waitFor(() =>
      expect(cartService.updateCartItem).toHaveBeenCalledWith(1, 0),
    );
  });
});

// ─── handleRemove ─────────────────────────────────────────────────────────────

describe("useCart — handleRemove", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.removeCartItem with itemId", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));
    cartService.removeCartItem.mockResolvedValue(MOCK_MUTATION_RESULT);

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.handleRemove(1);
    });

    await waitFor(() =>
      expect(cartService.removeCartItem).toHaveBeenCalledWith(1),
    );
  });
});

// ─── handleClearCart ──────────────────────────────────────────────────────────

describe("useCart — handleClearCart", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.clearCart", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));
    cartService.clearCart.mockResolvedValue(MOCK_MUTATION_RESULT);

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.handleClearCart();
    });

    await waitFor(() => expect(cartService.clearCart).toHaveBeenCalled());
  });
});

// ─── handleAddToCart ──────────────────────────────────────────────────────────

describe("useCart — handleAddToCart", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls cartService.addToCart with productId and quantity", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));
    cartService.addToCart.mockResolvedValue(MOCK_MUTATION_RESULT);

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    act(() => {
      result.current.handleAddToCart(99, 1);
    });

    await waitFor(() =>
      expect(cartService.addToCart).toHaveBeenCalledWith(99, 1),
    );
  });
});

// ─── isMutating ───────────────────────────────────────────────────────────────

describe("useCart — isMutating", () => {
  beforeEach(() => vi.clearAllMocks());

  it("is false when no mutation is pending", async () => {
    cartService.getCart.mockResolvedValue(makeServiceResult(MOCK_CART));

    const { result } = renderHook(() => useCart(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isLoading).toBe(false));

    expect(result.current.isMutating).toBe(false);
  });
});
