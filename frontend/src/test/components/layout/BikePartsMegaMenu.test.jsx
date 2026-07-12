// src/test/components/layout/BikePartsMegaMenu.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import BikePartsMegaMenu from "../../../components/layout/menu/BikePartsMegaMenu";

// ─── Mocks ────────────────────────────────────────────────────────────────────

let mockCategoriesData = [];
let mockIsLoading = false;

vi.mock("../../../hooks/products/useProductQueries", () => ({
  useCategoriesTree: vi.fn(() => ({
    data: mockCategoriesData,
    isLoading: mockIsLoading,
  })),
}));

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const categoryTree = [
  {
    id: 1,
    name: "Engine Parts",
    slug: "engine-parts",
    children: [
      {
        id: 3,
        name: "Pistons",
        slug: "pistons",
        children: [
          { id: 5, name: "Piston Rings", slug: "piston-rings", children: [] },
        ],
      },
      { id: 4, name: "Camshaft", slug: "camshaft", children: [] },
    ],
  },
  {
    id: 2,
    name: "Brake System",
    slug: "brake-system",
    children: [
      { id: 6, name: "Brake Pads", slug: "brake-pads", children: [] },
    ],
  },
];

const onClose = vi.fn();

function renderMenu(props = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BikePartsMegaMenu onClose={onClose} {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockCategoriesData = categoryTree;
  mockIsLoading = false;
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("BikePartsMegaMenu", () => {

  // ── Loading state ──────────────────────────────────────────────────────────

  it("shows loading spinner when isLoading is true", () => {
    mockIsLoading = true;
    mockCategoriesData = [];
    renderMenu();

    expect(document.querySelector(".loading")).toBeInTheDocument();
  });

  it("does not show category panels while loading", () => {
    mockIsLoading = true;
    mockCategoriesData = [];
    renderMenu();

    expect(screen.queryByText("Engine Parts")).not.toBeInTheDocument();
  });

  // ── Panel 1 — root categories ──────────────────────────────────────────────

  it("renders all root categories in panel 1", () => {
    renderMenu();

    expect(screen.getByText("Engine Parts")).toBeInTheDocument();
    expect(screen.getByText("Brake System")).toBeInTheDocument();
  });

  it("shows ChevronRight next to categories with children", () => {
    renderMenu();
    // SVG icons inside buttons — check that button contains children indicator
    const engineBtn = screen.getByRole("button", { name: /Engine Parts/ });
    expect(engineBtn).toBeInTheDocument();
  });

  // ── Panel 2 — subcategories on hover ──────────────────────────────────────

  it("shows first root's children in panel 2 by default", () => {
    renderMenu();

    // effectiveRoot defaults to first → Engine Parts
    // Its children: Pistons, Camshaft
    expect(screen.getByText("Pistons")).toBeInTheDocument();
    expect(screen.getByText("Camshaft")).toBeInTheDocument();
  });

  it("shows hovered root's children in panel 2", () => {
    renderMenu();

    fireEvent.mouseEnter(screen.getByRole("button", { name: /Brake System/ }));

    expect(screen.getByText("Brake Pads")).toBeInTheDocument();
    expect(screen.queryByText("Pistons")).not.toBeInTheDocument();
  });

  it("shows No subcategories when root has no children", () => {
    mockCategoriesData = [
      { id: 1, name: "Accessories", slug: "accessories", children: [] },
    ];
    renderMenu();

    expect(screen.getByText("No subcategories")).toBeInTheDocument();
  });

  // ── Panel 3 — sub-subcategories ───────────────────────────────────────────

  it("shows sub-subcategories for first sub by default", () => {
    renderMenu();

    // Default: Engine Parts → Pistons → Piston Rings
    expect(screen.getByText("Piston Rings")).toBeInTheDocument();
  });

  it("shows Browse link when leaf subcategory is hovered", () => {
    renderMenu();

    // Hover Camshaft — it has no children → leaf
    fireEvent.mouseEnter(screen.getByRole("button", { name: /Camshaft/ }));

    expect(screen.getByText(/Browse Camshaft/)).toBeInTheDocument();
  });

  // ── Navigation links ───────────────────────────────────────────────────────

  it("renders View All Categories link", () => {
    renderMenu();

    expect(
      screen.getByRole("link", { name: /View All Categories/ }),
    ).toHaveAttribute("href", "/product");
  });

  it("sub-subcategory link navigates to correct category slug", () => {
    renderMenu();

    const link = screen.getByRole("link", { name: /Piston Rings/ });
    expect(link).toHaveAttribute("href", "/product?category=piston-rings");
  });

  it("CTA Select Bike link navigates to /product", () => {
    renderMenu();

    const ctaLinks = screen.getAllByRole("link", { name: /Select Bike/ });
    expect(ctaLinks[0]).toHaveAttribute("href", "/product");
  });

  // ── onClose ────────────────────────────────────────────────────────────────

  it("calls onClose when View All Categories is clicked", () => {
    renderMenu();

    fireEvent.click(screen.getByRole("link", { name: /View All Categories/ }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose on mouse leave", () => {
    renderMenu();

    const menu = screen.getByText("Engine Parts").closest(".absolute");
    fireEvent.mouseLeave(menu);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // ── Footer ─────────────────────────────────────────────────────────────────

  it("shows total root categories count in footer", () => {
    renderMenu();

    expect(screen.getByText("2 Categories")).toBeInTheDocument();
  });

  it("shows total subcategories count in footer", () => {
    renderMenu();

    // Engine: 2 subs + Brake: 1 sub = 3
    expect(screen.getByText("3 Sub Categories")).toBeInTheDocument();
  });
});