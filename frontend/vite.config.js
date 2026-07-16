import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import process from "process";
import tailwindcss from "@tailwindcss/vite";

//* Resolve the absolute directory of vite.config.js
const __dirname = path.dirname(fileURLToPath(import.meta.url));
console.log(__dirname);

//* Detect if certs folder exists inside Docker container (/app/certs)
const isDocker = fs.existsSync("/app/certs");
console.log("isDocker =", isDocker);

//* Choose certs directory: use /app/certs in Docker, fallback to local ../certs
const certsDir = isDocker ? "/app/certs" : path.resolve(__dirname, "../certs");

//* Configure HTTPS only if cert files exist, otherwise disable HTTPS
const httpsConfig = fs.existsSync(`${certsDir}/localhost-key.pem`)
  ? {
      key: fs.readFileSync(`${certsDir}/localhost-key.pem`),
      cert: fs.readFileSync(`${certsDir}/localhost.pem`),
    }
  : false;

export default defineConfig(({ mode }) => {
  //* Load environment variables based on mode (local, docker, etc.)
  const env = loadEnv(mode, process.cwd(), "");

  const apiTarget = env.VITE_API_ORIGIN;
  console.log("apiTarget =", apiTarget);

  return {
    plugins: [react(), tailwindcss()],

    // ── Path Aliases ────────────────────────────────────────────────────────
    // FSD layer aliases — import from layer root, never from internal paths.
    //
    // CORRECT:   import { useLoginForm } from '@features/auth'
    // INCORRECT: import { useLoginForm } from '@features/auth/model/useLoginForm'
    //
    // Every slice exposes a public index.js barrel — import from that only.
    resolve: {
      alias: {
        "@app": path.resolve(__dirname, "src/app"),
        "@pages": path.resolve(__dirname, "src/pages"),
        "@widgets": path.resolve(__dirname, "src/widgets"),
        "@features": path.resolve(__dirname, "src/features"),
        "@entities": path.resolve(__dirname, "src/entities"),
        "@shared": path.resolve(__dirname, "src/shared"),
      },
    },

    // ── Test Configuration ──────────────────────────────────────────────────
    test: {
      globals: true,
      environment: "jsdom",

      // Points to NEW location after Phase 2 moves setup.js to app/config/test/
      // During Phase 1 (right now) this still points to old location.
      // We update this path when we execute the setup.js move in Phase 2.
      setupFiles: "./src/test/setup.js",
    },

    // ── Dev Server ──────────────────────────────────────────────────────────
    server: {
      host: "0.0.0.0",
      port: 5173,
      hmr: { clientPort: 5173 },
      watch: { usePolling: true },
      https: httpsConfig,
      proxy: {
        "/api": {
          target: apiTarget,
          changeOrigin: true,
          secure: true,
        },
      },
    },
  };
});
// import { defineConfig,loadEnv } from 'vite'
// import react from '@vitejs/plugin-react'
// import fs from 'fs'
// import path from 'path'
// import { fileURLToPath } from 'url'
// import process from 'process'
// import tailwindcss from '@tailwindcss/vite'

// //* Resolve the absolute directory of vite.config.js
// const __dirname = path.dirname(fileURLToPath(import.meta.url))
// console.log(__dirname)

// //* Detect if certs folder exists inside Docker container (/app/certs)
// const isDocker = fs.existsSync('/app/certs')
// console.log('isDocker =', isDocker)

// //* Choose certs directory: use /app/certs in Docker, fallback to local ../certs when running outside
// const certsDir = isDocker
//   ? '/app/certs'
//   : path.resolve(__dirname, '../certs')

// //* Configure HTTPS only if cert files exist, otherwise disable HTTPS
// const httpsConfig = fs.existsSync(`${certsDir}/localhost-key.pem`)
//   ? {
//     key: fs.readFileSync(`${certsDir}/localhost-key.pem`),
//     cert: fs.readFileSync(`${certsDir}/localhost.pem`)
//   }
//   : false

// export default defineConfig(({ mode }) => {
//   //* Load environment variables based on mode (local, docker, etc.)
//   const env = loadEnv(mode, process.cwd(), '')

//   const apiTarget = env.VITE_API_ORIGIN
//   console.log('apiTarget =',apiTarget)

//   return {
//     plugins: [react(),tailwindcss()],

//     test: {
//       globals: true,
//       environment: 'jsdom',
//       setupFiles: './src/test/setup.js',
//     },

//     server: {
//       host: '0.0.0.0',
//       port: 5173,
//       hmr: { clientPort: 5173 },
//       watch: { usePolling: true },
//       https: httpsConfig,
//       proxy: {
//         '/api': {
//           target: apiTarget,
//           changeOrigin: true,
//           secure: true
//         }
//       }
//     }
//   }
// })
