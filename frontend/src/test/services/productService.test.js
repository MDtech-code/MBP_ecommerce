// src/test/services/productService.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { productService } from "../../services/productService";
import { api } from "../../api/client";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../api/client", () => ({
  api: {
    get: vi.fn(),
  },
}));

vi.mock("../../api/transformers", () => ({
  extractResponse: vi.fn((response) => response.data),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

const mockSuccessEnvelope = (data, meta = {}) => ({
  data: {
    success: true,
    message: "Success.",
    data,
    errors: null,
    meta: { request_id: "test-123", ...meta },
  },
});

// ─── getCategoriesTree ────────────────────────────────────────────────────────

describe("productService.getCategoriesTree", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls correct endpoint with view=tree param", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getCategoriesTree();

    expect(api.get).toHaveBeenCalledWith("/api/products/categories/", {
      params: { view: "tree" },
    });
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it("returns extracted response data", async () => {
    const treeData = [
      { id: 1, name: "Engine Parts", slug: "engine-parts", children: [] },
    ];
    api.get.mockResolvedValue(mockSuccessEnvelope(treeData));

    const result = await productService.getCategoriesTree();

    expect(result).toEqual(mockSuccessEnvelope(treeData).data);
  });

  it("does not catch errors — lets them bubble up", async () => {
    api.get.mockRejectedValue(new Error("Network Error"));

    await expect(productService.getCategoriesTree()).rejects.toThrow(
      "Network Error",
    );
  });
});

// ─── getCategoriesFlat ────────────────────────────────────────────────────────

describe("productService.getCategoriesFlat", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls correct endpoint with view=flat param", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getCategoriesFlat();

    expect(api.get).toHaveBeenCalledWith("/api/products/categories/", {
      params: { view: "flat" },
    });
  });

  it("returns extracted response", async () => {
    const flatData = [
      { id: 1, name: "Brakes", slug: "brakes", is_subcategory: false },
      { id: 2, name: "Brake Pads", slug: "brake-pads", is_subcategory: true },
    ];
    api.get.mockResolvedValue(mockSuccessEnvelope(flatData));

    const result = await productService.getCategoriesFlat();

    expect(result).toEqual(mockSuccessEnvelope(flatData).data);
  });

  it("bubbles up network errors", async () => {
    api.get.mockRejectedValue(new Error("Network Error"));

    await expect(productService.getCategoriesFlat()).rejects.toThrow(
      "Network Error",
    );
  });
});

// ─── getBrands ────────────────────────────────────────────────────────────────

describe("productService.getBrands", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls correct endpoint with no params", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getBrands();

    expect(api.get).toHaveBeenCalledWith("/api/products/brands/");
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it("returns extracted brand list", async () => {
    const brands = [
      { id: 1, name: "Honda", slug: "honda", logo: "/media/honda.png" },
      { id: 2, name: "Yamaha", slug: "yamaha", logo: null },
    ];
    api.get.mockResolvedValue(mockSuccessEnvelope(brands));

    const result = await productService.getBrands();

    expect(result).toEqual(mockSuccessEnvelope(brands).data);
  });

  it("bubbles up errors without catching", async () => {
    const error = new Error("Request failed with status 500");
    api.get.mockRejectedValue(error);

    await expect(productService.getBrands()).rejects.toThrow(
      "Request failed with status 500",
    );
  });
});

// ─── getBikeModels ────────────────────────────────────────────────────────────

describe("productService.getBikeModels", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls endpoint with no params when brandId is null", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getBikeModels(null);

    expect(api.get).toHaveBeenCalledWith("/api/products/bike-models/", {
      params: {},
    });
  });

  it("calls endpoint with no params when brandId is not provided", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getBikeModels();

    expect(api.get).toHaveBeenCalledWith("/api/products/bike-models/", {
      params: {},
    });
  });

  it("calls endpoint with brand param when brandId is provided", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getBikeModels(5);

    expect(api.get).toHaveBeenCalledWith("/api/products/bike-models/", {
      params: { brand: 5 },
    });
  });

  it("returns extracted bike model list", async () => {
    const models = [
      { id: 1, display_name: "Honda CD70 2023" },
      { id: 2, display_name: "Honda CG125 2023" },
    ];
    api.get.mockResolvedValue(mockSuccessEnvelope(models));

    const result = await productService.getBikeModels(1);

    expect(result).toEqual(mockSuccessEnvelope(models).data);
  });

  it("bubbles up errors", async () => {
    api.get.mockRejectedValue(new Error("Network Error"));

    await expect(productService.getBikeModels(1)).rejects.toThrow(
      "Network Error",
    );
  });
});

