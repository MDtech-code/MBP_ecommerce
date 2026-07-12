// src/test/components/products/ProductGrid.test.jsx
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ProductGrid from "../../../components/products/ProductGrid";

// ─── Mock ProductCard ─────────────────────────────────────────────────────────

vi.mock("../../../components/products/ProductCard", () => ({
  default: ({ product }) => (
    <div data-testid="product-card">{product.name}</div>
  ),
}));

// ─── Helpers ──────────────────────────────────────────────────────────────────

const makeProducts = (count) =>
  Array.from({ length: count }, (_, i) => ({
    id: i + 1,
    name: `Product ${i + 1}`,
    slug: `product-${i + 1}`,
  }));

function renderGrid(props = {}) {
  return render(
    <MemoryRouter>
      <ProductGrid {...props} />
    </MemoryRouter>,
  );
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductGrid", () => {

  // ── Loading skeleton ───────────────────────────────────────────────────────

  it("renders 12 skeleton cards when isLoading is true", () => {
    renderGrid({ isLoading: true });

    // Each skeleton has animate-pulse class
    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons).toHaveLength(12);
  });

  it("does not render ProductCard when loading", () => {
    renderGrid({ isLoading: true });
    expect(screen.queryByTestId("product-card")).not.toBeInTheDocument();
  });

  // ── Empty state ────────────────────────────────────────────────────────────

  it("shows no products found when products array is empty", () => {
    renderGrid({ products: [] });

    expect(screen.getByText("No products found")).toBeInTheDocument();
  });

  it("shows helper text in empty state", () => {
    renderGrid({ products: [] });

    expect(
      screen.getByText("Try adjusting your filters or search term"),
    ).toBeInTheDocument();
  });

  it("shows wrench emoji in empty state", () => {
    renderGrid({ products: [] });
    expect(screen.getByText("🔧")).toBeInTheDocument();
  });

  it("does not show empty state when products exist", () => {
    renderGrid({ products: makeProducts(3) });
    expect(screen.queryByText("No products found")).not.toBeInTheDocument();
  });

  // ── Product cards ──────────────────────────────────────────────────────────

  it("renders a ProductCard for each product", () => {
    renderGrid({ products: makeProducts(4) });

    expect(screen.getAllByTestId("product-card")).toHaveLength(4);
  });

  it("passes correct product name to each card", () => {
    renderGrid({ products: makeProducts(3) });

    expect(screen.getByText("Product 1")).toBeInTheDocument();
    expect(screen.getByText("Product 2")).toBeInTheDocument();
    expect(screen.getByText("Product 3")).toBeInTheDocument();
  });

  it("defaults products to empty array when not provided", () => {
    renderGrid();
    expect(screen.getByText("No products found")).toBeInTheDocument();
  });

  it("defaults isLoading to false when not provided", () => {
    renderGrid({ products: makeProducts(2) });
    expect(document.querySelectorAll(".animate-pulse")).toHaveLength(0);
  });
});