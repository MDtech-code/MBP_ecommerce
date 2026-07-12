// src/test/hooks/products/useProductDetail.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { useProductDetail } from "../../../hooks/products/useProductDetail";

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Controlled slug from URL
let mockSlug = "honda-brake-pad";

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    useParams: () => ({ slug: mockSlug }),
  };
});

// Controlled query result
let mockQueryResult = {
  data: null,
  isLoading: false,
  isError: false,
  error: null,
};

vi.mock("../../../hooks/products/useProductQueries", () => ({
  useProductDetail: vi.fn(() => mockQueryResult),
}));

vi.mock("../../../api/transformers", () => ({
  normalizeError: vi.fn((error) => ({
    message: error?.message ?? "Something went wrong.",
    isNotFound: error?.response?.status === 404,
  })),
}));

// ─── Wrapper ──────────────────────────────────────────────────────────────────

const makeWrapper = () => ({ children }) => (
  <MemoryRouter>{children}</MemoryRouter>
);

// ─── Full product fixture ──────────────────────────────────────────────────────

const makeProduct = (overrides = {}) => ({
  id: 1,
  name: "Honda Brake Pad",
  slug: "honda-brake-pad",
  description: "High quality brake pad",
  sku: "HBP-001",
  current_price: "450.00",
  price: "550.00",
  has_discount: true,
  discount_percentage: 18,
  is_in_stock: true,
  is_featured: false,
  stock: 25,
  primary_bike: "Honda CD70",
  brand: { name: "Honda", logo: "/media/honda.png" },
  category: {
    name: "Brake System",
    slug: "brake-system",
    parent: "engine-parts",
    parent_name: "Engine Parts",
  },
  images: [
    { id: 1, image: "/media/img1.jpg", is_primary: true,  order: 1 },
    { id: 2, image: "/media/img2.jpg", is_primary: false, order: 2 },
    { id: 3, image: "/media/img3.jpg", is_primary: false, order: 0 },
  ],
  compatible_bikes: [
    { display_name: "Honda CD70 2023" },
    { display_name: "Honda CG125 2022" },
  ],
  related_products: [
    { id: 2, name: "Yamaha Brake Pad" },
  ],
  ...overrides,
});

