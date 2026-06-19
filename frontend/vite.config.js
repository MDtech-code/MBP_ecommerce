import { defineConfig } from 'vite'          // Vite config helper
import react from '@vitejs/plugin-react'     // Enables React JSX/fast refresh
import fs from 'fs'                          // Node file system (to read certs)

export default defineConfig({
  plugins: [react()],                        // Load React plugin
  server: {
    host: '0.0.0.0',                         // Bind to all interfaces (local + Docker)
    port: 5173,                              // Dev server port
    hmr: {
      clientPort: 5173                       // WebSocket port for hot reload (HMR)
    },
    watch: {
      usePolling: true                       // Ensures file changes are detected in Docker/WSL
    },
    proxy: {
      'api/': {
        target: 'https://localhost:8000',    // Forward /api requests to Django backend
        changeOrigin: true,                  // Rewrite Host header for backend compatibility
        secure: false                        // Allow self‑signed SSL certs (mkcert)
      }
    },
    https: {
      key: fs.readFileSync('../certs/localhost-key.pem'), // SSL private key
      cert: fs.readFileSync('../certs/localhost.pem')     // SSL certificate
    }
  }
})
