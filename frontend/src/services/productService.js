// // src/services/productService.js
// import { api } from "../api/client";
// import { extractResponse } from "../api/transformers";

// /**
//  * Product service — Layer 2
//  *
//  * Rules:
//  *   - Only makes API calls
//  *   - Always passes response through extractResponse()
//  *   - Never catches errors — let them bubble to hooks
//  *   - Never imports from hooks or stores
//  */

// export const productService = {
//   /**
//    * GET /api/products/categories/?view=tree
//    * Used by BikePartsMegaMenu — needs parent/child nesting
//    */
//   getCategoriesTree: async () => {
//     const response = await api.get("/api/products/categories/", {
//       params: { view: "tree" },
//     });
//     return extractResponse(response);
//   },

//   /**
//    * GET /api/products/categories/?view=flat
//    * Used by ProductSidebar — flat list for checkboxes
//    */
//   getCategoriesFlat: async () => {
//     const response = await api.get("/api/products/categories/", {
//       params: { view: "flat" },
//     });
//     return extractResponse(response);
//   },

//   /**
//    * GET /api/products/brands/
//    * Used by BrandsMegaMenu and ProductSidebar
//    */
//   getBrands: async () => {
//     const response = await api.get("/api/products/brands/");
//     return extractResponse(response);
//   },

//   /**
//    * GET /api/products/bike-models/
//    * GET /api/products/bike-models/?brand=<id>
//    * Used by ProductSidebar bike model dropdown
//    *
//    * @param {number|null} brandId
//    */
//   getBikeModels: async (brandId = null) => {
//     const params = brandId ? { brand: brandId } : {};
//     const response = await api.get("/api/products/bike-models/", { params });
//     return extractResponse(response);
//   },

//   /**
//    * GET /api/products/
//    * Full filter + sort + pagination support
//    *
//    * @param {Object} filters
//    * @param {string}  filters.category    - category slug
//    * @param {string}  filters.brand       - brand slug
//    * @param {number}  filters.bike_model  - bike model id
//    * @param {number}  filters.min_price
//    * @param {number}  filters.max_price
//    * @param {string}  filters.q           - search query
//    * @param {boolean} filters.featured
//    * @param {string}  filters.sort        - featured|newest|price_asc|price_desc|name_asc
//    * @param {number}  filters.page
//    * @param {number}  filters.page_size
//    */
//   getProducts: async (filters = {}) => {
//     // Strip undefined/null/empty string values — keep only truthy params
//     const params = Object.fromEntries(
//       Object.entries(filters).filter(
//         ([, v]) => v !== null && v !== undefined && v !== "",
//       ),
//     );
//     const response = await api.get("/api/products/", { params });
//     return extractResponse(response);
//   },

//   /**
//    * GET /api/products/<slug>/
//    * Full product detail including related_products
//    *
//    * @param {string} slug
//    */
//   getProductBySlug: async (slug) => {
//     const response = await api.get(`/api/products/${slug}/`);
//     return extractResponse(response);
//   },
// };
