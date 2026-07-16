import { useMutation} from "@tanstack/react-query";
import { accountService } from "../../../shared/api/services/accountService";
// import { useAuthStore } from "../../../entities/user/model/authStore";

import { queryClient } from "../../../shared/lib/queryClient";




// src/hooks/account/useAuthMutations.js
// Add these after useChangePassword

/**
 * useCreateAddress
 * POST /api/accounts/addresses/
 * On success: sync full user back into store so addresses list updates
 * immediately without page refresh
 */
export function useCreateAddress() {
  

  return useMutation({
    mutationFn: accountService.createAddress,
    onSuccess: () => {
      // Refetch full profile — addresses are nested in user object
      // invalidateQueries triggers useProfile to re-fetch and setUser
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}

/**
 * useUpdateAddress
 * PUT /api/accounts/addresses/:id/
 * On success: refetch profile to sync updated address into store
 */
export function useUpdateAddress() {
  return useMutation({
    mutationFn: ({ id, data }) => accountService.updateAddress(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}

/**
 * useDeleteAddress
 * DELETE /api/accounts/addresses/:id/
 * On success: refetch profile — deleted address must disappear from list
 */
export function useDeleteAddress() {
  return useMutation({
    mutationFn: (id) => accountService.deleteAddress(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}

/**
 * useSetDefaultAddress
 * PATCH /api/accounts/addresses/:id/set-default/
 * On success: refetch profile — is_default flags must update across all cards
 */
export function useSetDefaultAddress() {
  return useMutation({
    mutationFn: (id) => accountService.setDefaultAddress(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}