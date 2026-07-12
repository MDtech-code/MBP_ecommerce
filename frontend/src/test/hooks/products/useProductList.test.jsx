// src/test/hooks/products/useProductList.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useProductList } from "../../../hooks/products/useProductList";

// ─── Mocks ────────────────────────────────────────────────────────────────────

let mockProductsData = {
  products: [{ id: 1, name: "Brake Pad" }],
  meta: { page: 1, total_pages: 3, total: 25 },
};

let mockQueryState = {
  data: mockProductsData,
  isLoading: false,
  isError: false,
  error: null,
  isFetching: false,
};

vi.mock("../../../hooks/products/useProductQueries", () => ({
  useProducts: vi.fn(() => mockQueryState),
}));

vi.mock("../../../api/transformers", () => ({
  normalizeError: vi.fn((error) => ({
    message: error?.message ?? "Something went wrong.",
    isNotFound: false,
  })),
}));

// ─── Wrapper ──────────────────────────────────────────────────────────────────

/**
 * useProductList reads/writes URL search params.
 * MemoryRouter provides the routing context.
 * initialEntries lets us simulate pre-set URL params.
 */
const makeWrapper = (initialUrl = "/") => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialUrl]}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

// ─── Reset ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mockQueryState = {
    data: mockProductsData,
    isLoading: false,
    isError: false,
    error: null,
    isFetching: false,
  };
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("useProductList", () => {

  // ── Initial state ──────────────────────────────────────────────────────────

  it("returns products and meta from query", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.products).toEqual([{ id: 1, name: "Brake Pad" }]);
    expect(result.current.meta).toEqual({
      page: 1, total_pages: 3, total: 25,
    });
  });

  it("returns empty products when query data is undefined", () => {
    mockQueryState.data = undefined;

    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.products).toEqual([]);
  });

  it("returns empty meta when query data is undefined", () => {
    mockQueryState.data = undefined;

    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.meta).toEqual({});
  });

  it("exposes isLoading from query", () => {
    mockQueryState.isLoading = true;
    mockQueryState.data = undefined;

    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  it("exposes isFetching from query", () => {
    mockQueryState.isFetching = true;

    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isFetching).toBe(true);
  });

  // ── Default activeFilters from empty URL ───────────────────────────────────

  it("defaults sort to newest when no URL param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    expect(result.current.activeFilters.sort).toBe("newest");
  });

  it("defaults page to 1 when no URL param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    expect(result.current.activeFilters.page).toBe(1);
  });

  it("defaults all filter values to null when URL is empty", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    const { category, brand, bikeModel, minPrice, maxPrice, search, featured } =
      result.current.activeFilters;

    expect(category).toBeNull();
    expect(brand).toBeNull();
    expect(bikeModel).toBeNull();
    expect(minPrice).toBeNull();
    expect(maxPrice).toBeNull();
    expect(search).toBeNull();
    expect(featured).toBeNull();
  });

  // ── Reading filters from URL ───────────────────────────────────────────────

  it("reads category from URL params", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?category=brakes"),
    });

    expect(result.current.activeFilters.category).toBe("brakes");
  });

  it("reads brand from URL params", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?brand=honda"),
    });

    expect(result.current.activeFilters.brand).toBe("honda");
  });

  it("reads page from URL params as number", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?page=3"),
    });

    expect(result.current.activeFilters.page).toBe(3);
  });

  it("reads sort from URL params", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?sort=price_asc"),
    });

    expect(result.current.activeFilters.sort).toBe("price_asc");
  });

  // ── Filter setters ─────────────────────────────────────────────────────────

  it("setCategory updates URL and resets page", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?page=3"),
    });

    act(() => {
      result.current.setCategory("engine-parts");
    });

    expect(result.current.activeFilters.category).toBe("engine-parts");
    // page resets to 1
    expect(result.current.activeFilters.page).toBe(1);
  });

  it("setCategory with null removes param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?category=brakes"),
    });

    act(() => {
      result.current.setCategory(null);
    });

    expect(result.current.activeFilters.category).toBeNull();
  });

  it("setBrand updates URL and resets page", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?page=2"),
    });

    act(() => {
      result.current.setBrand("honda");
    });

    expect(result.current.activeFilters.brand).toBe("honda");
    expect(result.current.activeFilters.page).toBe(1);
  });

  it("setBikeModel updates URL param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    act(() => {
      result.current.setBikeModel("5");
    });

    expect(result.current.activeFilters.bikeModel).toBe("5");
  });

  it("setMinPrice updates URL param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    act(() => {
      result.current.setMinPrice("500");
    });

    expect(result.current.activeFilters.minPrice).toBe("500");
  });

  it("setMaxPrice updates URL param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    act(() => {
      result.current.setMaxPrice("5000");
    });

    expect(result.current.activeFilters.maxPrice).toBe("5000");
  });

  it("setSearch updates URL param", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/"),
    });

    act(() => {
      result.current.setSearch("brake pad");
    });

    expect(result.current.activeFilters.search).toBe("brake pad");
  });

  it("setSort updates sort param and resets page", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?sort=newest&page=3"),
    });

    act(() => {
      result.current.setSort("price_asc");
    });

    expect(result.current.activeFilters.sort).toBe("price_asc");
    expect(result.current.activeFilters.page).toBe(1);
  });

  it("setPage updates page param only — preserves other params", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?category=brakes&sort=newest"),
    });

    act(() => {
      result.current.setPage(4);
    });

    expect(result.current.activeFilters.page).toBe(4);
    expect(result.current.activeFilters.category).toBe("brakes");
    expect(result.current.activeFilters.sort).toBe("newest");
  });

  it("clearFilters removes all params", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper("/?category=brakes&brand=honda&page=3&sort=price_asc"),
    });

    act(() => {
      result.current.clearFilters();
    });

    const { category, brand, page, sort } = result.current.activeFilters;
    expect(category).toBeNull();
    expect(brand).toBeNull();
    expect(page).toBe(1);          // defaults to 1 after clear
    expect(sort).toBe("newest");   // defaults to newest after clear
  });

  // ── Error state ────────────────────────────────────────────────────────────

  it("exposes errorMessage when isError is true", () => {
    mockQueryState.isError = true;
    mockQueryState.error = new Error("Network Error");

    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isError).toBe(true);
    expect(result.current.errorMessage).toBe("Network Error");
  });

  it("errorMessage is null when no error", () => {
    const { result } = renderHook(() => useProductList(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.errorMessage).toBeNull();
  });

  // ── page_size fixed ────────────────────────────────────────────────────────

  // ✅ CORRECT — make it async
it("always sends page_size 12 to query", async () => {
  const { useProducts } = await import("../../../hooks/products/useProductQueries");

  renderHook(() => useProductList(), { wrapper: makeWrapper() });

  expect(vi.mocked(useProducts)).toHaveBeenCalledWith(
    expect.objectContaining({ page_size: 12 }),
  );
});
});