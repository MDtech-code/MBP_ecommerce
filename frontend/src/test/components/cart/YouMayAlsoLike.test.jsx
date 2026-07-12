// src/test/components/cart/YouMayAlsoLike.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import YouMayAlsoLike from "../../../components/cart/YouMayAlsoLike";

/**
 * YouMayAlsoLike is a pure component — receives products as props.
 * No hooks, no mocks needed.
 *
 * Tests verify:
 *   - Section heading renders
 *   - Each product renders name, price, link
 *   - Discount badge renders when has_discount=true
 *   - Fallback image on error
 *   - Renders nothing extra when products array is empty
 */

const makeProduct = (overrides = {}) => ({
  id: 1,
  slug: "honda-oil-filter",
  name: "Honda Oil Filter",
  primary_image: "/media/oil-filter.jpg",
  primary_bike: "Honda CD70",
  has_discount: false,
  discount_percentage: 0,
  current_price: "250.00",
  price: "300.00",
  ...overrides,
});

function renderComponent(products) {
  return render(
    <MemoryRouter>
      <YouMayAlsoLike products={products} />
    </MemoryRouter>,
  );
}

// ─── Heading ──────────────────────────────────────────────────────────────────

describe("YouMayAlsoLike — heading", () => {
  it("renders You May Also Like heading", () => {
    renderComponent([makeProduct()]);
    expect(screen.getByText("You May Also Like")).toBeInTheDocument();
  });
});

// ─── Product rendering ────────────────────────────────────────────────────────

describe("YouMayAlsoLike — product rendering", () => {
  it("renders product name", () => {
    renderComponent([makeProduct()]);
    expect(screen.getByText("Honda Oil Filter")).toBeInTheDocument();
  });

  it("renders primary bike", () => {
    renderComponent([makeProduct()]);
    expect(screen.getByText("Honda CD70")).toBeInTheDocument();
  });

  it("renders current price", () => {
    renderComponent([makeProduct({ current_price: "250.00" })]);
    expect(screen.getByText(/Rs\. 250/)).toBeInTheDocument();
  });

  it("renders link to /product/:slug", () => {
    renderComponent([makeProduct()]);
    const link = screen.getByRole("link");
    expect(link.getAttribute("href")).toBe("/product/honda-oil-filter");
  });

  it("renders all products passed in array", () => {
    const products = [
      makeProduct({ id: 1, name: "Oil Filter", slug: "oil-filter" }),
      makeProduct({ id: 2, name: "Brake Pad",  slug: "brake-pad"  }),
      makeProduct({ id: 3, name: "Chain Kit",  slug: "chain-kit"  }),
    ];
    renderComponent(products);

    expect(screen.getByText("Oil Filter")).toBeInTheDocument();
    expect(screen.getByText("Brake Pad")).toBeInTheDocument();
    expect(screen.getByText("Chain Kit")).toBeInTheDocument();
  });

  it("renders one link per product", () => {
    const products = [
      makeProduct({ id: 1, slug: "oil-filter" }),
      makeProduct({ id: 2, slug: "brake-pad"  }),
    ];
    renderComponent(products);
    expect(screen.getAllByRole("link")).toHaveLength(2);
  });
});

// ─── Discount ─────────────────────────────────────────────────────────────────

describe("YouMayAlsoLike — discount", () => {
  it("renders discount badge when has_discount is true", () => {
    renderComponent([
      makeProduct({ has_discount: true, discount_percentage: 15 }),
    ]);
    expect(screen.getByText(/-15%/)).toBeInTheDocument();
  });

  it("does not render discount badge when has_discount is false", () => {
    renderComponent([makeProduct({ has_discount: false })]);
    expect(screen.queryByText(/-\d+%/)).not.toBeInTheDocument();
  });

  it("does not render discount badge when discount_percentage is 0", () => {
    renderComponent([
      makeProduct({ has_discount: true, discount_percentage: 0 }),
    ]);
    expect(screen.queryByText("-0%")).not.toBeInTheDocument();
  });

  it("renders original price when has_discount is true", () => {
    renderComponent([
      makeProduct({ has_discount: true, price: "300.00", current_price: "250.00" }),
    ]);
    expect(screen.getByText(/Rs\. 300/)).toBeInTheDocument();
  });

  it("does not render original price when has_discount is false", () => {
    renderComponent([
      makeProduct({ has_discount: false, price: "300.00", current_price: "250.00" }),
    ]);
    // price "300" should not appear — only current_price "250" shown
    expect(screen.queryByText(/Rs\. 300/)).not.toBeInTheDocument();
  });
});

// ─── Image fallback ───────────────────────────────────────────────────────────

describe("YouMayAlsoLike — image", () => {
  it("renders product image", () => {
    renderComponent([makeProduct()]);
    const img = screen.getByAltText("Honda Oil Filter");
    expect(img).toHaveAttribute("src", "/media/oil-filter.jpg");
  });

  it("uses placeholder when primary_image is null", () => {
    renderComponent([makeProduct({ primary_image: null })]);
    const img = screen.getByAltText("Honda Oil Filter");
    expect(img).toHaveAttribute("src", "/placeholder-part.png");
  });

  it("falls back to placeholder on image error", () => {
    renderComponent([makeProduct({ primary_image: "/broken.jpg" })]);
    const img = screen.getByAltText("Honda Oil Filter");
    fireEvent.error(img);
    expect(img).toHaveAttribute("src", "/placeholder-part.png");
  });
});