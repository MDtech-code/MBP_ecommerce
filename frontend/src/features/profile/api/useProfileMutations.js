// src/features/profile/api/useProfileMutations.js

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { accountService } from "@shared/api"
import { useAuthStore } from "@entities/user"
import { queryClient } from "@shared/lib"

const PROFILE_KEY = ["account", "profile"]

export function useProfile(options = {}) {
  const setUser = useAuthStore((state) => state.setUser)

  return useQuery({
    queryKey: PROFILE_KEY,
    queryFn: async () => {
      const result = await accountService.getProfile()
      setUser(result.data)
      return result
    },
    ...options,
  })
}

export function useUpdateProfile() {
  const setUser = useAuthStore((state) => state.setUser)
  return useMutation({
    mutationFn: accountService.updateProfile,
    onSuccess: ({ data }) => {
      setUser(data)
      queryClient.invalidateQueries({ queryKey: PROFILE_KEY })
    },
  })
}

export function useUploadAvatar() {
  return useMutation({
    mutationFn: accountService.uploadAvatar,

    // ── OLD ────────────────────────────────────────────────────────
    // Manual Zustand merge — inconsistent with all other mutations
    // that use query invalidation as the single update strategy.
    // Manual merge is also fragile: if user object shape changes on
    // backend, this merge silently produces a stale nested object.
    //
    // onSuccess: ({ data }) => {
    //   setUser({
    //     ...user,
    //     profile: { ...user.profile, avatar: data.avatar },
    //   })
    // },
    // ───────────────────────────────────────────────────────────────

    // ── NEW ────────────────────────────────────────────────────────
    // Invalidate profile query — refetch calls setUser once via
    // useProfile queryFn. Single consistent strategy across all
    // mutations. Backend response is always source of truth.
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: PROFILE_KEY })
    },
  })
}

export function useSendPhoneOtp() {
  return useMutation({
    mutationFn: (phone) => accountService.sendPhoneOtp({ phone }),
  })
}

export function useVerifyPhoneOtp() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ phone, otp }) =>
      accountService.verifyPhoneOtp({ phone, otp }),
    onSuccess: () => {
      // ── OLD ──────────────────────────────────────────────────────
      // Wrong key — ["user-profile"] does not match ["account","profile"]
      // Invalidation fired but matched nothing — is_phone_verified
      // stayed stale in Zustand until manual page refresh.
      //
      // queryClient.invalidateQueries({ queryKey: ["user-profile"] })
      // ─────────────────────────────────────────────────────────────

      // ── NEW — correct key ─────────────────────────────────────────
      queryClient.invalidateQueries({ queryKey: PROFILE_KEY })
    },
  })
}
// import { useMutation, useQuery ,useQueryClient} from "@tanstack/react-query";
// import { accountService } from "@shared/api";
// import { useAuthStore } from "@entities/user";

// import { queryClient } from "@shared/lib";





// /**
//  * useProfile
//  * GET /api/accounts/profile/
//  * Called on protected pages to restore user state after page refresh
//  * Only runs when user has an access token (hasAuthToken check in component)
//  */
// export function useProfile(options = {}) {
//   const setUser = useAuthStore((state) => state.setUser);

//   return useQuery({
//     queryKey: ["account", "profile"],
//     queryFn: async () => {
//       const result = await accountService.getProfile();
//       // Sync fetched profile into Zustand so UI is always consistent
//       setUser(result.data);
//       return result;
//     },
//     ...options,
//   });
// }

// export function useUpdateProfile() {
//   const setUser = useAuthStore((state) => state.setUser);
//   return useMutation({
//     mutationFn: accountService.updateProfile,
//     onSuccess: ({ data }) => {
//       setUser(data);
//       queryClient.invalidateQueries({ queryKey: ["account", "profile"] });
//     },
//   });
// }



// export function useUploadAvatar() {
//   const user = useAuthStore((state) => state.user);
//   const setUser = useAuthStore((state) => state.setUser);
//   return useMutation({
//     mutationFn: accountService.uploadAvatar,
//     onSuccess: ({ data }) => {
//       setUser({
//         ...user,
//         profile: {
//           ...user.profile,
//           avatar: data.avatar,
//         },
//       });
//     },
//   });
// }



// export function useSendPhoneOtp() {
//   return useMutation({
//     mutationFn: (phone) => accountService.sendPhoneOtp({ phone }),
//   });
// }

// export function useVerifyPhoneOtp() {
//   const queryClient = useQueryClient();
//   return useMutation({
//     mutationFn: ({ phone, otp }) =>
//       accountService.verifyPhoneOtp({ phone, otp }),
//     onSuccess: () => {
//       // Invalidate user profile so ProfileView re-fetches is_phone_verified
//       queryClient.invalidateQueries({ queryKey: ["user-profile"] });
//     },
//   });
// }
