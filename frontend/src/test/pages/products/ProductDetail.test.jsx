// src/test/pages/products/ProductDetail.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ProductDetail from "../../../pages/products/ProductDetail";

// ─── Mock all child components ────────────────────────────────────────────────

vi.mock("../../../components/layout/Header", () => ({
  default: () => <div data-testid="header" />,
}));

vi.mock("../../../components/product-detail/ProductGallery", () => ({
  default: ({ images }) => (
    <div data-testid="gallery">{images.length} images</div>
  ),
}));

vi.mock("../../../components/product-detail/ProductInfo", () => ({
  default: ({ product }) => (
    <div data-testid="product-info">{product?.name}</div>
  ),
}));

vi.mock("../../../components/product-detail/ProductActions", () => ({
  default: ({ isInStock, stock }) => (
    <div data-testid="product-actions">
      {isInStock ? "in-stock" : "out-of-stock"} | stock:{stock}
    </div>
  ),
}));

vi.mock("../../../components/product-detail/ProductTrust", () => ({
  default: () => <div data-testid="product-trust" />,
}));

vi.mock("../../../components/product-detail/ProductTabs", () => ({
  default: ({ product }) => (
    <div data-testid="product-tabs">{product?.sku}</div>
  ),
}));

vi.mock("../../../components/product-detail/RelatedProducts", () => ({
  default: ({ products }) => (
    <div data-testid="related-products">{products.length} related</div>
  ),
}));

// ─── Mock useProductDetail ────────────────────────────────────────────────────

const mockHookState = {
  product:         null,
  isLoading:       false,
  isError:         false,
  isNotFound:      false,
  errorMessage:    null,
  images:          [],
  breadcrumb:      [{ label: "Home", to: "/" }],
  relatedProducts: [],
  isInStock:       true,
  stock:           10,
};

vi.mock("../../../hooks/products/useProductDetail", () => ({
  useProductDetail: vi.fn(() => mockHookState),
}));

import { useProductDetail } from "../../../hooks/products/useProductDetail";

// ─── Helper ───────────────────────────────────────────────────────────────────

function renderPage() {
  return render(
    <MemoryRouter>
      <ProductDetail />
    </MemoryRouter>,
  );
}

