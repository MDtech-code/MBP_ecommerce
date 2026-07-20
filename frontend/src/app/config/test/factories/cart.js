// src/app/config/test/factories/cart.js
import { createProduct } from "./product";

// ── Cart item ─────────────────────────────────────────────────────────────────
export const createCartItem = (overrides = {}) => ({
  id: 1,
  product: createProduct(),
  quantity: 1,
  unit_price: "1500.00",
  total_price: "1500.00",
  ...overrides,
});

// ── Cart ──────────────────────────────────────────────────────────────────────
// Shape returned by GET /api/cart/ → extractResponse → data
export const createCart = (overrides = {}) => ({
  id: 1,
  items: [createCartItem()],
  total_items: 1,
  total_price: "1500.00",
  is_empty: false,
  ...overrides,
});

// ── Empty cart ────────────────────────────────────────────────────────────────
export const createEmptyCart = () =>
  createCart({
    items: [],
    total_items: 0,
    total_price: "0.00",
    is_empty: true,
  });

// ── Cart response ─────────────────────────────────────────────────────────────
// Full extractResponse shape — what useCartQuery.queryFn returns
export const createCartResponse = (cartOverrides = {}) => ({
  data: createCart(cartOverrides),
  message: null,
  meta: null,
});
