// // src/lib/queryClient.js
// import { QueryClient } from "@tanstack/react-query";
// import { normalizeError } from "../api/transformers";

// export const queryClient = new QueryClient({
//   defaultOptions: {
//     queries: {
//       // Data is "fresh" for 5 minutes — won't re-fetch if already in cache
//       staleTime: 1000 * 60 * 5,

//       // Keep inactive query data in cache for 10 minutes
//       gcTime: 1000 * 60 * 10,

//       // Smart retry: never retry client errors (4xx), retry network/server errors
//       retry: (failureCount, error) => {
//         const normalized = normalizeError(error);
//         if (normalized.isClientError) return false; // 4xx → never retry
//         if (normalized.isNetworkError) return failureCount < 3;
//         return failureCount < 2; // 5xx → retry twice
//       },

//       // Don't spam refetch when user switches tabs (adjust per feature if needed)
//       refetchOnWindowFocus: false,

//       // Propagate errors to nearest ErrorBoundary
//       throwOnError: false,
//     },

//     mutations: {
//       retry: false, // Never auto-retry mutations — side effects are dangerous to repeat
//     },
//   },
// });
