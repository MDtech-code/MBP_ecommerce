import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App.jsx'
import {  QueryClientProvider } from '@tanstack/react-query'

import { ApolloProvider } from "@apollo/client/react";
import { client } from "../shared/api/graphqlClient.js";
import { setupInterceptors } from '../shared/api/interceptors.js'
import { initAuthSync } from "../shared/lib/authSync";
import { queryClient } from "../shared/lib/queryClient.js"

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