// ─── Reset ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  useProductDetail.mockReturnValue({
    product: {
      name:        "Honda Brake Pad",
      sku:         "HBP-001",
      description: "Quality part.",
    },
    isLoading:       false,
    isError:         false,
    isNotFound:      false,
    errorMessage:    null,
    images:          [{ id: 1, image: "/img.jpg", is_primary: true, order: 1 }],
    breadcrumb: [
      { label: "Home",        to: "/"                          },
      { label: "Brake System", to: "/product?category=brakes"  },
      { label: "Honda Brake Pad", to: null                     },
    ],
    relatedProducts: [{ id: 2, name: "Yamaha Pad" }],
    isInStock:       true,
    stock:           10,
  });
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductDetail Page", () => {

  // ── Loading skeleton ───────────────────────────────────────────────────────

  it("renders loading skeleton when isLoading is true", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isLoading: true,
    });
    renderPage();

    // Skeleton has animate-pulse divs
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders header even during loading", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isLoading: true,
    });
    renderPage();

    expect(screen.getByTestId("header")).toBeInTheDocument();
  });

  it("does not render product components while loading", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isLoading: true,
    });
    renderPage();

    expect(screen.queryByTestId("gallery")).not.toBeInTheDocument();
    expect(screen.queryByTestId("product-info")).not.toBeInTheDocument();
  });

  // ── 404 state ──────────────────────────────────────────────────────────────

  it("shows Product Not Found when isNotFound is true", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isNotFound: true,
      isError:    true,
    });
    renderPage();

    expect(screen.getByText("Product Not Found")).toBeInTheDocument();
  });

  it("shows 404 description text", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isNotFound: true,
      isError:    true,
    });
    renderPage();

    expect(
      screen.getByText(/does not exist or has been removed/),
    ).toBeInTheDocument();
  });

  it("shows Browse All Products link on 404", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isNotFound: true,
      isError:    true,
    });
    renderPage();

    expect(
      screen.getByRole("link", { name: "Browse All Products" }),
    ).toHaveAttribute("href", "/product");
  });

  it("shows wrench emoji on 404", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isNotFound: true,
      isError:    true,
    });
    renderPage();

    expect(screen.getByText("🔧")).toBeInTheDocument();
  });

  // ── Generic error state ────────────────────────────────────────────────────

  it("shows Failed to load product on generic error", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isError:     true,
      isNotFound:  false,
      errorMessage: "Network Error",
    });
    renderPage();

    expect(screen.getByText("Failed to load product")).toBeInTheDocument();
  });

  it("shows errorMessage in generic error state", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isError:      true,
      isNotFound:   false,
      errorMessage: "Network Error",
    });
    renderPage();

    expect(screen.getByText("Network Error")).toBeInTheDocument();
  });

  it("shows fallback error message when errorMessage is null", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      isError:      true,
      isNotFound:   false,
      errorMessage: null,
    });
    renderPage();

    expect(
      screen.getByText("Something went wrong. Please try again."),
    ).toBeInTheDocument();
  });

  it("shows Try Again button that triggers reload", () => {
    const reloadMock = vi.fn();
    Object.defineProperty(window, "location", {
      value:    { reload: reloadMock },
      writable: true,
    });

    useProductDetail.mockReturnValue({
      ...mockHookState,
      isError:    true,
      isNotFound: false,
    });
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Try Again" }));
    expect(reloadMock).toHaveBeenCalledTimes(1);
  });

  // ── Success state — renders all components ─────────────────────────────────

  it("renders header on success", () => {
    renderPage();
    expect(screen.getByTestId("header")).toBeInTheDocument();
  });

  it("renders ProductGallery with images", () => {
    renderPage();
    expect(screen.getByTestId("gallery")).toHaveTextContent("1 images");
  });

  it("renders ProductInfo with product", () => {
    renderPage();
    expect(screen.getByTestId("product-info")).toHaveTextContent(
      "Honda Brake Pad",
    );
  });

  it("renders ProductActions with isInStock and stock", () => {
    renderPage();
    expect(screen.getByTestId("product-actions")).toHaveTextContent(
      "in-stock | stock:10",
    );
  });

  it("renders ProductTrust", () => {
    renderPage();
    expect(screen.getByTestId("product-trust")).toBeInTheDocument();
  });

  it("renders ProductTabs with product", () => {
    renderPage();
    expect(screen.getByTestId("product-tabs")).toHaveTextContent("HBP-001");
  });

  it("renders RelatedProducts with relatedProducts", () => {
    renderPage();
    expect(screen.getByTestId("related-products")).toHaveTextContent(
      "1 related",
    );
  });

  // ── Breadcrumb ─────────────────────────────────────────────────────────────

  it("renders Home breadcrumb link", () => {
    renderPage();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  it("renders middle breadcrumb as link", () => {
    renderPage();
    expect(
      screen.getByRole("link", { name: "Brake System" }),
    ).toHaveAttribute("href", "/product?category=brakes");
  });

 it("renders last breadcrumb as plain text not a link", () => {
  renderPage();

  // Get the breadcrumb nav container
  const breadcrumbNav = screen.getByRole("navigation");

  // "Honda Brake Pad" inside nav must be a span, not a link
  const breadcrumbSpan = breadcrumbNav.querySelector(
    "span.text-gray-800",
  );

  expect(breadcrumbSpan).toBeInTheDocument();
  expect(breadcrumbSpan).toHaveTextContent("Honda Brake Pad");

  // Confirm it is NOT wrapped in an anchor tag
  expect(breadcrumbSpan.closest("a")).toBeNull();
});

  it("renders breadcrumb separators between items", () => {
    renderPage();

    // Separator › appears between each breadcrumb item
    const separators = screen.getAllByText("›");
    expect(separators.length).toBeGreaterThan(0);
  });

  // ── Out of stock product ───────────────────────────────────────────────────

  it("passes isInStock false to ProductActions", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      product:  { name: "Brake Pad", sku: "BP-001" },
      isInStock: false,
      stock:     0,
    });
    renderPage();

    expect(screen.getByTestId("product-actions")).toHaveTextContent(
      "out-of-stock | stock:0",
    );
  });

  // ── Empty related products ─────────────────────────────────────────────────

  it("passes empty array to RelatedProducts when no related", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      product:         { name: "Brake Pad", sku: "BP-001" },
      relatedProducts: [],
    });
    renderPage();

    expect(screen.getByTestId("related-products")).toHaveTextContent(
      "0 related",
    );
  });

  // ── Empty images ───────────────────────────────────────────────────────────

  it("passes empty images array to ProductGallery when no images", () => {
    useProductDetail.mockReturnValue({
      ...mockHookState,
      product: { name: "Brake Pad", sku: "BP-001" },
      images:  [],
    });
    renderPage();

    expect(screen.getByTestId("gallery")).toHaveTextContent("0 images");
  });
});