// ─── Reset ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();
  mockSlug = "honda-brake-pad";
  mockQueryResult = {
    data: null,
    isLoading: false,
    isError: false,
    error: null,
  };
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("useProductDetail", () => {

  // ── Loading state ──────────────────────────────────────────────────────────

  it("exposes isLoading from query", () => {
    mockQueryResult.isLoading = true;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isLoading).toBe(true);
  });

  // ── Null product (no data yet) ─────────────────────────────────────────────

  it("returns null product when data is null", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.product).toBeNull();
  });

  it("returns null name when product is null", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.name).toBeNull();
  });

  it("returns empty images array when product is null", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.images).toEqual([]);
  });

  it("returns empty compatibleBikes when product is null", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.compatibleBikes).toEqual([]);
  });

  // ── Loaded product ─────────────────────────────────────────────────────────

  it("exposes raw product object", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.product).toEqual(product);
  });

  it("exposes convenience shorthand fields", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.name).toBe("Honda Brake Pad");
    expect(result.current.sku).toBe("HBP-001");
    expect(result.current.brandName).toBe("Honda");
    expect(result.current.brandLogo).toBe("/media/honda.png");
    expect(result.current.categoryName).toBe("Brake System");
    expect(result.current.hasDiscount).toBe(true);
    expect(result.current.discountPercentage).toBe(18);
    expect(result.current.isInStock).toBe(true);
    expect(result.current.stock).toBe(25);
    expect(result.current.isFeatured).toBe(false);
  });

  it("exposes relatedProducts array", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.relatedProducts).toEqual([
      { id: 2, name: "Yamaha Brake Pad" },
    ]);
  });

  // ── Images — sorted by order, primary first ────────────────────────────────

  it("sorts images by order ascending", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    // order: 0, 1, 2
    expect(result.current.images[0].order).toBe(0);
    expect(result.current.images[1].order).toBe(1);
    expect(result.current.images[2].order).toBe(2);
  });

  it("builds imageUrls array in sorted order", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.imageUrls).toEqual([
      "/media/img3.jpg", // order 0
      "/media/img1.jpg", // order 1
      "/media/img2.jpg", // order 2
    ]);
  });

  it("returns primaryImageUrl from is_primary=true image", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.primaryImageUrl).toBe("/media/img1.jpg");
  });

  it("falls back to first image when no is_primary image exists", () => {
    const product = makeProduct({
      images: [
        { id: 1, image: "/media/img1.jpg", is_primary: false, order: 1 },
        { id: 2, image: "/media/img2.jpg", is_primary: false, order: 2 },
      ],
    });
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    // first image after sort by order
    expect(result.current.primaryImageUrl).toBe("/media/img1.jpg");
  });

  it("returns null primaryImageUrl when images array is empty", () => {
    const product = makeProduct({ images: [] });
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.primaryImageUrl).toBeNull();
  });

  // ── compatibleBikes ────────────────────────────────────────────────────────

  it("maps compatible_bikes to display_name strings", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.compatibleBikes).toEqual([
      "Honda CD70 2023",
      "Honda CG125 2022",
    ]);
  });

  // ── displayPrice / originalPrice ───────────────────────────────────────────

  it("formats displayPrice as Rs. with locale string", () => {
    const product = makeProduct({ current_price: "1500.00" });
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.displayPrice).toBe("Rs. 1,500");
  });

  it("shows originalPrice when has_discount is true", () => {
    const product = makeProduct({ has_discount: true, price: "2000.00" });
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.originalPrice).toBe("Rs. 2,000");
  });

  it("returns null originalPrice when has_discount is false", () => {
    const product = makeProduct({ has_discount: false });
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.originalPrice).toBeNull();
  });

  it("returns null displayPrice when product is null", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.displayPrice).toBeNull();
  });

  // ── Breadcrumb ─────────────────────────────────────────────────────────────

  it("builds breadcrumb with Home, parent category, category, product", () => {
    const product = makeProduct();
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.breadcrumb).toEqual([
      { label: "Home", to: "/" },
      { label: "Engine Parts", to: "/product?category=engine-parts" },
      { label: "Brake System", to: "/product?category=brake-system" },
      { label: "Honda Brake Pad", to: null },
    ]);
  });

  it("skips parent breadcrumb when category has no parent_name", () => {
    const product = makeProduct({
      category: {
        name: "Brake System",
        slug: "brake-system",
        parent: null,
        parent_name: null,
      },
    });
    mockQueryResult.data = product;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.breadcrumb).toEqual([
      { label: "Home", to: "/" },
      { label: "Brake System", to: "/product?category=brake-system" },
      { label: "Honda Brake Pad", to: null },
    ]);
  });

  it("returns minimal breadcrumb when product is null", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    // Only Home survives the filter(Boolean)
    expect(result.current.breadcrumb).toEqual([
      { label: "Home", to: "/" },
    ]);
  });

  // ── Error handling ─────────────────────────────────────────────────────────

  it("exposes isError from query", () => {
    mockQueryResult.isError = true;
    mockQueryResult.error = new Error("Network Error");

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isError).toBe(true);
  });

  it("exposes errorMessage when isError is true", () => {
    mockQueryResult.isError = true;
    mockQueryResult.error = new Error("Network Error");

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.errorMessage).toBe("Network Error");
  });

  it("detects 404 and sets isNotFound true", () => {
    const error = new Error("Not Found");
    error.response = { status: 404 };
    mockQueryResult.isError = true;
    mockQueryResult.error = error;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isNotFound).toBe(true);
  });

  it("isNotFound is false for non-404 errors", () => {
    const error = new Error("Server Error");
    error.response = { status: 500 };
    mockQueryResult.isError = true;
    mockQueryResult.error = error;

    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.isNotFound).toBe(false);
  });

  it("errorMessage is null when no error", () => {
    const { result } = renderHook(() => useProductDetail(), {
      wrapper: makeWrapper(),
    });

    expect(result.current.errorMessage).toBeNull();
  });
});