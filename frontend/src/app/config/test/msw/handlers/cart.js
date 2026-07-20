// src/app/config/test/msw/handlers/cart.js

import { http, HttpResponse } from "msw";
import { createCartResponse, createEmptyCart } from "../../factories/cart";

const success = (data, message = null) => ({
  success: true,
  message,
  data,
  errors: null,
  meta: { request_id: "test-request-id" },
});

export const cartHandlers = [
  // ── Get cart ──────────────────────────────────────────────────────────────
  http.get("/api/cart/", () => {
    return HttpResponse.json(success(createCartResponse().data));
  }),

  // ── Add to cart ───────────────────────────────────────────────────────────
  http.post("/api/cart/items/", () => {
    return HttpResponse.json(success(createCartResponse().data), {
      status: 201,
    });
  }),

  // ── Update cart item ──────────────────────────────────────────────────────
  http.patch("/api/cart/items/:itemId/", () => {
    return HttpResponse.json(success(createCartResponse().data));
  }),

  // ── Remove cart item ──────────────────────────────────────────────────────
  http.delete("/api/cart/items/:itemId/", () => {
    return HttpResponse.json(success(createCartResponse().data));
  }),

  // ── Clear cart ────────────────────────────────────────────────────────────
  http.delete("/api/cart/clear/", () => {
    return HttpResponse.json(success(createEmptyCart()));
  }),
];
