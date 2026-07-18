// src/app/providers/index.jsx
//
// Composes all global providers for the application.
// Import order matters:
//   QueryClientProvider must wrap everything that uses React Query.
//   RouterProvider must be inside QueryClientProvider so route
//   components can use queries directly.
//
// Add new providers here — never in App.jsx or main.jsx directly.

export { default } from './router.jsx'