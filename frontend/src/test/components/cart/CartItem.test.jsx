// src/tests/components/cart/CartItem.test.jsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import CartItem from "../../../components/cart/CartItem";

/**
 * CartItem is a pure component — no hooks to mock.
 * All handlers are passed as props.
 * Tests verify rendering + handler calls + disabled states.
 */

const BASE_ITEM = {
  id: 1,
  product_name: "Yamaha Oil Filter",
  product_slug: "yamaha-oil-filter",
  product_price: "250.00",
  product_image: null,
  is_in_stock: true,
  quantity: 2,
  subtotal: "500.00",
};

function renderItem(overrides = {}) {
  const props = {
    item: BASE_ITEM,
    onIncrease: vi.fn(),
    onDecrease: vi.fn(),
    onRemove: vi.fn(),
    isMutating: false,
    ...overrides,
  };

  render(
    <MemoryRouter>
      <CartItem {...props} />
    </MemoryRouter>
  );

  return props;
}

// ─── Rendering ────────────────────────────────────────────────────────────────

describe("CartItem — rendering", () => {
  it("renders product_name", () => {
    renderItem();
    expect(screen.getByText("Yamaha Oil Filter")).toBeInTheDocument();
  });

  it("renders unit price from product_price", () => {
    renderItem();
    // parseFloat("250.00").toLocaleString() → "250" in test env
    expect(screen.getByText(/Rs\. 250/)).toBeInTheDocument();
  });

  it("renders current quantity", () => {
    renderItem();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("renders subtotal from backend subtotal field", () => {
    renderItem();
    expect(screen.getByText(/Rs\. 500/)).toBeInTheDocument();
  });

  it("renders two links to /product/:slug", () => {
    renderItem();
    const links = screen.getAllByRole("link");
    links.forEach((link) => {
      expect(link.getAttribute("href")).toBe("/product/yamaha-oil-filter");
    });
  });

  it("shows Out of Stock label when is_in_stock is false", () => {
    renderItem({ item: { ...BASE_ITEM, is_in_stock: false } });
    expect(screen.getByText("Out of Stock")).toBeInTheDocument();
  });

  it("does not show Out of Stock label when is_in_stock is true", () => {
    renderItem();
    expect(screen.queryByText("Out of Stock")).not.toBeInTheDocument();
  });
});

// ─── Handlers ─────────────────────────────────────────────────────────────────

describe("CartItem — handler calls", () => {
  it("calls onDecrease(id, quantity) when minus button clicked", () => {
    const onDecrease = vi.fn();
    renderItem({ onDecrease });

    // minus is the first button rendered inside the quantity group
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]); // minus

    expect(onDecrease).toHaveBeenCalledWith(1, 2);
  });

  it("calls onIncrease(id, quantity) when plus button clicked", () => {
    const onIncrease = vi.fn();
    renderItem({ onIncrease });

    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[1]); // plus

    expect(onIncrease).toHaveBeenCalledWith(1, 2);
  });

  it("calls onRemove(id) when trash button clicked", () => {
    const onRemove = vi.fn();
    renderItem({ onRemove });

    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[2]); // trash

    expect(onRemove).toHaveBeenCalledWith(1);
  });
});

// ─── Disabled states ──────────────────────────────────────────────────────────

describe("CartItem — disabled states", () => {
  it("disables all three buttons when isMutating is true", () => {
    renderItem({ isMutating: true });

    screen.getAllByRole("button").forEach((btn) => {
      expect(btn).toBeDisabled();
    });
  });

  it("disables plus button when is_in_stock is false", () => {
    renderItem({ item: { ...BASE_ITEM, is_in_stock: false } });

    const buttons = screen.getAllByRole("button");
    expect(buttons[1]).toBeDisabled(); // plus
  });

  it("keeps minus and trash enabled when only is_in_stock is false", () => {
    renderItem({ item: { ...BASE_ITEM, is_in_stock: false } });

    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).not.toBeDisabled(); // minus
    expect(buttons[2]).not.toBeDisabled(); // trash
  });

  it("all buttons enabled when in stock and not mutating", () => {
    renderItem();

    screen.getAllByRole("button").forEach((btn) => {
      expect(btn).not.toBeDisabled();
    });
  });
});