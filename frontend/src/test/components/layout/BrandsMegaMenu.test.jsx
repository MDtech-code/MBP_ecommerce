// src/test/components/layout/BrandsMegaMenu.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import BrandsMegaMenu from "../../../components/layout/menu/BrandsMegaMenu";

// ─── Mocks ────────────────────────────────────────────────────────────────────

vi.mock("../../../hooks/products/useProductQueries", () => ({
  useBrands:         vi.fn(),
  useCategoriesTree: vi.fn(),
}));

vi.mock("../../../utils/media", () => ({
  getMediaUrl: vi.fn((path) => `http://localhost${path}`),
}));

import {
  useBrands,
  useCategoriesTree,
} from "../../../hooks/products/useProductQueries";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const makeBrands = (count) =>
  Array.from({ length: count }, (_, i) => ({
    id:   i + 1,
    name: `Brand ${i + 1}`,
    slug: `brand-${i + 1}`,
    // Only odd-index brands have logo → Brand 1,3,5 have logo; Brand 2,4 do not
    logo: i % 2 === 0 ? `/media/brand-${i + 1}.png` : null,
  }));

const makeCategories = () => [
  { id: 1, name: "Engine Parts", slug: "engine-parts", children: [] },
  { id: 2, name: "Brake System", slug: "brake-system", children: [] },
];

const onClose = vi.fn();

function renderMenu(props = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BrandsMegaMenu onClose={onClose} {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useBrands.mockReturnValue({ data: makeBrands(5), isLoading: false });
  useCategoriesTree.mockReturnValue({ data: makeCategories(), isLoading: false });
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("BrandsMegaMenu", () => {

  // ── Loading ────────────────────────────────────────────────────────────────

  it("shows loading spinner when loading", () => {
    useBrands.mockReturnValue({ data: [], isLoading: true });
    useCategoriesTree.mockReturnValue({ data: [], isLoading: true });
    renderMenu();

    expect(document.querySelector(".loading")).toBeInTheDocument();
  });

  // ── Panel 1 — categories ───────────────────────────────────────────────────

  it("renders Shop By Category heading", () => {
    renderMenu();
    expect(screen.getByText("Shop By Category")).toBeInTheDocument();
  });

  it("renders all categories in panel 1", () => {
    renderMenu();

    expect(screen.getByText("Engine Parts")).toBeInTheDocument();
    expect(screen.getByText("Brake System")).toBeInTheDocument();
  });

  it("category links navigate to correct category slug", () => {
    renderMenu();

    // ✅ FIX: Link name is "Engine Parts›" because of <span>›</span> inside
    // Use exact:false to match partial name
    const engineLink = screen.getByRole("link", { name: /Engine Parts/ });
    expect(engineLink).toHaveAttribute(
      "href",
      "/product?category=engine-parts",
    );
  });

  it("renders Not sure CTA in panel 1", () => {
    renderMenu();
    expect(screen.getByText("Not sure what you need?")).toBeInTheDocument();
  });

  // ── Panel 2 — brands grid ──────────────────────────────────────────────────

  it("renders Popular Brands heading", () => {
    renderMenu();
    expect(screen.getByText("Popular Brands")).toBeInTheDocument();
  });

  it("renders up to 14 brands in grid", () => {
    useBrands.mockReturnValue({ data: makeBrands(20), isLoading: false });
    renderMenu();

    const brandLinks = screen
      .getAllByRole("link")
      .filter((l) => l.getAttribute("href")?.includes("/product?brand="));

    expect(brandLinks).toHaveLength(14);
  });

  it("shows View All Brands when brands exceed 14", () => {
    useBrands.mockReturnValue({ data: makeBrands(20), isLoading: false });
    renderMenu();

    expect(
      screen.getByRole("link", { name: /View All Brands/ }),
    ).toBeInTheDocument();
  });

  it("does not show View All Brands when brands 14 or fewer", () => {
    useBrands.mockReturnValue({ data: makeBrands(5), isLoading: false });
    renderMenu();

    expect(
      screen.queryByRole("link", { name: /View All Brands/ }),
    ).not.toBeInTheDocument();
  });

  it("brand link navigates to correct brand slug", () => {
    renderMenu();

    const brand1Link = screen.getByRole("link", { name: /Brand 1/ });
    expect(brand1Link).toHaveAttribute("href", "/product?brand=brand-1");
  });

  it("renders brand logo image when logo exists", () => {
    renderMenu();

    // Brand 1 (index 0 → even → has logo)
    const img = screen.getByAltText("Brand 1");
    expect(img).toHaveAttribute(
      "src",
      "http://localhost/media/brand-1.png",
    );
  });

  it("renders brand initial letter when logo is null", () => {
    // ✅ FIX: Use specific brand name — Brand 2 has no logo
    // Use getAllByText since multiple brands may share first letter
    // Instead query the specific brand link that has no img
    renderMenu();

    // Brand 2 has no logo → renders "B" initial inside its link
    const brand2Link = screen.getByRole("link", { name: /Brand 2/ });
    expect(brand2Link).toBeInTheDocument();

    // The initial "B" is inside brand2Link
    expect(brand2Link.querySelector("span.text-gray-400")).toHaveTextContent("B");
  });

  // ── Panel 3 — promo card ───────────────────────────────────────────────────

  it("renders 100% Genuine promo card", () => {
    renderMenu();
    expect(screen.getByText("100% Genuine")).toBeInTheDocument();
    expect(screen.getByText("Trusted Brands")).toBeInTheDocument();
  });

  // ── Trust badges ───────────────────────────────────────────────────────────

  it("renders all 5 trust badges", () => {
    renderMenu();

    expect(screen.getByText("100% Genuine Parts")).toBeInTheDocument();
    expect(screen.getByText("Best Prices")).toBeInTheDocument();
    expect(screen.getByText("Fast Delivery")).toBeInTheDocument();
    expect(screen.getByText("Easy Returns")).toBeInTheDocument();
    expect(screen.getByText("Secure Payments")).toBeInTheDocument();
  });

  // ── Bottom strip ───────────────────────────────────────────────────────────

  it("renders Looking for a specific brand text", () => {
    renderMenu();
    expect(
      screen.getByText("Looking for a specific brand?"),
    ).toBeInTheDocument();
  });

  it("renders Request a Brand button", () => {
    renderMenu();
    expect(
      screen.getByRole("button", { name: /Request a Brand/ }),
    ).toBeInTheDocument();
  });

  // ── onClose ────────────────────────────────────────────────────────────────

  it("calls onClose on mouse leave from menu container", () => {
    renderMenu();

    const menu = document.querySelector(".absolute");
    fireEvent.mouseLeave(menu);

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when category link clicked", () => {
    renderMenu();

    // ✅ FIX: use regex match — link name includes the › span
    fireEvent.click(screen.getByRole("link", { name: /Engine Parts/ }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when brand link clicked", () => {
    renderMenu();

    fireEvent.click(screen.getByRole("link", { name: /Brand 1/ }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});