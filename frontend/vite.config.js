import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true
    },
    https: {
      key: fs.readFileSync('../certs/localhost-key.pem'),
      cert: fs.readFileSync('../certs/localhost.pem')
    }
  }
})
