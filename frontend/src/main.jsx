import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import 'bootstrap/dist/css/bootstrap.min.css' 
import './index.css'
import App from './App.jsx'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { ApolloProvider } from "@apollo/client/react";
import { client } from "./graphql/client";
import "./api/interceptors";
import { initAuthSync } from "./api/authSync";

initAuthSync();
const queryClient = new QueryClient() 
createRoot(document.getElementById('root')).render(
  <StrictMode>
  <QueryClientProvider client={queryClient}>
    <ApolloProvider client={client}>
    <App />
    </ApolloProvider>
  </QueryClientProvider>
  </StrictMode>
)
