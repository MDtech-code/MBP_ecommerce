// src/lib/queryClient.js
import { QueryClient } from "@tanstack/react-query";
import { normalizeError } from "@shared/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
     
      staleTime: 1000 * 60 * 5,

      
      gcTime: 1000 * 60 * 10,

      
      retry: (failureCount, error) => {
        const normalized = normalizeError(error);
        if (normalized.isClientError) return false; 
        if (normalized.isNetworkError) return failureCount < 3;
        return failureCount < 2; // 5xx → retry twice
      },

      
      refetchOnWindowFocus: false,

      
      throwOnError: false,
    },

    mutations: {
      retry: false, 
    },
  },
});
