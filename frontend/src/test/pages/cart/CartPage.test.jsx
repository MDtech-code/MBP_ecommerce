// src/test/pages/cart/CartPage.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import CartPage from "../../../pages/cart/CartPage";

/**
 * CartPage is a thin orchestration layer.
 * We mock useCart and useProducts — test only what CartPage itself does:
 *   - Which child components render in which states
 *   - Loading skeleton shows when isLoading=true
 *   - Error state shows when isError=true
 *   - Empty state shows when isEmpty=true
 *   - Cart content shows when isEmpty=false
 *   - Mutation error banner shows when mutationErrorMessage is set
 *   - YouMayAlsoLike shows only when suggestedProducts exist
 *
 * We do NOT test CartList / CartSummary internals here —
 * those have their own test files.
 */

// ─── Mocks ────────────────────────────────────────────────────────────────────

const mockUseCart = vi.fn();
const mockUseProducts = vi.fn();

vi.mock("../../../hooks/cart/useCart", () => ({
  useCart: () => mockUseCart(),
}));

vi.mock("../../../hooks/products/useProductQueries", () => ({
  useProducts: () => mockUseProducts(),
}));

// Mock heavy child components — CartPage layout is what we test here
vi.mock("../../../components/layout/Header", () => ({
  default: () => <div data-testid="header">Header</div>,
}));

vi.mock("../../../components/cart/CartList", () => ({
  default: ({ items }) => (
    <div data-testid="cart-list">CartList ({items.length} items)</div>
  ),
}));

vi.mock("../../../components/cart/CartSummary", () => ({
  default: ({ totalPrice }) => (
    <div data-testid="cart-summary">CartSummary {totalPrice}</div>
  ),
}));

vi.mock("../../../components/cart/CartTrust", () => ({
  default: () => <div data-testid="cart-trust">CartTrust</div>,
}));

