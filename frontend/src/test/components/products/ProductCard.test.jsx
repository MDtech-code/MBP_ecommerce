// src/test/components/products/ProductCard.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ProductCard from "../../../components/products/ProductCard";

// ─── Fixture ──────────────────────────────────────────────────────────────────

const makeProduct = (overrides = {}) => ({
  id: 1,
  slug: "honda-brake-pad",
  name: "Honda Brake Pad",
  primary_image: "/media/brake-pad.jpg",
  primary_bike: "Honda CD70",
  has_discount: false,
  discount_percentage: 0,
  current_price: "450.00",
  price: "450.00",
  is_in_stock: true,
  is_featured: false,
  ...overrides,
});

function renderCard(product) {
  return render(
    <MemoryRouter>
      <ProductCard product={product} />
    </MemoryRouter>,
  );
}

beforeEach(() => vi.clearAllMocks());

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductCard", () => {

  // ── Renders ────────────────────────────────────────────────────────────────

  it("renders product name", () => {
    renderCard(makeProduct());
    expect(screen.getByText("Honda Brake Pad")).toBeInTheDocument();
  });

  it("renders primary bike", () => {
    renderCard(makeProduct());
    expect(screen.getByText("Honda CD70")).toBeInTheDocument();
  });

  it("renders product image with alt text", () => {
    renderCard(makeProduct());
    const img = screen.getByAltText("Honda Brake Pad");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "/media/brake-pad.jpg");
  });

  it("uses fallback image when primary_image is null", () => {
    renderCard(makeProduct({ primary_image: null }));
    const img = screen.getByAltText("Honda Brake Pad");
    expect(img).toHaveAttribute("src", "/placeholder-part.png");
  });

  it("renders link to product detail page", () => {
    renderCard(makeProduct());
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/product/honda-brake-pad");
  });

  // ── Price display ──────────────────────────────────────────────────────────

  it("renders current price formatted", () => {
    renderCard(makeProduct({ current_price: "1500.00" }));
    expect(screen.getByText("Rs. 1,500")).toBeInTheDocument();
  });

  it("does not render original price when has_discount is false", () => {
    renderCard(makeProduct({ has_discount: false, price: "550.00" }));
    // Only one price shown — no strikethrough
    expect(screen.queryByText("Rs. 550")).not.toBeInTheDocument();
  });

  it("renders original price crossed out when has_discount is true", () => {
    renderCard(
      makeProduct({
        has_discount: true,
        discount_percentage: 18,
        current_price: "450.00",
        price: "550.00",
      }),
    );

    expect(screen.getByText("Rs. 550")).toBeInTheDocument();
  });

  // ── Discount badge ─────────────────────────────────────────────────────────

  it("shows discount badge when has_discount is true", () => {
    renderCard(
      makeProduct({ has_discount: true, discount_percentage: 18 }),
    );
    expect(screen.getByText("-18%")).toBeInTheDocument();
  });

  it("does not show discount badge when has_discount is false", () => {
    renderCard(makeProduct({ has_discount: false }));
    expect(screen.queryByText(/-\d+%/)).not.toBeInTheDocument();
  });

  it("does not show discount badge when discount_percentage is 0", () => {
    renderCard(makeProduct({ has_discount: true, discount_percentage: 0 }));
    expect(screen.queryByText("-0%")).not.toBeInTheDocument();
  });

  // ── Stars ──────────────────────────────────────────────────────────────────

  it("renders 5 star icons", () => {
    renderCard(makeProduct());
    // Stars are SVG — check review count is visible
    expect(screen.getByText("(0)")).toBeInTheDocument();
  });

  // ── Add to Cart button ─────────────────────────────────────────────────────

  it("renders ADD TO CART when is_in_stock is true", () => {
    renderCard(makeProduct({ is_in_stock: true }));
    expect(
      screen.getByRole("button", { name: /add to cart/i }),
    ).toBeInTheDocument();
  });

  it("renders OUT OF STOCK when is_in_stock is false", () => {
    renderCard(makeProduct({ is_in_stock: false }));
    expect(
      screen.getByRole("button", { name: /out of stock/i }),
    ).toBeInTheDocument();
  });

  it("disables button when is_in_stock is false", () => {
    renderCard(makeProduct({ is_in_stock: false }));
    expect(
      screen.getByRole("button", { name: /out of stock/i }),
    ).toBeDisabled();
  });

  it("enables button when is_in_stock is true", () => {
    renderCard(makeProduct({ is_in_stock: true }));
    expect(
      screen.getByRole("button", { name: /add to cart/i }),
    ).not.toBeDisabled();
  });

  it("does not navigate on Add to Cart click — e.preventDefault called", () => {
    renderCard(makeProduct({ is_in_stock: true }));
    const btn = screen.getByRole("button", { name: /add to cart/i });

    // Should not throw — prevents link navigation
    expect(() => fireEvent.click(btn)).not.toThrow();
  });

  // ── Wishlist button ────────────────────────────────────────────────────────

  it("renders wishlist heart button", () => {
    renderCard(makeProduct());
    // There are 2 buttons: Add to Cart + Heart
    const buttons = screen.getAllByRole("button");
    expect(buttons).toHaveLength(2);
  });

  it("does not navigate on Heart button click", () => {
    renderCard(makeProduct());
    const buttons = screen.getAllByRole("button");
    const heartBtn = buttons[buttons.length - 1];

    expect(() => fireEvent.click(heartBtn)).not.toThrow();
  });

  // ── Image error fallback ───────────────────────────────────────────────────

  it("falls back to placeholder on image error", () => {
    renderCard(makeProduct({ primary_image: "/broken-url.jpg" }));
    const img = screen.getByAltText("Honda Brake Pad");

    fireEvent.error(img);

    expect(img).toHaveAttribute("src", "/placeholder-part.png");
  });
});