// src/test/components/products/ProductSidebar.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ProductSidebar from "../../../components/products/ProductSidebar";

// ─── Mocks ────────────────────────────────────────────────────────────────────

// ✅ CORRECT path — must match what ProductSidebar.jsx imports from
vi.mock("../../../hooks/products/useProductQueries", () => ({
  useCategoriesFlat: vi.fn(),
  useBrands:         vi.fn(),
  useBikeModels:     vi.fn(),
}));

// Import AFTER mock so we get the mocked version
import {
  useCategoriesFlat,
  useBrands,
  useBikeModels,
} from "../../../hooks/products/useProductQueries";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const mockCategories = [
  { id: 1, name: "Brakes",     slug: "brakes",     is_subcategory: false, subcategory_count: 3 },
  { id: 2, name: "Engine",     slug: "engine",     is_subcategory: false, subcategory_count: 0 },
  { id: 3, name: "Brake Pads", slug: "brake-pads", is_subcategory: true,  subcategory_count: 0 },
];

const mockBrands = [
  { id: 1, name: "Honda",  slug: "honda"  },
  { id: 2, name: "Yamaha", slug: "yamaha" },
];

const mockBikeModels = [
  { id: 1, display_name: "Honda CD70 2023"  },
  { id: 2, display_name: "Honda CG125 2022" },
];

// ─── Handlers ─────────────────────────────────────────────────────────────────

const setCategory  = vi.fn();
const setBrand     = vi.fn();
const setBikeModel = vi.fn();
const setMinPrice  = vi.fn();
const setMaxPrice  = vi.fn();
const clearFilters = vi.fn();

const defaultProps = {
  activeFilters: {
    category:  null,
    brand:     null,
    bikeModel: null,
    minPrice:  null,
    maxPrice:  null,
  },
  setCategory,
  setBrand,
  setBikeModel,
  setMinPrice,
  setMaxPrice,
  clearFilters,
};

// ─── Wrapper ──────────────────────────────────────────────────────────────────

