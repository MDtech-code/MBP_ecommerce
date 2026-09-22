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
      

      // ── NEW — correct key ─────────────────────────────────────────
      queryClient.invalidateQueries({ queryKey: PROFILE_KEY })
    },
  })
}