// ─── getProducts ──────────────────────────────────────────────────────────────

describe("productService.getProducts", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls correct endpoint with no params when filters is empty", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getProducts();

    expect(api.get).toHaveBeenCalledWith("/api/products/", { params: {} });
  });

  it("strips null values from filters", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getProducts({
      category: "brakes",
      brand: null,
      min_price: null,
    });

    expect(api.get).toHaveBeenCalledWith("/api/products/", {
      params: { category: "brakes" },
    });
  });

  it("strips undefined values from filters", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getProducts({
      category: "brakes",
      brand: undefined,
      q: undefined,
    });

    expect(api.get).toHaveBeenCalledWith("/api/products/", {
      params: { category: "brakes" },
    });
  });

  it("strips empty string values from filters", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    await productService.getProducts({
      category: "",
      brand: "honda",
      q: "",
    });

    expect(api.get).toHaveBeenCalledWith("/api/products/", {
      params: { brand: "honda" },
    });
  });

  it("passes all valid truthy filters to API", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope([]));

    const filters = {
      category: "brakes",
      brand: "honda",
      bike_model: 1,
      min_price: 500,
      max_price: 5000,
      q: "brake pad",
      featured: true,
      sort: "newest",
      page: 2,
      page_size: 12,
    };

    await productService.getProducts(filters);

    expect(api.get).toHaveBeenCalledWith("/api/products/", {
      params: filters,
    });
  });

  it("returns extracted product list with meta", async () => {
    const products = [{ id: 1, name: "Brake Pad", slug: "brake-pad" }];
    const meta = { page: 1, total_pages: 3, total: 25 };

    api.get.mockResolvedValue(mockSuccessEnvelope(products, meta));

    const result = await productService.getProducts({ category: "brakes" });

    expect(result).toEqual(mockSuccessEnvelope(products, meta).data);
  });

  it("bubbles up 400 validation errors", async () => {
    const error = new Error("Request failed with status 400");
    api.get.mockRejectedValue(error);

    await expect(productService.getProducts({ page: -1 })).rejects.toThrow();
  });
});

// ─── getProductBySlug ─────────────────────────────────────────────────────────

describe("productService.getProductBySlug", () => {
  beforeEach(() => vi.clearAllMocks());

  it("calls correct endpoint with slug", async () => {
    api.get.mockResolvedValue(mockSuccessEnvelope({}));

    await productService.getProductBySlug("honda-brake-pad");

    expect(api.get).toHaveBeenCalledWith("/api/products/honda-brake-pad/");
    expect(api.get).toHaveBeenCalledTimes(1);
  });

  it("returns extracted product detail", async () => {
    const product = {
      id: 1,
      name: "Honda Brake Pad",
      slug: "honda-brake-pad",
      current_price: "450.00",
      price: "550.00",
      has_discount: true,
      discount_percentage: 18,
      is_in_stock: true,
    };
    api.get.mockResolvedValue(mockSuccessEnvelope(product));

    const result = await productService.getProductBySlug("honda-brake-pad");

    expect(result).toEqual(mockSuccessEnvelope(product).data);
  });

  it("bubbles up 404 errors", async () => {
    const error = new Error("Request failed with status 404");
    error.response = { status: 404, data: { success: false } };
    api.get.mockRejectedValue(error);

    await expect(
      productService.getProductBySlug("non-existent-slug"),
    ).rejects.toThrow();
  });

  it("does not catch network errors", async () => {
    api.get.mockRejectedValue(new Error("Network Error"));

    await expect(productService.getProductBySlug("some-slug")).rejects.toThrow(
      "Network Error",
    );
  });
});
