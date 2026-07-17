// src/hooks/products/useProductDetail.js
import { useParams } from "react-router-dom";

import { useProductDetail as useProductDetailQuery } from "@entities/product";
import { normalizeError } from "@shared/api";

/**
 * useProductDetail — Layer 3b
 *
 * Business logic hook for the ProductDetail page.
 *
 * Responsibilities:
 *   - Reads slug from URL params (/product/:slug)
 *   - Exposes clean product fields — no raw API shape in the UI
 *   - Derives computed display values from backend fields
 *   - Handles 404 detection
 *   - Returns normalized error for error states
 *
 * Why derive display values here not in the component:
 *   Component stays dumb — just renders what it receives.
 *   If backend field names change, only this hook changes.
 *   Component never needs to know about discount_percentage vs has_discount.
 */
export function useProductDetail() {
  const { slug } = useParams();
  const {
    data: product,
    isLoading,
    isError,
    error,
  } = useProductDetailQuery(slug);

  const normalized = isError ? normalizeError(error) : null;

  // ── Derived display values ─────────────────────────────────────────────────

  // Images — sorted by order, primary first
  const images = product?.images
    ? [...product.images].sort((a, b) => a.order - b.order)
    : [];

  // Primary image URL for og/meta tags
  const primaryImageUrl =
    images.find((img) => img.is_primary)?.image ?? images[0]?.image ?? null;

  // image URLs array for gallery component
  const imageUrls = images.map((img) => img.image);

  // Compatible bikes as display strings
  const compatibleBikes =
    product?.compatible_bikes?.map((bike) => bike.display_name) ?? [];

  // Breadcrumb parts
  // category.parent_name → category.name → product.name
  const breadcrumb = [
    { label: "Home", to: "/" },
    product?.category?.parent_name
      ? {
          label: product.category.parent_name,
          to: `/product?category=${product.category.parent}`,
        }
      : null,
    product?.category
      ? {
          label: product.category.name,
          to: `/product?category=${product.category.slug}`,
        }
      : null,
    product ? { label: product.name, to: null } : null,
  ].filter(Boolean);

  // Price display
  const displayPrice = product
    ? `Rs. ${parseFloat(product.current_price).toLocaleString()}`
    : null;

  const originalPrice = product?.has_discount
    ? `Rs. ${parseFloat(product.price).toLocaleString()}`
    : null;

  // 404 detection
  const isNotFound = isError && normalized?.isNotFound;

  return {
    // Raw product (for components that need full object)
    product,

    // Loading states
    isLoading,
    isError,
    isNotFound,
    errorMessage: normalized?.message ?? null,

    // Derived values — component renders these directly
    images,
    imageUrls,
    primaryImageUrl,
    compatibleBikes,
    breadcrumb,
    displayPrice,
    originalPrice,

    // Convenience shorthand
    name: product?.name ?? null,
    description: product?.description ?? "",
    sku: product?.sku ?? null,
    brandName: product?.brand?.name ?? null,
    brandLogo: product?.brand?.logo ?? null,
    categoryName: product?.category?.name ?? null,
    hasDiscount: product?.has_discount ?? false,
    discountPercentage: product?.discount_percentage ?? 0,
    isInStock: product?.is_in_stock ?? false,
    stock: product?.stock ?? 0,
    isFeatured: product?.is_featured ?? false,
    relatedProducts: product?.related_products ?? [],
  };
}
