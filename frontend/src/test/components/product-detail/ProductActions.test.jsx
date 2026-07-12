// src/test/components/product-detail/ProductActions.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProductActions from "../../../components/product-detail/ProductActions";

// ─── Helper ───────────────────────────────────────────────────────────────────

function renderActions(props = {}) {
  const defaults = { isInStock: true, stock: 10 };
  return render(<ProductActions {...defaults} {...props} />);
}

beforeEach(() => vi.clearAllMocks());

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductActions", () => {

  // ── Quantity selector — only when in stock ─────────────────────────────────

  it("shows quantity selector when isInStock is true", () => {
    renderActions({ isInStock: true, stock: 10 });
    expect(screen.getByText("Quantity:")).toBeInTheDocument();
  });

  it("hides quantity selector when isInStock is false", () => {
    renderActions({ isInStock: false, stock: 0 });
    expect(screen.queryByText("Quantity:")).not.toBeInTheDocument();
  });

  it("shows initial quantity of 1", () => {
    renderActions();
    expect(screen.getByText("1")).toBeInTheDocument();
  });

  // ── Increment ──────────────────────────────────────────────────────────────

  it("increments quantity when Plus is clicked", () => {
    renderActions({ stock: 10 });

    // Plus button — second button (Minus, qty display, Plus)
    const buttons = screen.getAllByRole("button");
    // Plus is last among the qty buttons
    const plusBtn = buttons.find((b) =>
      b.querySelector("svg") && buttons.indexOf(b) > 0
        && buttons.indexOf(b) < buttons.length - 2
    );

    // Simpler: get all buttons, Plus is index 1 in qty row
    // Qty row buttons: [Minus(0), Plus(1)] then action buttons
    fireEvent.click(buttons[1]); // Plus

    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("does not increment beyond stock limit", () => {
    renderActions({ stock: 3 });

    const buttons = screen.getAllByRole("button");
    // Click Plus 5 times — should cap at 3
    fireEvent.click(buttons[1]);
    fireEvent.click(buttons[1]);
    fireEvent.click(buttons[1]);
    fireEvent.click(buttons[1]);
    fireEvent.click(buttons[1]);

    expect(screen.getByText("3")).toBeInTheDocument();
  });

  // ── Decrement ──────────────────────────────────────────────────────────────

  it("decrements quantity when Minus is clicked", () => {
    renderActions({ stock: 10 });

    const buttons = screen.getAllByRole("button");
    // First increment
    fireEvent.click(buttons[1]); // Plus → qty = 2
    // Then decrement
    fireEvent.click(buttons[0]); // Minus → qty = 1

    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("does not decrement below 1", () => {
    renderActions({ stock: 10 });

    const buttons = screen.getAllByRole("button");
    // qty starts at 1 — click Minus multiple times
    fireEvent.click(buttons[0]);
    fireEvent.click(buttons[0]);
    fireEvent.click(buttons[0]);

    expect(screen.getByText("1")).toBeInTheDocument();
  });

  // ── Add to Cart button ─────────────────────────────────────────────────────

  it("renders ADD TO CART when isInStock is true", () => {
    renderActions({ isInStock: true });
    expect(
      screen.getByRole("button", { name: /add to cart/i }),
    ).toBeInTheDocument();
  });

  it("renders OUT OF STOCK when isInStock is false", () => {
    renderActions({ isInStock: false });
    expect(
      screen.getByRole("button", { name: /out of stock/i }),
    ).toBeInTheDocument();
  });

  it("disables ADD TO CART button when isInStock is false", () => {
    renderActions({ isInStock: false });
    expect(
      screen.getByRole("button", { name: /out of stock/i }),
    ).toBeDisabled();
  });

  it("enables ADD TO CART button when isInStock is true", () => {
    renderActions({ isInStock: true });
    expect(
      screen.getByRole("button", { name: /add to cart/i }),
    ).not.toBeDisabled();
  });

  // ── Buy Now button ─────────────────────────────────────────────────────────

  it("renders BUY NOW button", () => {
    renderActions({ isInStock: true });
    expect(
      screen.getByRole("button", { name: /buy now/i }),
    ).toBeInTheDocument();
  });

  it("disables BUY NOW button when isInStock is false", () => {
    renderActions({ isInStock: false });
    expect(
      screen.getByRole("button", { name: /buy now/i }),
    ).toBeDisabled();
  });

  it("enables BUY NOW button when isInStock is true", () => {
    renderActions({ isInStock: true });
    expect(
      screen.getByRole("button", { name: /buy now/i }),
    ).not.toBeDisabled();
  });

  // ── Edge cases ─────────────────────────────────────────────────────────────

  it("caps maxQty at 1 when stock is 0 — no infinite qty", () => {
    renderActions({ isInStock: true, stock: 0 });

    const buttons = screen.getAllByRole("button");
    // Click Plus many times — stock=0 → maxQty=1 → stays at 1
    fireEvent.click(buttons[1]);
    fireEvent.click(buttons[1]);

    expect(screen.getByText("1")).toBeInTheDocument();
  });

  it("defaults isInStock to true when not provided", () => {
    render(<ProductActions stock={5} />);
    expect(
      screen.getByRole("button", { name: /add to cart/i }),
    ).toBeInTheDocument();
  });

  it("defaults stock to 0 when not provided", () => {
    render(<ProductActions isInStock={true} />);
    // stock=0 → maxQty=1 → qty stays at 1 after increment
    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[1]);
    expect(screen.getByText("1")).toBeInTheDocument();
  });
});