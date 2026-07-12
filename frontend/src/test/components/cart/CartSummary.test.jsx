// src/tests/components/cart/CartSummary.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CartSummary from "../../../components/cart/CartSummary";

/**
 * CartSummary is a pure component.
 * Tests verify:
 *   - Subtotal renders from totalPrice prop
 *   - Total = subtotal + 150 (hardcoded shipping)
 *   - Item count renders in label
 *   - Checkout button disabled states
 */

// ─── Rendering ────────────────────────────────────────────────────────────────

describe("CartSummary — rendering", () => {
  it("renders Order Summary heading", () => {
    render(<CartSummary totalPrice="0.00" totalItems={0} />);
    expect(screen.getByText("Order Summary")).toBeInTheDocument();
  });

  it("renders subtotal from totalPrice prop", () => {
    render(<CartSummary totalPrice="500.00" totalItems={2} />);
    expect(screen.getByText(/Rs\. 500/)).toBeInTheDocument();
  });

  it("renders total = subtotal + 150 shipping fee", () => {
    render(<CartSummary totalPrice="500.00" totalItems={2} />);
    // 500 + 150 = 650
    expect(screen.getByText(/Rs\. 650/)).toBeInTheDocument();
  });

  it("renders item count in subtotal row", () => {
    render(<CartSummary totalPrice="500.00" totalItems={3} />);
    expect(screen.getByText(/3 items/)).toBeInTheDocument();
  });

  it("renders Secure Checkout text", () => {
    render(<CartSummary totalPrice="0.00" totalItems={0} />);
    expect(screen.getByText(/Secure Checkout/i)).toBeInTheDocument();
  });

  it("renders shipping fee of Rs. 150 in shipping row", () => {
  // totalPrice="500.00" → total = 650, so only the shipping row shows "Rs. 150"
  render(<CartSummary totalPrice="500.00" totalItems={2} />);

  const shippingRow = screen.getByText("Shipping").closest("div");
  expect(shippingRow).toHaveTextContent("Rs. 150");
});
});

// ─── Checkout button ──────────────────────────────────────────────────────────

describe("CartSummary — checkout button disabled states", () => {
  it("is disabled when isMutating is true", () => {
    render(
      <CartSummary totalPrice="500.00" totalItems={2} isMutating={true} />
    );
    expect(
      screen.getByRole("button", { name: /checkout/i })
    ).toBeDisabled();
  });

  it("is disabled when totalItems is 0", () => {
    render(<CartSummary totalPrice="0.00" totalItems={0} isMutating={false} />);
    expect(
      screen.getByRole("button", { name: /checkout/i })
    ).toBeDisabled();
  });

  it("is enabled when cart has items and not mutating", () => {
    render(
      <CartSummary totalPrice="500.00" totalItems={2} isMutating={false} />
    );
    expect(
      screen.getByRole("button", { name: /checkout/i })
    ).not.toBeDisabled();
  });
});
