import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './styles/index.css'
import App from './App.jsx'
import {  QueryClientProvider } from '@tanstack/react-query'
import { GoogleOAuthProvider } from "@react-oauth/google";
import { ApolloProvider } from "@apollo/client/react";
import { client } from "@shared/api";
import { setupInterceptors } from '@shared/api'
import { initAuthSync } from "@shared/lib";
import { queryClient } from "@shared/lib"

initAuthSync();
setupInterceptors();


createRoot(document.getElementById('root')).render(
  <StrictMode>
  <QueryClientProvider client={queryClient}>
    <ApolloProvider client={client}>
    <GoogleOAuthProvider clientId={import.meta.env.VITE_GOOGLE_CLIENT_ID}>
    <App />
    </GoogleOAuthProvider>
    </ApolloProvider>
  </QueryClientProvider>
  </StrictMode>
)
