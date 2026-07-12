// src/tests/components/cart/CartList.test.jsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import CartList from "../../../components/cart/CartList";

/**
 * CartList is a pure component that delegates to CartItem.
 * Tests verify:
 *   - Column headers render
 *   - Items are rendered (one CartItem per item in array)
 *   - Continue Shopping link points to /product
 *   - Clear Cart button calls onClearCart
 *   - Clear Cart disabled when isMutating or items empty
 */

const ITEMS = [
  {
    id: 1,
    product_name: "Oil Filter",
    product_slug: "oil-filter",
    product_price: "250.00",
    product_image: null,
    is_in_stock: true,
    quantity: 2,
    subtotal: "500.00",
  },
  {
    id: 2,
    product_name: "Brake Pad",
    product_slug: "brake-pad",
    product_price: "400.00",
    product_image: null,
    is_in_stock: true,
    quantity: 1,
    subtotal: "400.00",
  },
];

function renderList(overrides = {}) {
  const props = {
    items: ITEMS,
    isMutating: false,
    onIncrease: vi.fn(),
    onDecrease: vi.fn(),
    onRemove: vi.fn(),
    onClearCart: vi.fn(),
    ...overrides,
  };

  render(
    <MemoryRouter>
      <CartList {...props} />
    </MemoryRouter>
  );

  return props;
}

// ─── Headers ──────────────────────────────────────────────────────────────────

describe("CartList — column headers", () => {
  it("renders Product header", () => {
    renderList();
    expect(screen.getByText(/product/i)).toBeInTheDocument();
  });

  it("renders Price header", () => {
    renderList();
    expect(screen.getByText(/price/i)).toBeInTheDocument();
  });

  it("renders Quantity header", () => {
    renderList();
    expect(screen.getByText(/quantity/i)).toBeInTheDocument();
  });

  it("renders Action header", () => {
    renderList();
    expect(screen.getByText(/action/i)).toBeInTheDocument();
  });
});

// ─── Items ────────────────────────────────────────────────────────────────────

describe("CartList — item rendering", () => {
  it("renders all items passed in props", () => {
    renderList();
    expect(screen.getByText("Oil Filter")).toBeInTheDocument();
    expect(screen.getByText("Brake Pad")).toBeInTheDocument();
  });

  it("renders nothing in item area when items array is empty", () => {
    renderList({ items: [] });
    expect(screen.queryByText("Oil Filter")).not.toBeInTheDocument();
  });
});

// ─── Continue Shopping ────────────────────────────────────────────────────────

describe("CartList — Continue Shopping link", () => {
  it("renders link to /product", () => {
    renderList();
    const link = screen.getByRole("link", { name: /continue shopping/i });
    expect(link.getAttribute("href")).toBe("/product");
  });
});

// ─── Clear Cart button ────────────────────────────────────────────────────────

describe("CartList — Clear Cart button", () => {
  it("calls onClearCart when clicked", () => {
    const onClearCart = vi.fn();
    renderList({ onClearCart });

    fireEvent.click(screen.getByRole("button", { name: /clear cart/i }));

    expect(onClearCart).toHaveBeenCalledTimes(1);
  });

  it("is disabled when isMutating is true", () => {
    renderList({ isMutating: true });
    expect(
      screen.getByRole("button", { name: /clear cart/i })
    ).toBeDisabled();
  });

  it("is disabled when items array is empty", () => {
    renderList({ items: [] });
    expect(
      screen.getByRole("button", { name: /clear cart/i })
    ).toBeDisabled();
  });

  it("is enabled when items exist and not mutating", () => {
    renderList();
    expect(
      screen.getByRole("button", { name: /clear cart/i })
    ).not.toBeDisabled();
  });
});