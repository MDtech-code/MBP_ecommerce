// src/test/components/products/ProductToolbar.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProductToolbar from "../../../components/products/ProductToolbar";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const onSort = vi.fn();

function renderToolbar(props = {}) {
  const defaults = {
    meta: { showing_from: 1, showing_to: 12, total: 36 },
    activeSort: "newest",
    onSort,
  };
  return render(<ProductToolbar {...defaults} {...props} />);
}

beforeEach(() => vi.clearAllMocks());

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductToolbar", () => {

  // ── Result count display ───────────────────────────────────────────────────

  it("shows showing_from, showing_to and total", () => {
    renderToolbar();

    expect(screen.getByText(/1–12/)).toBeInTheDocument();
    expect(screen.getByText(/36 products/)).toBeInTheDocument();
  });

  it("shows No products found when total is 0", () => {
    renderToolbar({
      meta: { showing_from: 0, showing_to: 0, total: 0 },
    });

    expect(screen.getByText("No products found")).toBeInTheDocument();
  });

  it("shows zeros from empty meta", () => {
    renderToolbar({ meta: {} });

    expect(screen.getByText("No products found")).toBeInTheDocument();
  });

  // ── Sort select ────────────────────────────────────────────────────────────

  it("renders sort select with all options", () => {
    renderToolbar();

    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();

    expect(screen.getByRole("option", { name: "Newest First" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Featured" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Price Low to High" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Price High to Low" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Name A–Z" })).toBeInTheDocument();
  });

  it("reflects activeSort as selected option", () => {
    renderToolbar({ activeSort: "price_asc" });

    const select = screen.getByRole("combobox");
    expect(select.value).toBe("price_asc");
  });

  it("defaults to newest when activeSort not provided", () => {
    render(<ProductToolbar meta={{}} />);

    const select = screen.getByRole("combobox");
    expect(select.value).toBe("newest");
  });

  it("calls onSort with selected value on change", () => {
    renderToolbar();

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "price_desc" },
    });

    expect(onSort).toHaveBeenCalledWith("price_desc");
  });

  it("calls onSort with price_asc", () => {
    renderToolbar();

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "price_asc" },
    });

    expect(onSort).toHaveBeenCalledWith("price_asc");
  });

  it("does not throw when onSort is not provided", () => {
    render(
      <ProductToolbar
        meta={{ showing_from: 1, showing_to: 12, total: 36 }}
        activeSort="newest"
      />,
    );

    expect(() => {
      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "featured" },
      });
    }).not.toThrow();
  });

  // ── Sort label ─────────────────────────────────────────────────────────────

  it("renders Sort By label", () => {
    renderToolbar();
    expect(screen.getByText("Sort By:")).toBeInTheDocument();
  });
});