import { useMutation, useQuery } from "@tanstack/react-query";
import { accountService } from "../../../shared/api/services/accountService";
import { useAuthStore } from "../../../entities/user/model/authStore";

import { queryClient } from "../../../shared/lib/queryClient";





/**
 * useProfile
 * GET /api/accounts/profile/
 * Called on protected pages to restore user state after page refresh
 * Only runs when user has an access token (hasAuthToken check in component)
 */
export function useProfile(options = {}) {
  const setUser = useAuthStore((state) => state.setUser);

  return useQuery({
    queryKey: ["account", "profile"],
    queryFn: async () => {
      const result = await accountService.getProfile();
      // Sync fetched profile into Zustand so UI is always consistent
      setUser(result.data);
      return result;
    },
    ...options,
  });
}

export function useUpdateProfile() {
  const setUser = useAuthStore((state) => state.setUser);
  return useMutation({
    mutationFn: accountService.updateProfile,
    onSuccess: ({ data }) => {
      setUser(data);
      queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
    },
  });
}



export function useUploadAvatar() {
  const user = useAuthStore((state) => state.user);
  const setUser = useAuthStore((state) => state.setUser);
  return useMutation({
    mutationFn: accountService.uploadAvatar,
    onSuccess: ({ data }) => {
      setUser({
        ...user,
        profile: {
          ...user.profile,
          avatar: data.avatar,
        },
      });
    },
  });
}




