// src/test/pages/products/ProductListing.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ProductListing from "../../../pages/products/ProductListing";

// ─── Mocks — all child components ────────────────────────────────────────────

// ✅ CORRECT — relative to ProductListing.jsx source location
vi.mock("../../../components/layout/Header", () => ({
  default: () => <div data-testid="header" />,
}));

vi.mock("../../../components/products/ProductSidebar", () => ({
  default: (props) => (
    <div data-testid="sidebar">
      <button onClick={props.clearFilters}>Clear</button>
    </div>
  ),
}));

vi.mock("../../../components/products/ProductGrid", () => ({
  default: ({ products, isLoading }) => (
    <div data-testid="product-grid">
      {isLoading ? "loading" : `${products.length} products`}
    </div>
  ),
}));

vi.mock("../../../components/products/ProductToolbar", () => ({
  default: ({ meta, onSort }) => (
    <div data-testid="toolbar">
      <span>{meta?.total ?? 0} total</span>
      <button onClick={() => onSort("price_asc")}>Sort</button>
    </div>
  ),
}));

vi.mock("../../../components/common/Pagination", () => ({
  default: ({ currentPage, totalPages, onPageChange }) => (
    <div data-testid="pagination">
      <button onClick={() => onPageChange(currentPage + 1)}>Next</button>
      <span>Page {currentPage} of {totalPages}</span>
    </div>
  ),
}));
// ─── Mock useProductList ───────────────────────────────────────────────────────

const setCategory  = vi.fn();
const setBrand     = vi.fn();
const setBikeModel = vi.fn();
const setMinPrice  = vi.fn();
const setMaxPrice  = vi.fn();
const setSort      = vi.fn();
const setPage      = vi.fn();
const clearFilters = vi.fn();

let mockHookState = {
  products: [{ id: 1, name: "Brake Pad" }],
  meta: {
    page: 1,
    total_pages: 3,
    total: 36,
    has_next: true,
    has_previous: false,
  },
  isLoading: false,
  isFetching: false,
  isError: false,
  errorMessage: null,
  activeFilters: {
    category: null,
    brand: null,
    bikeModel: null,
    minPrice: null,
    maxPrice: null,
    sort: "newest",
    page: 1,
  },
  setCategory,
  setBrand,
  setBikeModel,
  setMinPrice,
  setMaxPrice,
  setSort,
  setPage,
  clearFilters,
};

vi.mock("../../../hooks/products/useProductList", () => ({
  useProductList: () => mockHookState,
}));

// ─── Helper ───────────────────────────────────────────────────────────────────

function renderPage(url = "/product") {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <ProductListing />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockHookState = {
    products: [{ id: 1, name: "Brake Pad" }],
    meta: {
      page: 1,
      total_pages: 3,
      total: 36,
      has_next: true,
      has_previous: false,
    },
    isLoading: false,
    isFetching: false,
    isError: false,
    errorMessage: null,
    activeFilters: {
      category: null,
      brand: null,
      bikeModel: null,
      minPrice: null,
      maxPrice: null,
      sort: "newest",
      page: 1,
    },
    setCategory,
    setBrand,
    setBikeModel,
    setMinPrice,
    setMaxPrice,
    setSort,
    setPage,
    clearFilters,
  };
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductListing Page", () => {

  // ── Renders ────────────────────────────────────────────────────────────────

  it("renders header", () => {
    renderPage();
    expect(screen.getByTestId("header")).toBeInTheDocument();
  });

  it("renders sidebar", () => {
    renderPage();
    expect(screen.getByTestId("sidebar")).toBeInTheDocument();
  });

  it("renders product grid", () => {
    renderPage();
    expect(screen.getByTestId("product-grid")).toBeInTheDocument();
  });

  it("renders toolbar", () => {
    renderPage();
    expect(screen.getByTestId("toolbar")).toBeInTheDocument();
  });

  it("renders pagination", () => {
    renderPage();
    expect(screen.getByTestId("pagination")).toBeInTheDocument();
  });

  // ── Breadcrumb ─────────────────────────────────────────────────────────────

  it("shows All Products in breadcrumb when no category filter", () => {
    renderPage();
    expect(screen.getByText("All Products")).toBeInTheDocument();
  });

  it("shows formatted category name in breadcrumb", () => {
    mockHookState.activeFilters.category = "brake-system";
    renderPage();

    expect(screen.getByText("Brake System")).toBeInTheDocument();
  });

  it("renders Home breadcrumb link", () => {
    renderPage();
    expect(screen.getByRole("link", { name: "Home" })).toHaveAttribute(
      "href",
      "/",
    );
  });

  // ── Error state ────────────────────────────────────────────────────────────

  it("shows error banner when isError is true", () => {
    mockHookState.isError = true;
    mockHookState.errorMessage = "Failed to load products.";
    renderPage();

    expect(
      screen.getByText("Failed to load products."),
    ).toBeInTheDocument();
  });

  it("shows fallback error message when errorMessage is null", () => {
    mockHookState.isError = true;
    mockHookState.errorMessage = null;
    renderPage();

    expect(
      screen.getByText("Failed to load products. Please try again."),
    ).toBeInTheDocument();
  });

  it("does not show error banner when isError is false", () => {
    renderPage();
    expect(
      screen.queryByText(/Failed to load/),
    ).not.toBeInTheDocument();
  });

  // ── Loading opacity ────────────────────────────────────────────────────────

  it("applies opacity class to grid when isFetching and not isLoading", () => {
    mockHookState.isFetching = true;
    mockHookState.isLoading = false;
    renderPage();

    // The wrapper div around ProductGrid gets opacity-60
    const gridWrapper = screen.getByTestId("product-grid").parentElement;
    expect(gridWrapper.className).toContain("opacity-60");
  });

  it("does not apply opacity when not fetching", () => {
    mockHookState.isFetching = false;
    renderPage();

    const gridWrapper = screen.getByTestId("product-grid").parentElement;
    expect(gridWrapper.className).not.toContain("opacity-60");
  });

  it("does not apply opacity when isLoading is true (skeleton shown instead)", () => {
    mockHookState.isLoading = true;
    mockHookState.isFetching = true;
    renderPage();

    const gridWrapper = screen.getByTestId("product-grid").parentElement;
    expect(gridWrapper.className).not.toContain("opacity-60");
  });

  // ── Passes correct props ───────────────────────────────────────────────────

  it("passes products count to grid", () => {
    mockHookState.products = [
      { id: 1 }, { id: 2 }, { id: 3 },
    ];
    renderPage();

    expect(screen.getByTestId("product-grid")).toHaveTextContent("3 products");
  });

  it("passes total to toolbar", () => {
    mockHookState.meta.total = 99;
    renderPage();

    expect(screen.getByTestId("toolbar")).toHaveTextContent("99 total");
  });

  it("passes pagination props — page and totalPages", () => {
    mockHookState.meta.page = 2;
    mockHookState.meta.total_pages = 5;
    renderPage();

    expect(screen.getByTestId("pagination")).toHaveTextContent(
      "Page 2 of 5",
    );
  });
});