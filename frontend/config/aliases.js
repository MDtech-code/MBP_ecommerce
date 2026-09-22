import { fileURLToPath } from "node:url";

// Shared by Vite and Vitest: test imports must resolve exactly like the app.
export const aliases = Object.fromEntries(
  ["app", "pages", "widgets", "features", "entities", "shared"].map((layer) => [
    `@${layer}`, fileURLToPath(new URL(`../src/${layer}`, import.meta.url)),
  ]),
);
