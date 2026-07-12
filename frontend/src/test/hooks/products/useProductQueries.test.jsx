// src/test/hooks/products/useProductQueries.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import {
  useCategoriesTree,
  useCategoriesFlat,
  useBrands,
  useBikeModels,
  useProducts,
  useProductDetail,
} from "../../../hooks/products/useProductQueries";

import { productService } from "../../../services/productService";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../services/productService", () => ({
  productService: {
    getCategoriesTree: vi.fn(),
    getCategoriesFlat: vi.fn(),
    getBrands: vi.fn(),
    getBikeModels: vi.fn(),
    getProducts: vi.fn(),
    getProductBySlug: vi.fn(),
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
 * Simulates the shape extractResponse returns from the backend.
 * select() in each query reads result.data and result.meta.
 */
const makeServiceResult = (data, meta = {}) => ({
  data,
  message: "Success.",
  meta: { request_id: "test-123", ...meta },
});

// ─── useCategoriesTree ────────────────────────────────────────────────────────

describe("useCategoriesTree", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns empty array while loading", () => {
    productService.getCategoriesTree.mockResolvedValue(
      makeServiceResult([]),
    );
    const { result } = renderHook(() => useCategoriesTree(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it("returns category tree data on success", async () => {
    const tree = [
      { id: 1, name: "Engine Parts", slug: "engine-parts", children: [] },
    ];
    productService.getCategoriesTree.mockResolvedValue(
      makeServiceResult(tree),
    );

    const { result } = renderHook(() => useCategoriesTree(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // select() returns result.data ?? []
    expect(result.current.data).toEqual(tree);
  });

  it("returns empty array when data is null via select fallback", async () => {
    productService.getCategoriesTree.mockResolvedValue(
      makeServiceResult(null),
    );

    const { result } = renderHook(() => useCategoriesTree(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });

  it("uses correct query key [categories, tree]", async () => {
    productService.getCategoriesTree.mockResolvedValue(
      makeServiceResult([]),
    );

    const { result } = renderHook(() => useCategoriesTree(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(productService.getCategoriesTree).toHaveBeenCalledTimes(1);
  });

  it("sets isError on service failure", async () => {
    productService.getCategoriesTree.mockRejectedValue(
      new Error("Network Error"),
    );

    const { result } = renderHook(() => useCategoriesTree(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useCategoriesFlat ────────────────────────────────────────────────────────

describe("useCategoriesFlat", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns flat category list on success", async () => {
    const flat = [
      { id: 1, name: "Brakes", slug: "brakes", is_subcategory: false },
    ];
    productService.getCategoriesFlat.mockResolvedValue(
      makeServiceResult(flat),
    );

    const { result } = renderHook(() => useCategoriesFlat(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(flat);
  });

  it("falls back to empty array when data is null", async () => {
    productService.getCategoriesFlat.mockResolvedValue(
      makeServiceResult(null),
    );

    const { result } = renderHook(() => useCategoriesFlat(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });

  it("sets isError when service fails", async () => {
    productService.getCategoriesFlat.mockRejectedValue(
      new Error("Network Error"),
    );

    const { result } = renderHook(() => useCategoriesFlat(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useBrands ────────────────────────────────────────────────────────────────

describe("useBrands", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns brand list on success", async () => {
    const brands = [
      { id: 1, name: "Honda", slug: "honda" },
      { id: 2, name: "Yamaha", slug: "yamaha" },
    ];
    productService.getBrands.mockResolvedValue(makeServiceResult(brands));

    const { result } = renderHook(() => useBrands(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(brands);
  });

  it("falls back to empty array when data is null", async () => {
    productService.getBrands.mockResolvedValue(makeServiceResult(null));

    const { result } = renderHook(() => useBrands(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });

  it("sets isError on failure", async () => {
    productService.getBrands.mockRejectedValue(new Error("Network Error"));

    const { result } = renderHook(() => useBrands(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useBikeModels ────────────────────────────────────────────────────────────

describe("useBikeModels", () => {
  beforeEach(() => vi.clearAllMocks());

  it("fetches all models when brandId is null (default)", async () => {
    const models = [{ id: 1, display_name: "Honda CD70 2023" }];
    productService.getBikeModels.mockResolvedValue(makeServiceResult(models));

    const { result } = renderHook(() => useBikeModels(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(productService.getBikeModels).toHaveBeenCalledWith(null);
    expect(result.current.data).toEqual(models);
  });

  it("passes brandId to service when provided", async () => {
    productService.getBikeModels.mockResolvedValue(makeServiceResult([]));

    const { result } = renderHook(() => useBikeModels(3), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(productService.getBikeModels).toHaveBeenCalledWith(3);
  });

  it("uses brandId in query key — different brandIds = different cache entries", async () => {
    productService.getBikeModels.mockResolvedValue(makeServiceResult([]));

    // brandId=1
    const { result: r1 } = renderHook(() => useBikeModels(1), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(r1.current.isSuccess).toBe(true));

    // brandId=2 — fresh wrapper = fresh cache
    const { result: r2 } = renderHook(() => useBikeModels(2), {
      wrapper: makeWrapper(),
    });
    await waitFor(() => expect(r2.current.isSuccess).toBe(true));

    expect(productService.getBikeModels).toHaveBeenCalledWith(1);
    expect(productService.getBikeModels).toHaveBeenCalledWith(2);
  });

  it("falls back to empty array when data is null", async () => {
    productService.getBikeModels.mockResolvedValue(makeServiceResult(null));

    const { result } = renderHook(() => useBikeModels(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([]);
  });
});

// ─── useProducts ──────────────────────────────────────────────────────────────

describe("useProducts", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns products and meta on success", async () => {
    const products = [{ id: 1, name: "Brake Pad", slug: "brake-pad" }];
    const meta = { page: 1, total_pages: 3, total: 25 };

    productService.getProducts.mockResolvedValue(
      makeServiceResult(products, meta),
    );

    const { result } = renderHook(() => useProducts({ category: "brakes" }), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // select() returns { products: result.data, meta: result.meta }
    expect(result.current.data.products).toEqual(products);
    expect(result.current.data.meta).toEqual({
      request_id: "test-123",
      ...meta,
    });
  });

  it("returns empty products array when data is null", async () => {
    productService.getProducts.mockResolvedValue(makeServiceResult(null));

    const { result } = renderHook(() => useProducts(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data.products).toEqual([]);
  });

  it("returns empty meta object when meta is null", async () => {
    productService.getProducts.mockResolvedValue({
      data: [],
      message: "Success.",
      meta: null,
    });

    const { result } = renderHook(() => useProducts(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data.meta).toEqual({});
  });

  it("passes full filters object to service", async () => {
    productService.getProducts.mockResolvedValue(makeServiceResult([]));

    const filters = { category: "brakes", brand: "honda", page: 2 };

    const { result } = renderHook(() => useProducts(filters), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(productService.getProducts).toHaveBeenCalledWith(filters);
  });

  it("sets isError on service failure", async () => {
    productService.getProducts.mockRejectedValue(new Error("Network Error"));

    const { result } = renderHook(() => useProducts(), {
      wrapper: makeWrapper(),
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ─── useProductDetail ─────────────────────────────────────────────────────────

describe("useProductDetail", () => {
  beforeEach(() => vi.clearAllMocks());

  it("does NOT fire query when slug is undefined", () => {
    const { result } = renderHook(() => useProductDetail(undefined), {
      wrapper: makeWrapper(),
    });

    // enabled: !!slug → false when undefined
    expect(result.current.fetchStatus).toBe("idle");
    expect(productService.getProductBySlug).not.toHaveBeenCalled();
  });

  it("does NOT fire query when slug is empty string", () => {
    const { result } = renderHook(() => useProductDetail(""), {
      wrapper: makeWrapper(),
    });

    expect(result.current.fetchStatus).toBe("idle");
    expect(productService.getProductBySlug).not.toHaveBeenCalled();
  });

  it("fires query when slug is provided", async () => {
    const product = { id: 1, name: "Brake Pad", slug: "brake-pad" };
    productService.getProductBySlug.mockResolvedValue(
      makeServiceResult(product),
    );

    const { result } = renderHook(
      () => useProductDetail("brake-pad"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(productService.getProductBySlug).toHaveBeenCalledWith("brake-pad");
  });

  it("returns product data via select", async () => {
    const product = {
      id: 1,
      name: "Brake Pad",
      slug: "brake-pad",
      current_price: "450.00",
    };
    productService.getProductBySlug.mockResolvedValue(
      makeServiceResult(product),
    );

    const { result } = renderHook(
      () => useProductDetail("brake-pad"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    // select() returns result.data ?? null
    expect(result.current.data).toEqual(product);
  });

  it("returns null via select when data is null", async () => {
    productService.getProductBySlug.mockResolvedValue(
      makeServiceResult(null),
    );

    const { result } = renderHook(
      () => useProductDetail("some-slug"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
  });

  it("sets isError on 404", async () => {
    const error = new Error("Not Found");
    error.response = { status: 404 };
    productService.getProductBySlug.mockRejectedValue(error);

    const { result } = renderHook(
      () => useProductDetail("bad-slug"),
      { wrapper: makeWrapper() },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));

    expect(result.current.error).toBe(error);
  });
});