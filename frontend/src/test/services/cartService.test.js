// src/tests/services/cartService.test.js
import { describe, it, expect, vi, beforeEach } from "vitest";
import { cartService } from "../../services/cartService";
import { api } from "../../api/client";
import { extractResponse } from "../../api/transformers";

vi.mock("../../api/client");
vi.mock("../../api/transformers");

/**
 * cartService tests — Layer 2
 *
 * Strategy:
 *   - Mock api.get/post/patch/delete
 *   - Mock extractResponse to return its input (passthrough)
 *   - Verify correct HTTP method + URL + payload for each method
 *   - Verify extractResponse is always called with the api response
 *   - Verify errors bubble (no try/catch in service)
 */

const MOCK_API_RESPONSE = { data: { items: [], total_items: 0 } };
const MOCK_EXTRACTED = { data: { items: [], total_items: 0 } };

beforeEach(() => {
  vi.clearAllMocks();
  extractResponse.mockReturnValue(MOCK_EXTRACTED);
});

describe("cartService.getCart", () => {
  it("calls GET /api/cart/ and returns extractResponse result", async () => {
    api.get.mockResolvedValue(MOCK_API_RESPONSE);

    const result = await cartService.getCart();

    expect(api.get).toHaveBeenCalledWith("/api/cart/");
    expect(extractResponse).toHaveBeenCalledWith(MOCK_API_RESPONSE);
    expect(result).toEqual(MOCK_EXTRACTED);
  });

  it("bubbles error when api.get rejects", async () => {
    api.get.mockRejectedValue(new Error("Network error"));

    await expect(cartService.getCart()).rejects.toThrow("Network error");
  });
});

describe("cartService.addToCart", () => {
  it("calls POST /api/cart/items/ with correct payload", async () => {
    api.post.mockResolvedValue(MOCK_API_RESPONSE);

    const result = await cartService.addToCart(42, 2);

    expect(api.post).toHaveBeenCalledWith("/api/cart/items/", {
      product_id: 42,
      quantity: 2,
    });
    expect(extractResponse).toHaveBeenCalledWith(MOCK_API_RESPONSE);
    expect(result).toEqual(MOCK_EXTRACTED);
  });

  it("defaults quantity to 1 when not provided", async () => {
    api.post.mockResolvedValue(MOCK_API_RESPONSE);

    await cartService.addToCart(10);

    expect(api.post).toHaveBeenCalledWith("/api/cart/items/", {
      product_id: 10,
      quantity: 1,
    });
  });

  it("bubbles error when api.post rejects", async () => {
    api.post.mockRejectedValue(new Error("Server error"));

    await expect(cartService.addToCart(1)).rejects.toThrow("Server error");
  });
});

describe("cartService.updateCartItem", () => {
  it("calls PATCH /api/cart/items/<id>/ with correct payload", async () => {
    api.patch.mockResolvedValue(MOCK_API_RESPONSE);

    const result = await cartService.updateCartItem(7, 3);

    expect(api.patch).toHaveBeenCalledWith("/api/cart/items/7/", {
      quantity: 3,
    });
    expect(extractResponse).toHaveBeenCalledWith(MOCK_API_RESPONSE);
    expect(result).toEqual(MOCK_EXTRACTED);
  });

  it("allows quantity=0 (server-side auto-delete)", async () => {
    api.patch.mockResolvedValue(MOCK_API_RESPONSE);

    await cartService.updateCartItem(7, 0);

    expect(api.patch).toHaveBeenCalledWith("/api/cart/items/7/", {
      quantity: 0,
    });
  });
});

describe("cartService.removeCartItem", () => {
  it("calls DELETE /api/cart/items/<id>/", async () => {
    api.delete.mockResolvedValue(MOCK_API_RESPONSE);

    const result = await cartService.removeCartItem(5);

    expect(api.delete).toHaveBeenCalledWith("/api/cart/items/5/");
    expect(extractResponse).toHaveBeenCalledWith(MOCK_API_RESPONSE);
    expect(result).toEqual(MOCK_EXTRACTED);
  });
});

describe("cartService.clearCart", () => {
  it("calls DELETE /api/cart/clear/", async () => {
    api.delete.mockResolvedValue(MOCK_API_RESPONSE);

    const result = await cartService.clearCart();

    expect(api.delete).toHaveBeenCalledWith("/api/cart/clear/");
    expect(extractResponse).toHaveBeenCalledWith(MOCK_API_RESPONSE);
    expect(result).toEqual(MOCK_EXTRACTED);
  });
});
