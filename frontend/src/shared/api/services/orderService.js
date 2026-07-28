/**
 * orderService.js — Order API layer
 *
 * Rules (same as all service files):
 *   - Only makes API calls
 *   - Always passes response through extractResponse()
 *   - Never catches errors — let them bubble to hooks
 *   - Never imports from hooks or stores
 *
 * Backend endpoints:
 *   POST /api/orders/checkout/              → place order
 *   GET  /api/orders/                       → paginated order list
 *   GET  /api/orders/<order_number>/        → order detail
 *   POST /api/orders/<order_number>/cancel/ → cancel pending order
 */

import { api } from "../client";
import { extractResponse } from "../transformers";

export const orderService = {
  /**
   * POST /api/orders/checkout/
   *
   * Executes full atomic checkout.
   * Coupon already applied on cart — not passed here.
   *
   * @param {{
   *   payment_method: "cod" | "online" | "bank_transfer",
   *   selected_item_ids: number[],
   *   notes: string,
   *   shipping_address: {
   *     full_name: string,
   *     phone: string,
   *     address_line1: string,
   *     address_line2: string,
   *     city: string,
   *     province: string,
   *     postal_code: string,
   *   }
   * }} checkoutData
   */
  checkout: async (checkoutData) => {
    const response = await api.post("/api/orders/checkout/", checkoutData);
    return extractResponse(response);
  },

  /**
   * GET /api/orders/
   * Returns paginated list of authenticated user's orders.
   * Most recent first.
   *
   * @param {{ page?: number, pageSize?: number }} options
   */
  getOrders: async ({ page = 1, pageSize = 10 } = {}) => {
    const response = await api.get("/api/orders/", {
      params: {
        page,
        page_size: pageSize,
      },
    });
    return extractResponse(response);
  },

  /**
   * GET /api/orders/<order_number>/
   * Returns full order detail with items, address, payment status.
   * Ownership enforced at backend — wrong user gets 404.
   *
   * @param {string} orderNumber e.g. "ORD-20240115-A1B2C3D4"
   */
  getOrderDetail: async (orderNumber) => {
    const response = await api.get(`/api/orders/${orderNumber}/`);
    return extractResponse(response);
  },

  /**
   * POST /api/orders/<order_number>/cancel/
   * Cancels a PENDING order.
   * Returns 409 DomainError if order is not cancellable.
   *
   * @param {string} orderNumber
   */
  cancelOrder: async (orderNumber) => {
    const response = await api.post(`/api/orders/${orderNumber}/cancel/`);
    return extractResponse(response);
  },
};
