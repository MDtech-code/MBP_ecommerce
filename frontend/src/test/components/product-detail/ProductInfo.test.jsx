// src/test/components/product-detail/ProductInfo.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ProductInfo from "../../../components/product-detail/ProductInfo";

// ─── Fixture ──────────────────────────────────────────────────────────────────

const makeProduct = (overrides = {}) => ({
  name:                "Honda Brake Pad",
  sku:                 "HBP-001",
  brand:               { name: "Honda" },
  has_discount:        false,
  discount_percentage: 0,
  current_price:       "450.00",
  price:               "550.00",
  is_in_stock:         true,
  stock:               10,
  compatible_bikes:    [],
  description:         "High quality brake pad",
  ...overrides,
});

function renderInfo(product) {
  return render(<ProductInfo product={product} />);
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductInfo", () => {

  // ── Null guard ─────────────────────────────────────────────────────────────

  it("renders nothing when product is null", () => {
    const { container } = render(<ProductInfo product={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when product is undefined", () => {
    const { container } = render(<ProductInfo />);
    expect(container.firstChild).toBeNull();
  });

  // ── Product name ───────────────────────────────────────────────────────────

  it("renders product name as heading", () => {
    renderInfo(makeProduct());
    expect(
      screen.getByRole("heading", { name: "Honda Brake Pad" }),
    ).toBeInTheDocument();
  });

  // ── Brand + SKU ────────────────────────────────────────────────────────────

  it("renders brand name", () => {
    renderInfo(makeProduct());
    expect(screen.getByText("Honda")).toBeInTheDocument();
  });

  it("renders SKU", () => {
    renderInfo(makeProduct());
    expect(screen.getByText("SKU: HBP-001")).toBeInTheDocument();
  });

  it("does not render brand when brand is null", () => {
    renderInfo(makeProduct({ brand: null }));
    expect(screen.queryByText("Honda")).not.toBeInTheDocument();
  });

  // ── Rating placeholder ─────────────────────────────────────────────────────

  it("renders rating score 4.0", () => {
    renderInfo(makeProduct());
    expect(screen.getByText(/4\.0/)).toBeInTheDocument();
  });

  it("renders No reviews yet when DUMMY_REVIEWS is 0", () => {
    renderInfo(makeProduct());
    expect(screen.getByText(/No reviews yet/)).toBeInTheDocument();
  });

  // ── Price display ──────────────────────────────────────────────────────────

  it("renders current price formatted", () => {
    renderInfo(makeProduct({ current_price: "1500.00" }));
    expect(screen.getByText("Rs. 1,500")).toBeInTheDocument();
  });

  it("does not show original price when has_discount is false", () => {
    renderInfo(makeProduct({ has_discount: false, price: "550.00" }));
    expect(screen.queryByText("Rs. 550")).not.toBeInTheDocument();
  });

  it("shows crossed original price when has_discount is true", () => {
    renderInfo(
      makeProduct({
        has_discount:        true,
        discount_percentage: 18,
        current_price:       "450.00",
        price:               "550.00",
      }),
    );
    expect(screen.getByText("Rs. 550")).toBeInTheDocument();
  });

  it("shows discount badge when has_discount is true", () => {
    renderInfo(
      makeProduct({ has_discount: true, discount_percentage: 18 }),
    );
    expect(screen.getByText("-18%")).toBeInTheDocument();
  });

  it("does not show discount badge when has_discount is false", () => {
    renderInfo(makeProduct({ has_discount: false }));
    expect(screen.queryByText(/-\d+%/)).not.toBeInTheDocument();
  });

  it("renders tax note", () => {
    renderInfo(makeProduct());
    expect(screen.getByText("Inclusive of all taxes")).toBeInTheDocument();
  });

  // ── Availability ───────────────────────────────────────────────────────────

  it("shows In Stock when is_in_stock is true", () => {
    renderInfo(makeProduct({ is_in_stock: true }));
    expect(screen.getByText("In Stock")).toBeInTheDocument();
  });

  it("shows Out of Stock when is_in_stock is false", () => {
    renderInfo(makeProduct({ is_in_stock: false, stock: 0 }));
    expect(screen.getByText("Out of Stock")).toBeInTheDocument();
  });

  it("shows low stock warning when stock <= 5 and in stock", () => {
    renderInfo(makeProduct({ is_in_stock: true, stock: 3 }));
    expect(screen.getByText("(Only 3 left)")).toBeInTheDocument();
  });

  it("does not show low stock warning when stock > 5", () => {
    renderInfo(makeProduct({ is_in_stock: true, stock: 10 }));
    expect(screen.queryByText(/Only \d+ left/)).not.toBeInTheDocument();
  });

  it("does not show low stock warning when stock is exactly 5 boundary", () => {
    renderInfo(makeProduct({ is_in_stock: true, stock: 5 }));
    expect(screen.getByText("(Only 5 left)")).toBeInTheDocument();
  });

  it("does not show low stock warning when stock is 6", () => {
    renderInfo(makeProduct({ is_in_stock: true, stock: 6 }));
    expect(screen.queryByText(/Only \d+ left/)).not.toBeInTheDocument();
  });

  // ── Compatible Bikes ───────────────────────────────────────────────────────

  it("shows compatible bikes when array has items", () => {
    renderInfo(
      makeProduct({
        compatible_bikes: [
          { id: 1, display_name: "Honda CD70 2023" },
          { id: 2, display_name: "Honda CG125 2022" },
        ],
      }),
    );

    expect(screen.getByText("Honda CD70 2023")).toBeInTheDocument();
    expect(screen.getByText("Honda CG125 2022")).toBeInTheDocument();
  });

  it("shows Compatible Bikes heading when bikes exist", () => {
    renderInfo(
      makeProduct({
        compatible_bikes: [{ id: 1, display_name: "Honda CD70" }],
      }),
    );
    expect(screen.getByText("Compatible Bikes:")).toBeInTheDocument();
  });

  it("shows Universal badge when compatible_bikes is empty", () => {
    renderInfo(makeProduct({ compatible_bikes: [] }));
    expect(
      screen.getByText("Universal — Fits All Bikes"),
    ).toBeInTheDocument();
  });

  it("shows Compatibility heading when no bikes", () => {
    renderInfo(makeProduct({ compatible_bikes: [] }));
    expect(screen.getByText("Compatibility:")).toBeInTheDocument();
  });

  it("does not show Universal badge when bikes exist", () => {
    renderInfo(
      makeProduct({
        compatible_bikes: [{ id: 1, display_name: "Honda CD70" }],
      }),
    );
    expect(
      screen.queryByText("Universal — Fits All Bikes"),
    ).not.toBeInTheDocument();
  });
});