// src/app/config/test/factories/product.js

// ── Product ───────────────────────────────────────────────────────────────────
export const createProduct = (overrides = {}) => ({
  id: 1,
  name: "Test Brake Pad",
  slug: "test-brake-pad",
  description: "High quality brake pads for all bikes.",
  price: "1500.00",
  sale_price: null,
  is_on_sale: false,
  stock: 10,
  is_in_stock: true,
  featured: false,
  images: [createProductImage()],
  primary_image: createProductImage(),
  category: createCategory(),
  brand: createBrand(),
  specifications: [],
  related_products: [],
  ...overrides,
});

// ── Product image ─────────────────────────────────────────────────────────────
export const createProductImage = (overrides = {}) => ({
  id: 1,
  image: "/media/products/test-brake-pad.jpg",
  alt_text: "Test Brake Pad",
  is_primary: true,
  ...overrides,
});

// ── Category ──────────────────────────────────────────────────────────────────
export const createCategory = (overrides = {}) => ({
  id: 1,
  name: "Brakes",
  slug: "brakes",
  icon: null,
  parent: null,
  children: [],
  ...overrides,
});

// ── Brand ─────────────────────────────────────────────────────────────────────
export const createBrand = (overrides = {}) => ({
  id: 1,
  name: "Test Brand",
  slug: "test-brand",
  logo: null,
  ...overrides,
});

// ── Bike model ────────────────────────────────────────────────────────────────
export const createBikeModel = (overrides = {}) => ({
  id: 1,
  name: "Honda CB150F",
  brand: 1,
  ...overrides,
});

// ── Product list response ─────────────────────────────────────────────────────
// Shape returned by GET /api/products/ → extractResponse
// meta contains pagination
export const createProductListResponse = (
  products = [],
  metaOverrides = {},
) => ({
  data: products.length ? products : [createProduct()],
  message: null,
  meta: {
    pagination: {
      page: 1,
      page_size: 20,
      total_pages: 1,
      total_items: products.length || 1,
    },
    ...metaOverrides,
  },
});