function renderSidebar(props = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProductSidebar {...defaultProps} {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ─── Reset ────────────────────────────────────────────────────────────────────

beforeEach(() => {
  vi.clearAllMocks();

  // ✅ Set mock return values in beforeEach — always fresh, always correct
  useCategoriesFlat.mockReturnValue({ data: mockCategories, isLoading: false });
  useBrands.mockReturnValue({ data: mockBrands, isLoading: false });
  useBikeModels.mockReturnValue({ data: mockBikeModels, isLoading: false });
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductSidebar", () => {

  // ── Section headings ───────────────────────────────────────────────────────

  it("renders Categories section heading", () => {
    renderSidebar();
    expect(screen.getByText("Categories")).toBeInTheDocument();
  });

  it("renders Brand section heading", () => {
    renderSidebar();
    expect(screen.getByText("Brand")).toBeInTheDocument();
  });

  it("renders Price Range section heading", () => {
    renderSidebar();
    expect(screen.getByText("Price Range")).toBeInTheDocument();
  });

  it("renders Bike Model section heading", () => {
    renderSidebar();
    expect(screen.getByText("Bike Model")).toBeInTheDocument();
  });

  // ── Loading skeletons ──────────────────────────────────────────────────────

  it("shows category skeleton when catsLoading is true", () => {
    useCategoriesFlat.mockReturnValue({ data: [], isLoading: true });
    renderSidebar();

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("shows bike model skeleton when bikesLoading is true", () => {
    useBikeModels.mockReturnValue({ data: [], isLoading: true });
    renderSidebar();

    const skeletons = document.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  // ── Categories — only root (is_subcategory=false) ─────────────────────────

  it("renders only root categories — filters out subcategories", () => {
    renderSidebar();

    expect(screen.getByText("Brakes")).toBeInTheDocument();
    expect(screen.getByText("Engine")).toBeInTheDocument();
    // "Brake Pads" is a subcategory — must NOT appear
    expect(screen.queryByText("Brake Pads")).not.toBeInTheDocument();
  });

  it("shows subcategory_count when greater than 0", () => {
    renderSidebar();
    expect(screen.getByText("(3)")).toBeInTheDocument();
  });

  it("does not show count of 0 for categories with no subcategories", () => {
    renderSidebar();
    expect(screen.queryByText("(0)")).not.toBeInTheDocument();
  });

  it("checks category checkbox matching activeFilters.category", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, category: "brakes" },
    });

    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes[0]).toBeChecked(); // Brakes is first
  });

  it("does not check category when it does not match activeFilters", () => {
    renderSidebar();

    const checkboxes = screen.getAllByRole("checkbox");
    checkboxes.slice(0, 2).forEach((cb) => {
      expect(cb).not.toBeChecked();
    });
  });

  it("calls setCategory with slug when unchecked category clicked", () => {
    renderSidebar();

    fireEvent.click(screen.getAllByRole("checkbox")[0]); // Brakes

    expect(setCategory).toHaveBeenCalledWith("brakes");
  });

  it("calls setCategory with null when active category clicked (deselect)", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, category: "brakes" },
    });

    fireEvent.click(screen.getAllByRole("checkbox")[0]);

    expect(setCategory).toHaveBeenCalledWith(null);
  });

  // ── Brands ────────────────────────────────────────────────────────────────

  it("renders all brands", () => {
    renderSidebar();

    expect(screen.getByText("Honda")).toBeInTheDocument();
    expect(screen.getByText("Yamaha")).toBeInTheDocument();
  });

  it("checks brand checkbox matching activeFilters.brand", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, brand: "honda" },
    });

    const checkboxes = screen.getAllByRole("checkbox");
    // 2 category checkboxes (Brakes + Engine) then Honda at index 2
    expect(checkboxes[2]).toBeChecked();
  });

  it("calls setBrand with slug on brand click", () => {
    renderSidebar();

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[2]); // Honda

    expect(setBrand).toHaveBeenCalledWith("honda");
  });

  it("calls setBrand with null when active brand clicked (deselect)", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, brand: "honda" },
    });

    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[2]);

    expect(setBrand).toHaveBeenCalledWith(null);
  });

  // ── Price range inputs ─────────────────────────────────────────────────────

  it("renders Min and Max price inputs", () => {
    renderSidebar();

    expect(screen.getByPlaceholderText("Min")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Max")).toBeInTheDocument();
  });

  it("reflects minPrice from activeFilters", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, minPrice: "500" },
    });

    expect(screen.getByPlaceholderText("Min")).toHaveValue(500);
  });

  it("reflects maxPrice from activeFilters", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, maxPrice: "5000" },
    });

    expect(screen.getByPlaceholderText("Max")).toHaveValue(5000);
  });

  it("calls setMinPrice on min input change", () => {
    renderSidebar();

    fireEvent.change(screen.getByPlaceholderText("Min"), {
      target: { value: "500" },
    });

    expect(setMinPrice).toHaveBeenCalledWith("500");
  });

  it("calls setMaxPrice on max input change", () => {
    renderSidebar();

    fireEvent.change(screen.getByPlaceholderText("Max"), {
      target: { value: "5000" },
    });

    expect(setMaxPrice).toHaveBeenCalledWith("5000");
  });

  it("calls setMinPrice with null when input cleared", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, minPrice: "500" },
    });

    fireEvent.change(screen.getByPlaceholderText("Min"), {
      target: { value: "" },
    });

    expect(setMinPrice).toHaveBeenCalledWith(null);
  });

  it("calls setMaxPrice with null when input cleared", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, maxPrice: "5000" },
    });

    fireEvent.change(screen.getByPlaceholderText("Max"), {
      target: { value: "" },
    });

    expect(setMaxPrice).toHaveBeenCalledWith(null);
  });

  // ── Quick price buttons ────────────────────────────────────────────────────

  it("renders all quick price buttons", () => {
    renderSidebar();

    expect(screen.getByRole("button", { name: "Under 500"  })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "500–2000"   })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2000–5000"  })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "5000+"      })).toBeInTheDocument();
  });

  it("sets null min and 500 max for 'Under 500'", () => {
    renderSidebar();
    fireEvent.click(screen.getByRole("button", { name: "Under 500" }));

    expect(setMinPrice).toHaveBeenCalledWith(null);
    expect(setMaxPrice).toHaveBeenCalledWith("500");
  });

  it("sets 500 min and 2000 max for '500–2000'", () => {
    renderSidebar();
    fireEvent.click(screen.getByRole("button", { name: "500–2000" }));

    expect(setMinPrice).toHaveBeenCalledWith("500");
    expect(setMaxPrice).toHaveBeenCalledWith("2000");
  });

  it("sets 2000 min and 5000 max for '2000–5000'", () => {
    renderSidebar();
    fireEvent.click(screen.getByRole("button", { name: "2000–5000" }));

    expect(setMinPrice).toHaveBeenCalledWith("2000");
    expect(setMaxPrice).toHaveBeenCalledWith("5000");
  });

  it("sets 5000 min and null max for '5000+'", () => {
    renderSidebar();
    fireEvent.click(screen.getByRole("button", { name: "5000+" }));

    expect(setMinPrice).toHaveBeenCalledWith("5000");
    expect(setMaxPrice).toHaveBeenCalledWith(null);
  });

  // ── Bike Model dropdown ────────────────────────────────────────────────────

  it("renders All Bike Models default option", () => {
    renderSidebar();

    expect(
      screen.getByRole("option", { name: "All Bike Models" }),
    ).toBeInTheDocument();
  });

  it("renders all bike model options", () => {
    renderSidebar();

    expect(
      screen.getByRole("option", { name: "Honda CD70 2023" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Honda CG125 2022" }),
    ).toBeInTheDocument();
  });

  it("calls setBikeModel with id string on bike model change", () => {
    renderSidebar();

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "1" },
    });

    expect(setBikeModel).toHaveBeenCalledWith("1");
  });

  it("calls setBikeModel with null when default option selected", () => {
    renderSidebar();

    fireEvent.change(screen.getByRole("combobox"), {
      target: { value: "" },
    });

    expect(setBikeModel).toHaveBeenCalledWith(null);
  });

  // ── Clear Filters ──────────────────────────────────────────────────────────

  it("does not show Clear All when no filters active", () => {
    renderSidebar();
    expect(screen.queryByText("Clear All")).not.toBeInTheDocument();
  });

  it("shows Clear All and singular label when 1 filter active", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, category: "brakes" },
    });

    expect(screen.getByText("Clear All")).toBeInTheDocument();
    expect(screen.getByText("1 filter active")).toBeInTheDocument();
  });

  it("shows plural label when 2+ filters active", () => {
    renderSidebar({
      activeFilters: {
        ...defaultProps.activeFilters,
        category: "brakes",
        brand:    "honda",
      },
    });

    expect(screen.getByText("2 filters active")).toBeInTheDocument();
  });

  it("calls clearFilters when Clear All clicked", () => {
    renderSidebar({
      activeFilters: { ...defaultProps.activeFilters, category: "brakes" },
    });

    fireEvent.click(screen.getByText("Clear All"));

    expect(clearFilters).toHaveBeenCalledTimes(1);
  });
});