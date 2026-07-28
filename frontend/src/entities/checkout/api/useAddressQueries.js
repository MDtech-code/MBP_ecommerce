// src/features/checkout/api/useAddressQueries.js

/**
 * useAddressQueries — re-export for checkout feature.
 *
 * Why re-export instead of duplicate:
 *   The address list query already exists in features/address/api/useAddressQuery.js
 *   created in Phase 2. Duplicating it would create two separate cache keys
 *   for the same data — mutations would need to invalidate both.
 *
 *   Re-exporting means checkout uses the exact same cache entry as the
 *   address management feature. When user adds/edits an address in checkout,
 *   the same ["account", "addresses"] key is invalidated and both consumers
 *   see the update.
 *
 * Consumers:
 *   useCheckoutAddress — address step logic hook
 *   CheckoutAddressPage — via useCheckoutAddress
 */

export {
  useAddressListQuery,
  ADDRESS_LIST_KEY,
} from "@features/address/api/useAddressQuery";
