import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ApolloProvider } from "@apollo/client/react";
import { client } from "./graphql/client";
import { setupInterceptors } from './api/interceptors'
import { initAuthSync } from "./api/authSync";

initAuthSync();
setupInterceptors();
// const queryClient = new QueryClient() 
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error?.response?.status === 401) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
      gcTime: 1000 * 60 * 30,
    },
    mutations: {
      retry: 1,
    },
  },
});


createRoot(document.getElementById('root')).render(
  <StrictMode>
  <QueryClientProvider client={queryClient}>
    <ApolloProvider client={client}>
    <App />
    </ApolloProvider>
  </QueryClientProvider>
  </StrictMode>
)
