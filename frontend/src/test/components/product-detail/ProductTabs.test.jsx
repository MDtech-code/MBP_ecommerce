// src/test/components/product-detail/ProductTabs.test.jsx
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProductTabs from "../../../components/product-detail/ProductTabs";

// ─── Fixture ──────────────────────────────────────────────────────────────────

const makeProduct = (overrides = {}) => ({
  description:      "High quality brake pad for CD70.",
  sku:              "HBP-001",
  category:         { name: "Brake System" },
  brand:            { name: "Honda" },
  is_in_stock:      true,
  compatible_bikes: [],
  ...overrides,
});

function renderTabs(product) {
  return render(<ProductTabs product={makeProduct(product)} />);
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductTabs", () => {

  // ── Tab headers ────────────────────────────────────────────────────────────

  it("renders all 4 tab buttons", () => {
    renderTabs();

    expect(screen.getByRole("button", { name: "DESCRIPTION"    })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "SPECIFICATIONS" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "REVIEWS (0)"    })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "COMPATIBILITY"  })).toBeInTheDocument();
  });

  it("shows DESCRIPTION tab as active by default", () => {
    renderTabs();

    const descBtn = screen.getByRole("button", { name: "DESCRIPTION" });
    expect(descBtn.className).toContain("text-primary");
  });

  // ── Description tab ────────────────────────────────────────────────────────

  it("shows description content by default", () => {
    renderTabs({ description: "High quality brake pad." });
    expect(screen.getByText("High quality brake pad.")).toBeInTheDocument();
  });

  it("shows no description message when description is empty", () => {
    renderTabs({ description: "" });
    expect(
      screen.getByText("No description available."),
    ).toBeInTheDocument();
  });

  it("shows no description message when description is null", () => {
    renderTabs({ description: null });
    expect(
      screen.getByText("No description available."),
    ).toBeInTheDocument();
  });

  // ── Specifications tab ─────────────────────────────────────────────────────

  it("switches to Specifications tab on click", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    // Description content gone
    expect(
      screen.queryByText("High quality brake pad for CD70."),
    ).not.toBeInTheDocument();
  });

  it("shows spec rows after switching to Specifications", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getByText("Part Number")).toBeInTheDocument();
    expect(screen.getByText("Category")).toBeInTheDocument();
    expect(screen.getByText("Brand")).toBeInTheDocument();
    expect(screen.getByText("Material")).toBeInTheDocument();
    expect(screen.getByText("Weight")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  it("shows SKU value in specifications", () => {
    renderTabs({ sku: "HBP-001" });

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getByText("HBP-001")).toBeInTheDocument();
  });

  it("shows category name in specifications", () => {
    renderTabs({ category: { name: "Brake System" } });

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getByText("Brake System")).toBeInTheDocument();
  });

  it("shows brand name in specifications", () => {
    renderTabs({ brand: { name: "Honda" } });

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getByText("Honda")).toBeInTheDocument();
  });

  it("shows Not Provided for Material", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getAllByText("Not Provided")).toHaveLength(2); // Material + Weight
  });

  it("shows In Stock status when is_in_stock is true", () => {
    renderTabs({ is_in_stock: true });

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getByText("In Stock")).toBeInTheDocument();
  });

  it("shows Out of Stock status when is_in_stock is false", () => {
    renderTabs({ is_in_stock: false });

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(screen.getByText("Out of Stock")).toBeInTheDocument();
  });

  it("shows future fields note in specifications", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(
      screen.getByText(/Additional specifications will be available soon/),
    ).toBeInTheDocument();
  });

  // ── Reviews tab ────────────────────────────────────────────────────────────

  it("switches to Reviews tab on click", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "REVIEWS (0)" }));

    expect(screen.getByText("No reviews yet")).toBeInTheDocument();
  });

  it("shows be the first to review message in reviews tab", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "REVIEWS (0)" }));

    expect(
      screen.getByText("Be the first to review this product"),
    ).toBeInTheDocument();
  });

  // ── Compatibility tab ──────────────────────────────────────────────────────

  it("switches to Compatibility tab on click", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "COMPATIBILITY" }));

    // Description content gone
    expect(
      screen.queryByText("High quality brake pad for CD70."),
    ).not.toBeInTheDocument();
  });

  it("shows universal message when no compatible bikes", () => {
    renderTabs({ compatible_bikes: [] });

    fireEvent.click(screen.getByRole("button", { name: "COMPATIBILITY" }));

    expect(
      screen.getByText("Universal — Compatible with all bikes"),
    ).toBeInTheDocument();
  });

  it("shows compatible bike names when bikes exist", () => {
    renderTabs({
      compatible_bikes: [
        { id: 1, display_name: "Honda CD70", year_start: 2020, year_end: 2023 },
        { id: 2, display_name: "Honda CG125", year_start: 2021, year_end: null },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "COMPATIBILITY" }));

    expect(screen.getByText(/Honda CD70/)).toBeInTheDocument();
    expect(screen.getByText(/Honda CG125/)).toBeInTheDocument();
  });

  it("shows year range when year_end is set", () => {
    renderTabs({
      compatible_bikes: [
        { id: 1, display_name: "Honda CD70", year_start: 2020, year_end: 2023 },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "COMPATIBILITY" }));

    expect(screen.getByText(/2020–2023/)).toBeInTheDocument();
  });

  it("shows present when year_end is null", () => {
    renderTabs({
      compatible_bikes: [
        { id: 1, display_name: "Honda CG125", year_start: 2021, year_end: null },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "COMPATIBILITY" }));

    expect(screen.getByText(/2021–present/)).toBeInTheDocument();
  });

  it("shows compatibility intro text when bikes exist", () => {
    renderTabs({
      compatible_bikes: [
        { id: 1, display_name: "Honda CD70", year_start: 2020, year_end: null },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "COMPATIBILITY" }));

    expect(
      screen.getByText(/compatible with the following bike models/),
    ).toBeInTheDocument();
  });

  // ── Tab switching ──────────────────────────────────────────────────────────

  it("switching tabs shows only active tab content", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));
    expect(screen.queryByText("High quality brake pad for CD70.")).not.toBeInTheDocument();
    expect(screen.getByText("Part Number")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "DESCRIPTION" }));
    expect(screen.getByText("High quality brake pad for CD70.")).toBeInTheDocument();
    expect(screen.queryByText("Part Number")).not.toBeInTheDocument();
  });

  it("active tab button has text-primary class", () => {
    renderTabs();

    fireEvent.click(screen.getByRole("button", { name: "SPECIFICATIONS" }));

    expect(
      screen.getByRole("button", { name: "SPECIFICATIONS" }).className,
    ).toContain("text-primary");
    expect(
      screen.getByRole("button", { name: "DESCRIPTION" }).className,
    ).not.toContain("text-primary");
  });

  // ── Null product guard ─────────────────────────────────────────────────────

  it("handles null product gracefully — shows no description", () => {
    render(<ProductTabs product={null} />);

    // Default tab is description — with null product shows fallback
    expect(
      screen.getByText("No description available."),
    ).toBeInTheDocument();
  });
});