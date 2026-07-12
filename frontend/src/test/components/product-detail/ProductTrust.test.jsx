// src/test/components/product-detail/ProductTrust.test.jsx
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import ProductTrust from "../../../components/product-detail/ProductTrust";

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductTrust", () => {

  it("renders all 4 trust items", () => {
    render(<ProductTrust />);

    expect(screen.getByText("Original Products")).toBeInTheDocument();
    expect(screen.getByText("Cash On Delivery")).toBeInTheDocument();
    expect(screen.getByText("Nationwide Delivery")).toBeInTheDocument();
    expect(screen.getByText("7 Days Returns")).toBeInTheDocument();
  });

  it("renders all 4 subtitles", () => {
    render(<ProductTrust />);

    expect(screen.getByText("100% Genuine")).toBeInTheDocument();
    expect(screen.getByText("Pay when you get")).toBeInTheDocument();
    expect(screen.getByText("Fast & Reliable")).toBeInTheDocument();
    expect(screen.getByText("Hassle free returns")).toBeInTheDocument();
  });

  it("renders exactly 4 trust item groups", () => {
    const { container } = render(<ProductTrust />);

    // Each item has: icon + text + sub in a flex div
    const items = container.querySelectorAll(".flex.items-start");
    expect(items).toHaveLength(4);
  });
});