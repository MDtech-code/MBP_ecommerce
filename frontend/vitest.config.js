import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { aliases } from "./config/aliases";

// No dev-server TLS, proxy or Tailwind bootstrapping needed by the test runner.
export default defineConfig({
  plugins: [react()],
  resolve: { alias: aliases },
  test: {
    globals: true,
    environment: "jsdom",
    environmentOptions: { jsdom: { url: "https://shop.example.test/" } },
    setupFiles: ["./src/app/config/test/setup.js"],
    include: ["src/**/*.test.{js,jsx}"],
    clearMocks: true,
    coverage: {
      provider: "v8",
      reporter: ["text", "json-summary", "html"],
      // Scoped to the explicitly listed shared foundations, not the whole app.
      thresholds: { perFile: true, statements: 90, branches: 90, functions: 90, lines: 90 },
      include: [
        "src/shared/lib/validators/*.js",
        "src/shared/lib/cookies.js",
        "src/shared/api/transformers.js",
        "src/shared/api/csrf.js",
        "src/shared/ui/useCountdown.js",
        "src/shared/ui/FormInput/FormInput.jsx",
      ],
      exclude: ["**/*.test.*", "**/index.js"],
    },
  },
});
