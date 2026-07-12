// src/test/components/product-detail/ProductGallery.test.jsx
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import ProductGallery from "../../../components/product-detail/ProductGallery";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const makeImages = (count, primaryIndex = 0) =>
  Array.from({ length: count }, (_, i) => ({
    id:         i + 1,
    image:      `/media/img-${i + 1}.jpg`,
    is_primary: i === primaryIndex,
    order:      i + 1,
  }));

function renderGallery(props = {}) {
  return render(<ProductGallery {...props} />);
}

beforeEach(() => vi.clearAllMocks());

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("ProductGallery", () => {

  // ── Empty state ────────────────────────────────────────────────────────────

  it("shows fallback image when images array is empty", () => {
    renderGallery({ images: [] });

    const img = screen.getByAltText("No image available");
    expect(img).toHaveAttribute("src", "/placeholder-part.png");
  });

  it("does not render thumbnails when images is empty", () => {
    renderGallery({ images: [] });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("defaults images to empty array when not provided", () => {
    renderGallery();
    expect(screen.getByAltText("No image available")).toBeInTheDocument();
  });

  // ── Single image ───────────────────────────────────────────────────────────

  it("renders main image with correct src", () => {
    const images = makeImages(1);
    renderGallery({ images });

    const mainImg = screen.getByAltText("product");
    expect(mainImg).toHaveAttribute("src", "/media/img-1.jpg");
  });

  it("does not render thumbnails when only 1 image", () => {
    renderGallery({ images: makeImages(1) });
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  // ── Multiple images ────────────────────────────────────────────────────────

  it("renders thumbnails when multiple images exist", () => {
    renderGallery({ images: makeImages(3) });

    // Each thumbnail is a button
    expect(screen.getAllByRole("button")).toHaveLength(3);
  });

  it("renders thumbnail images with correct alt text", () => {
    renderGallery({ images: makeImages(3) });

    expect(screen.getByAltText("thumb-0")).toBeInTheDocument();
    expect(screen.getByAltText("thumb-1")).toBeInTheDocument();
    expect(screen.getByAltText("thumb-2")).toBeInTheDocument();
  });

  // ── Primary image — initial active state ───────────────────────────────────

  it("sets primary image as initial active image", () => {
    // primaryIndex = 1 → img-2 should be the main displayed image
    const images = makeImages(3, 1);
    renderGallery({ images });

    const mainImg = screen.getByAltText("product");
    expect(mainImg).toHaveAttribute("src", "/media/img-2.jpg");
  });

  it("defaults to first image when no image is_primary", () => {
    const images = makeImages(3).map((img) => ({
      ...img,
      is_primary: false,
    }));
    renderGallery({ images });

    const mainImg = screen.getByAltText("product");
    expect(mainImg).toHaveAttribute("src", "/media/img-1.jpg");
  });

  // ── Thumbnail click changes active image ───────────────────────────────────

  it("changes main image when thumbnail is clicked", () => {
    renderGallery({ images: makeImages(3) });

    // Click second thumbnail (index 1)
    const thumbnails = screen.getAllByRole("button");
    fireEvent.click(thumbnails[1]);

    const mainImg = screen.getByAltText("product");
    expect(mainImg).toHaveAttribute("src", "/media/img-2.jpg");
  });

  it("applies active border to selected thumbnail", () => {
    renderGallery({ images: makeImages(3) });

    const thumbnails = screen.getAllByRole("button");

    // Click third thumbnail
    fireEvent.click(thumbnails[2]);

    // Active thumbnail has border-primary class
    expect(thumbnails[2].className).toContain("border-primary");
  });

  it("removes active border from previously selected thumbnail", () => {
    renderGallery({ images: makeImages(3) });

    const thumbnails = screen.getAllByRole("button");

    // Initially first is active → click second
    fireEvent.click(thumbnails[1]);

    // First should no longer have border-primary
    expect(thumbnails[0].className).not.toContain("border-primary");
    expect(thumbnails[1].className).toContain("border-primary");
  });

  it("clicking same thumbnail again keeps it active", () => {
    renderGallery({ images: makeImages(3) });

    const thumbnails = screen.getAllByRole("button");
    fireEvent.click(thumbnails[0]);
    fireEvent.click(thumbnails[0]);

    expect(thumbnails[0].className).toContain("border-primary");
  });

  // ── Fallback on image error ────────────────────────────────────────────────

  it("falls back main image to placeholder on error", () => {
    renderGallery({ images: makeImages(1) });

    const mainImg = screen.getByAltText("product");
    fireEvent.error(mainImg);

    expect(mainImg).toHaveAttribute("src", "/placeholder-part.png");
  });

  it("falls back thumbnail to placeholder on error", () => {
    renderGallery({ images: makeImages(2) });

    const thumbImgs = screen.getAllByAltText(/thumb-/);
    fireEvent.error(thumbImgs[0]);

    expect(thumbImgs[0]).toHaveAttribute("src", "/placeholder-part.png");
  });
});