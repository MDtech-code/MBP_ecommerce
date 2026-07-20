// src/app/config/test/msw/handlers/products.js

import { http, HttpResponse } from "msw";
import {
  createProduct,
  createCategory,
  createBrand,
  createBikeModel,
  createProductListResponse,
} from "../../factories/product";

const success = (data, meta = null) => ({
  success: true,
  message: null,
  data,
  errors: null,
  meta: { request_id: "test-request-id", ...meta },
});

export const productHandlers = [
  // ── Categories (tree + flat) ──────────────────────────────────────────────
  // Both views use the same endpoint with ?view= param
  http.get("/api/products/categories/", ({ request }) => {
    const url = new URL(request.url);
    const view = url.searchParams.get("view");

    if (view === "tree") {
      return HttpResponse.json(
        success([{ ...createCategory(), children: [] }]),
      );
    }
    // flat
    return HttpResponse.json(success([createCategory()]));
  }),

  // ── Brands ────────────────────────────────────────────────────────────────
  http.get("/api/products/brands/", () => {
    return HttpResponse.json(success([createBrand()]));
  }),

  // ── Bike models ───────────────────────────────────────────────────────────
  http.get("/api/products/bike-models/", () => {
    return HttpResponse.json(success([createBikeModel()]));
  }),

  // ── Product list ──────────────────────────────────────────────────────────
  http.get("/api/products/", () => {
    const response = createProductListResponse();
    return HttpResponse.json(success(response.data, response.meta));
  }),

  // ── Product detail ────────────────────────────────────────────────────────
  http.get("/api/products/:slug/", ({ params }) => {
    return HttpResponse.json(success(createProduct({ slug: params.slug })));
  }),
];
