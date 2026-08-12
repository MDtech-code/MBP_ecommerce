// src/features/address/api/useAddressQuery.js

import { useQuery } from "@tanstack/react-query";
import { accountService,extractData } from "@shared/api";

/**
 * Address query — fetches user's saved addresses for checkout.
 *
 * Why separate from profile query:
 *   Profile query ["account", "profile"] fetches full user + addresses together.
 *   That query is used for profile/security pages where full user context needed.
 *
 *   Checkout only needs the addresses list — lightweight, focused.
 *   Separate key ["account", "addresses"] means:
 *     - Checkout doesn't trigger full profile refetch on address change
 *     - Address mutations can invalidate this key specifically
 *     - staleTime tuned for checkout context (5 min — addresses change rarely)
 *
 * Why accountService.getAddresses() not profile:
 *   GET /api/accounts/addresses/ returns addresses only — less payload.
 *   GET /api/accounts/profile/ returns full user object — unnecessary here.
 *
 * Endpoint: GET /api/accounts/addresses/
 * Backend view: AddressListCreateView.get()
 * Returns: UserAddressSerializer[] with full address fields
 */

export const ADDRESS_LIST_KEY = ["account", "addresses"];

export function useAddressListQuery() {
  return useQuery({
    queryKey: ADDRESS_LIST_KEY,
    queryFn: () => accountService.getAddresses(),
    staleTime: 1000 * 60 * 5, // 5 min — addresses change rarely
    select: (result) => extractData(result),
  });
}
