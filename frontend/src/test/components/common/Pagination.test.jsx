// src/test/components/common/Pagination.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import Pagination from "../../../components/common/Pagination";

// ─── Helpers ──────────────────────────────────────────────────────────────────

const onPageChange = vi.fn();

function renderPagination(props = {}) {
  const defaults = {
    currentPage: 1,
    totalPages: 5,
    hasNext: true,
    hasPrevious: false,
    onPageChange,
  };
  return render(<Pagination {...defaults} {...props} />);
}

beforeEach(() => {
  vi.clearAllMocks();
  // Mock window.scrollTo — jsdom doesn't implement it
  window.scrollTo = vi.fn();
});

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("Pagination", () => {

  // ── Render nothing ─────────────────────────────────────────────────────────

  it("renders nothing when totalPages is 1", () => {
    const { container } = renderPagination({ totalPages: 1 });
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing when totalPages is 0", () => {
    const { container } = renderPagination({ totalPages: 0 });
    expect(container.firstChild).toBeNull();
  });

  // ── Page buttons ───────────────────────────────────────────────────────────

  it("renders page number buttons", () => {
    renderPagination({ currentPage: 1, totalPages: 5 });

    expect(screen.getByRole("button", { name: "1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "2" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "3" })).toBeInTheDocument();
  });

  it("applies active style to currentPage button", () => {
    renderPagination({ currentPage: 3, totalPages: 10 });

    const activeBtn = screen.getByRole("button", { name: "3" });
    expect(activeBtn.className).toContain("bg-primary");
    expect(activeBtn.className).toContain("text-white");
  });

  it("does not apply active style to non-current page buttons", () => {
    renderPagination({ currentPage: 1, totalPages: 5 });

    const btn2 = screen.getByRole("button", { name: "2" });
    expect(btn2.className).not.toContain("bg-primary");
  });

  // ── Prev / Next buttons ────────────────────────────────────────────────────

  it("renders Prev button", () => {
    renderPagination();
    // ChevronLeft inside — query by its container button
    const buttons = screen.getAllByRole("button");
    // First button is always Prev
    expect(buttons[0]).toBeInTheDocument();
  });

  it("disables Prev button when hasPrevious is false", () => {
    renderPagination({ hasPrevious: false });
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).toBeDisabled();
  });

  it("enables Prev button when hasPrevious is true", () => {
    renderPagination({ currentPage: 3, hasPrevious: true });
    const buttons = screen.getAllByRole("button");
    expect(buttons[0]).not.toBeDisabled();
  });

  it("disables Next button when hasNext is false", () => {
    renderPagination({ hasNext: false });
    const buttons = screen.getAllByRole("button");
    const nextBtn = buttons[buttons.length - 1];
    expect(nextBtn).toBeDisabled();
  });

  it("enables Next button when hasNext is true", () => {
    renderPagination({ hasNext: true });
    const buttons = screen.getAllByRole("button");
    const nextBtn = buttons[buttons.length - 1];
    expect(nextBtn).not.toBeDisabled();
  });

  // ── Click handlers ─────────────────────────────────────────────────────────

  it("calls onPageChange with next page when Next clicked", () => {
    renderPagination({ currentPage: 2, totalPages: 5, hasNext: true });

    const buttons = screen.getAllByRole("button");
    const nextBtn = buttons[buttons.length - 1];
    fireEvent.click(nextBtn);

    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it("calls onPageChange with previous page when Prev clicked", () => {
    renderPagination({
      currentPage: 3,
      totalPages: 5,
      hasPrevious: true,
    });

    const buttons = screen.getAllByRole("button");
    fireEvent.click(buttons[0]);

    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("calls onPageChange with correct page when page number clicked", () => {
    renderPagination({ currentPage: 1, totalPages: 5 });

    fireEvent.click(screen.getByRole("button", { name: "3" }));

    expect(onPageChange).toHaveBeenCalledWith(3);
  });

  it("does NOT call onPageChange when clicking currentPage button", () => {
    renderPagination({ currentPage: 2, totalPages: 5 });

    fireEvent.click(screen.getByRole("button", { name: "2" }));

    expect(onPageChange).not.toHaveBeenCalled();
  });

  it("scrolls to top on page change", () => {
    renderPagination({ currentPage: 1, totalPages: 5, hasNext: true });

    fireEvent.click(screen.getByRole("button", { name: "2" }));

    expect(window.scrollTo).toHaveBeenCalledWith({
      top: 0,
      behavior: "smooth",
    });
  });

  // ── Ellipsis + Last page ───────────────────────────────────────────────────

  it("shows ellipsis when pages outside window exist", () => {
    renderPagination({ currentPage: 1, totalPages: 10 });

    expect(screen.getByText("...")).toBeInTheDocument();
  });

  it("shows last page button when outside window", () => {
    renderPagination({ currentPage: 1, totalPages: 10 });

    expect(screen.getByRole("button", { name: "10" })).toBeInTheDocument();
  });

  it("does not show ellipsis when all pages fit in window", () => {
    renderPagination({ currentPage: 1, totalPages: 5 });

    expect(screen.queryByText("...")).not.toBeInTheDocument();
  });

  it("calls onPageChange with last page when last page button clicked", () => {
    renderPagination({ currentPage: 1, totalPages: 10 });

    fireEvent.click(screen.getByRole("button", { name: "10" }));

    expect(onPageChange).toHaveBeenCalledWith(10);
  });

  // ── Page window centering ──────────────────────────────────────────────────

  it("shows window of max 5 pages", () => {
    renderPagination({ currentPage: 5, totalPages: 20 });

    // Should see pages 3,4,5,6,7 (centered around 5)
    expect(screen.getByRole("button", { name: "3" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "4" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "5" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "6" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "7" })).toBeInTheDocument();
  });

  it("adjusts window at end of pages", () => {
    renderPagination({ currentPage: 20, totalPages: 20 });

    // Window should be 16,17,18,19,20
    expect(screen.getByRole("button", { name: "16" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "20" })).toBeInTheDocument();
  });
});