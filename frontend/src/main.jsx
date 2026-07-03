import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import {  QueryClientProvider } from '@tanstack/react-query'

import { ApolloProvider } from "@apollo/client/react";
import { client } from "./graphql/client";
import { setupInterceptors } from './api/interceptors'
import { initAuthSync } from "./api/authSync";
import { queryClient } from "./lib/queryClient.jsx"

initAuthSync();
setupInterceptors();


createRoot(document.getElementById('root')).render(
  <StrictMode>
  <QueryClientProvider client={queryClient}>
    <ApolloProvider client={client}>
    <App />
    </ApolloProvider>
  </QueryClientProvider>
  </StrictMode>
)