vi.mock("../../../components/cart/YouMayAlsoLike", () => ({
  default: ({ products }) => (
    <div data-testid="you-may-also-like">
      YouMayAlsoLike ({products.length})
    </div>
  ),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const CART_ITEM = {
  id: 1,
  product_name: "Oil Filter",
  product_slug: "oil-filter",
  product_price: "250.00",
  product_image: null,
  is_in_stock: true,
  quantity: 2,
  subtotal: "500.00",
};

const SUGGESTED_PRODUCT = {
  id: 10,
  slug: "brake-pad",
  name: "Brake Pad",
  primary_image: null,
  primary_bike: "Honda CD70",
  has_discount: false,
  discount_percentage: 0,
  current_price: "400.00",
  price: "400.00",
};

// Default useCart return — healthy non-empty cart
const defaultCart = () => ({
  items: [CART_ITEM],
  totalItems: 2,
  totalPrice: "500.00",
  isEmpty: false,
  isLoading: false,
  isError: false,
  isMutating: false,
  errorMessage: null,
  mutationErrorMessage: null,
  handleIncrease: vi.fn(),
  handleDecrease: vi.fn(),
  handleRemove: vi.fn(),
  handleClearCart: vi.fn(),
});

// Default useProducts return — no suggested products
const defaultProducts = () => ({
  data: { products: [] },
});

function renderPage() {
  return render(
    <MemoryRouter>
      <CartPage />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseProducts.mockReturnValue(defaultProducts());
});

// ─── Loading state ────────────────────────────────────────────────────────────

describe("CartPage — loading state", () => {
  beforeEach(() => {
    mockUseCart.mockReturnValue({ ...defaultCart(), isLoading: true });
  });

  it("renders Header during loading", () => {
    renderPage();
    expect(screen.getByTestId("header")).toBeInTheDocument();
  });

  it("does not render CartList during loading", () => {
    renderPage();
    expect(screen.queryByTestId("cart-list")).not.toBeInTheDocument();
  });

  it("does not render CartSummary during loading", () => {
    renderPage();
    expect(screen.queryByTestId("cart-summary")).not.toBeInTheDocument();
  });
});

// ─── Error state ──────────────────────────────────────────────────────────────

describe("CartPage — error state", () => {
  beforeEach(() => {
    mockUseCart.mockReturnValue({
      ...defaultCart(),
      isError: true,
      errorMessage: "Failed to load cart",
    });
  });

  it("renders Header during error", () => {
    renderPage();
    expect(screen.getByTestId("header")).toBeInTheDocument();
  });

  it("renders Failed to load cart heading", () => {
    renderPage();
    const heading = screen.getByText("Failed to load cart", {
      selector: "p.font-bold",
    });
    expect(heading).toBeInTheDocument();
  });

  it("renders errorMessage from useCart in description paragraph", () => {
    renderPage();
    const description = screen.getByText("Failed to load cart", {
      selector: "p.text-sm",
    });
    expect(description).toBeInTheDocument();
  });

  it("renders Try Again button", () => {
    renderPage();
    expect(
      screen.getByRole("button", { name: /try again/i }),
    ).toBeInTheDocument();
  });

  it("does not render CartList during error", () => {
    renderPage();
    expect(screen.queryByTestId("cart-list")).not.toBeInTheDocument();
  });
});


// ─── Empty cart state ─────────────────────────────────────────────────────────

describe("CartPage — empty cart state", () => {
  beforeEach(() => {
    mockUseCart.mockReturnValue({
      ...defaultCart(),
      items: [],
      totalItems: 0,
      totalPrice: "0.00",
      isEmpty: true,
    });
  });

  it("renders empty cart emoji", () => {
    renderPage();
    expect(screen.getByText("🛒")).toBeInTheDocument();
  });

  it("renders Your cart is empty message", () => {
    renderPage();
    expect(screen.getByText("Your cart is empty")).toBeInTheDocument();
  });

  it("renders Browse Products link", () => {
    renderPage();
    const link = screen.getByRole("link", { name: /browse products/i });
    expect(link).toBeInTheDocument();
    expect(link.getAttribute("href")).toBe("/product");
  });

  it("does not render CartList when empty", () => {
    renderPage();
    expect(screen.queryByTestId("cart-list")).not.toBeInTheDocument();
  });

  it("does not render CartSummary when empty", () => {
    renderPage();
    expect(screen.queryByTestId("cart-summary")).not.toBeInTheDocument();
  });
});

// ─── Populated cart state ─────────────────────────────────────────────────────


describe("CartPage — populated cart state", () => {
  beforeEach(() => {
    mockUseCart.mockReturnValue(defaultCart());
  });

  it("renders page title h1 with item count", () => {
    renderPage();
    const h1 = screen.getByRole("heading", { level: 1 });
    expect(h1).toHaveTextContent("Your Cart");
    expect(h1).toHaveTextContent("2 Items");
  });

  it("renders CartList", () => {
    renderPage();
    expect(screen.getByTestId("cart-list")).toBeInTheDocument();
  });

  it("renders CartSummary", () => {
    renderPage();
    expect(screen.getByTestId("cart-summary")).toBeInTheDocument();
  });

  it("renders CartTrust badges", () => {
    renderPage();
    expect(screen.getByTestId("cart-trust")).toBeInTheDocument();
  });

  it("renders Home breadcrumb link", () => {
    renderPage();
    const homeLink = screen.getByRole("link", { name: /home/i });
    expect(homeLink.getAttribute("href")).toBe("/");
  });

  it("renders Your Cart breadcrumb text in nav", () => {
    renderPage();
    const nav = screen.getByRole("navigation");
    expect(nav).toHaveTextContent("Your Cart");
  });
});
// ─── Mutation error banner ────────────────────────────────────────────────────

describe("CartPage — mutation error banner", () => {
  it("renders mutation error banner when mutationErrorMessage is set", () => {
    mockUseCart.mockReturnValue({
      ...defaultCart(),
      mutationErrorMessage: "Failed to update item",
    });

    renderPage();

    expect(screen.getByText("Failed to update item")).toBeInTheDocument();
  });

  it("does not render mutation error banner when mutationErrorMessage is null", () => {
    mockUseCart.mockReturnValue({
      ...defaultCart(),
      mutationErrorMessage: null,
    });

    renderPage();

    expect(
      screen.queryByText("Failed to update item"),
    ).not.toBeInTheDocument();
  });
});

// ─── YouMayAlsoLike ───────────────────────────────────────────────────────────

describe("CartPage — YouMayAlsoLike", () => {
  it("renders YouMayAlsoLike when suggested products exist", () => {
    mockUseCart.mockReturnValue(defaultCart());
    mockUseProducts.mockReturnValue({
      data: { products: [SUGGESTED_PRODUCT] },
    });

    renderPage();

    expect(screen.getByTestId("you-may-also-like")).toBeInTheDocument();
  });

  it("does not render YouMayAlsoLike when suggested products is empty", () => {
    mockUseCart.mockReturnValue(defaultCart());
    mockUseProducts.mockReturnValue({ data: { products: [] } });

    renderPage();

    expect(
      screen.queryByTestId("you-may-also-like"),
    ).not.toBeInTheDocument();
  });

  it("does not render YouMayAlsoLike when useProducts returns undefined data", () => {
    mockUseCart.mockReturnValue(defaultCart());
    mockUseProducts.mockReturnValue({ data: undefined });

    renderPage();

    expect(
      screen.queryByTestId("you-may-also-like"),
    ).not.toBeInTheDocument();
  });
});
