# Frontend Architecture & Knowledge Base

This document serves as the persistent knowledge base for this frontend codebase. It outlines the architectural decisions, structural patterns, and implementation statuses based on the Feature-Sliced Design (FSD) methodology. 

## 1. Project Architecture — FSD (Feature-Sliced Design)

The repository strictly follows the Feature-Sliced Design (FSD) pattern. The folder structure is segmented into specific layers, each with distinct responsibilities and strict cross-layer import rules.

### Directory Structure & Responsibilities

*   **`app/` (Layer 1)**: Global application configuration. Contains initialization logic (`App.jsx`, `main.jsx`), global styles (`index.css`), routing definitions (`providers/router.jsx`), authentication guards (`GuestRoute.jsx`, `ProtectedRoute.jsx`), session bootstrap logic (`useBootstrapAuth.js`), and top-level layout shells (`MainLayout.jsx`, `DashboardLayout.jsx`).
*   **`pages/` (Layer 2)**: Route-level components mapping directly to application URLs. Pages compose multiple widgets and features but contain minimal local business logic (e.g., `HomePage.jsx`, `ProductDetailPage.jsx`, `SecurityPage.jsx`).
*   **`widgets/` (Layer 3)**: Complex, standalone UI blocks that compose features and entities into cohesive sections. Examples include `Header`, `Footer`, `AccountSidebar`, `ProductGrid`, and `CartList`.
*   **`features/` (Layer 4)**: User interactions and business operations (mostly mutations). This includes forms and state-changing actions (e.g., `address` forms/mutations, `auth` forms, `cart` mutations like add/remove).
*   **`entities/` (Layer 5)**: Business domains providing read-only logic and display components. This layer owns the data models, Zustand stores, read-only queries (`use*Queries.js`), and dumb UI components (`CartItem.jsx`, `ProductCard.jsx`, `ProfileView.jsx`).
*   **`shared/` (Layer 6)**: Highly reusable, domain-agnostic infrastructure. Contains API clients (`client.js`), base UI components (`Button`, `FormField`), constants, and utility functions (`authToken.js`, `queryClient.js`).

### Dependency Rules
*   **Strict unidirectional imports**: A layer can only import from layers below it. `pages` can import `widgets`, `features`, `entities`, and `shared`. `entities` can only import `shared`.
*   **Cross-slice restrictions**: Slices within the same layer (e.g., `entities/cart` and `entities/product`) should generally avoid importing each other to prevent circular dependencies.

---

## 2. Workflow Mapping

FSD scatters workflows across domains. Here is the exact mapping for key application flows.

### Account Workflow (Registration, Login, Session)
*   **UI/Routing**: `pages/login/ui/LoginPage.jsx` handles the view. Routed under `<GuestRoute/>` in `app/providers/router.jsx`.
*   **Forms & Logic**: `features/auth/model/useLoginForm.js` coordinates validation and submission.
*   **State & Storage**: `entities/user/model/authStore.js` manages the local session (Zustand). In-memory access token is handled by `shared/lib/authToken.js`.
*   **Session Hydration**: Managed globally by `app/providers/useBootstrapAuth.js` which blocks the UI rendering while refreshing the session token on load.
*   **API Client**: Requests are routed through `shared/api/services/accountService.js`.

### Product Workflow (Listing, Detail)
*   **Routing**: `/product` routes to `ProductListingPage.jsx` and `/product/:slug` routes to `ProductDetailPage.jsx`.
*   **Data Fetching**: Pure query hooks in `entities/product/api/useProductQueries.js` handle fetching (`useProducts`, `useProductDetail`, `useCategoriesTree`).
*   **Dumb UI (Entities)**: Display components like `ProductCard.jsx`, `ProductGallery.jsx`, `ProductInfo.jsx`, and `ProductTabs.jsx` render the data.
*   **Smart UI (Widgets)**: `widgets/product/ui/ProductGrid.jsx` and `RelatedProducts.jsx` compose the product entities into larger blocks.

### Cart Workflow
*   **Routing**: `/cart` is a protected route utilizing `<ProtectedRoute/>` mapping to `pages/cart/ui/CartPage.jsx`.
*   **Data Fetching**: `entities/cart/api/useCartQueries.js` tracks the user's cart state with a short `staleTime` of 30 seconds.
*   **Mutations (Features)**: `features/cart/api/useCartMutations.js` handles adding/removing items.
*   **UI Elements**: `widgets/cart/ui/CartList.jsx` composes `entities/cart/ui/CartItem.jsx` (which is hardcoded to render prices and sub-totals fetched directly from backend decimal responses to avoid frontend float drift).

---

## 3. API Integration Layer

### Client Configuration
*   **Client**: The HTTP client is configured in `shared/api/client.js` with interceptors loaded via `setupInterceptors()` (`shared/api/interceptors.js`) on app initialization in `main.jsx`.
*   **Data Standardization**: API outputs are strictly extracted based on a backend envelope shape: `{ success, message, data, errors, meta }`. Errors are normalized into field errors and non-field errors (`createFieldErrorResponse`, `createNonFieldErrorResponse`).

### Tokens and Refresh Interceptor Logic
*   **Storage**: Access tokens are kept purely in-memory via closure/module variables (`shared/lib/authToken.js`). Refresh tokens are handled via HTTP-only cookies securely managed by the backend.
*   **Bootstrap**: On page load, `useBootstrapAuth.js` executes `accountService.bootstrap()` (which hits `/api/accounts/token/refresh/`). If successful, it receives a new access token, writes it to memory, and proceeds to fetch the user profile (`accountService.getProfile()`) before unlocking the UI.
*   **Refresh Failure**: If the refresh token fails (expired/invalid), the request silently resolves but leaves the user unauthenticated. The `ProtectedRoute` logic then catches the missing auth state and redirects to `/login`.

### API Modules
*   **Centralized**: Service modules are centralized inside `shared/api/services/` (`accountService.js`, `cartService.js`, `productService.js`). 

---

## 4. TanStack Query Usage Patterns

### Configuration
*   **Client Setup**: Defined in `shared/lib/queryClient.js`. For testing environments, queries and mutations are configured with `retry: false` and `gcTime: 0` (`wrappers.jsx`).

### Structure & Conventions
*   **Entities vs. Features**: Data fetching logic (GET) lives in `entities/*/api/use*Queries.js`. Data modification logic (POST/PUT/DELETE) lives in `features/*/api/use*Mutations.js`.
*   **Query Keys**: Strict array-based naming conventions. Keys include parameterized filters to ensure automatic cache segregation:
    *   `["cart"]`
    *   `["categories", "tree"]`
    *   `["products", filters]`
    *   `["product", slug]`
    *   `["account", "profile"]`
*   **Caching Strategy**: `staleTime` is finely tuned per domain:
    *   Cart: 30 seconds (highly volatile).
    *   Products list: 2 minutes.
    *   Categories/Brands: 10 minutes.
*   **Invalidation**: Mutations trigger refetches via `queryClient.invalidateQueries`. For example, `useCreateAddress` invalidates `["account", "profile"]` so the nested user address list updates instantly.
*   **State Handling**: UI states are driven by standard TanStack booleans (`isPending`, `isError`). Form validation heavily uses custom `normalizeError` helpers to extract field-level errors (e.g., in `useAddressForm.js`).

---

## 5. Zustand State Management Patterns

The codebase deliberately minimizes global state, preferring React Query for server data. Zustand is exclusively used for core user session coordination.

### `authStore` (`entities/user/model/authStore.js`)
*   **Purpose**: Single source of truth for client authentication status and base user profile.
*   **State Shape**:
    *   `user`: Object containing core profile data or null.
    *   `isAuthenticated`: Boolean tracking active session.
    *   `isBootstrapping`: Boolean (initially `true`) preventing route checks until token hydration finishes.
*   **Actions**: Standard actions mapped inside the store (`login`, `logout`, `setUser`, `setBootstrapping`). `logout()` explicitly invokes `queryClient.clear()` to wipe server data memory.
*   **Middleware**: Uses standard `create()`. It does **not** use `persist` middleware, ensuring secure handling of token restoration via HTTP-only cookies on reload.

---

## 6. Routing Structure

### Definitions
Defined in `app/providers/router.jsx` using `react-router-dom`'s `createBrowserRouter`. 

### Route Types & Guards
*   **Public Routes**: Wrapped in `MainLayout` (contains standard Header/Footer). Includes `/`, `/product`, `/product/:slug`.
*   **Guest Routes**: Protected by `<GuestRoute/>`. Contains auth workflows (`/login`, `/register`, `/forgot-password`). If an authenticated user hits these, they are redirected to `/`.
*   **Protected Routes**: Wrapped by `<ProtectedRoute/>` which ensures `isAuthenticated` is true after `isBootstrapping` completes. Redirects unauthenticated users to `/login`.
*   **Nested Protected Layouts**: Routes like `/profile`, `/security`, and `/security/verify` are deeply nested inside `<ProtectedRoute/>` -> `<DashboardLayout/>` -> `<Outlet/>` to manage complex authenticated dashboard structures.

---

## 7. Current Feature Completion Status

### Fully Implemented
*   **Account/Auth**: Registration, login, logout, password resets, secure session bootstrapping, and full MSW test coverage.
*   **Address Management**: Full CRUD implemented. Custom form hooks map postal codes dynamically based on Pakistan cities (e.g., `Lahore: 54000`). Handled via nested profile invalidations.
*   **Routing Infrastructure**: All FSD layout wrappers and security guards are operational.

### Partially Implemented / Stubs
*   **Product Detail**: Core UI (`ProductGallery`, `ProductInfo`) is built. However:
    *   Reviews are mocked with `DUMMY_RATING` and `DUMMY_REVIEWS = 0`.
    *   Certain product attributes (`Material`, `Weight`) are mocked as "Not Provided" pending backend data model updates.
*   **Cart Flow**: Addition/removal API hooks and UI (`CartItem.jsx`, `useCartMutations.js`) are built. *Note: Actual checkout/payment flow is not visible in the current router setup.*
*   **Security Settings**: Heavy route scaffolding exists for Change Email/Password and OTP systems under `/security/*`, utilizing robust nested FSD structures.

---

## 8. Backend Contract Summary (Frontend Perspective)

The frontend expects a strict JSON envelope for all successful and failed responses:
```json
{
  "success": boolean,
  "message": string | null,
  "data": object | array | null,
  "errors": {
    "code": string,
    "fields": object | null,
    "non_fields": object | null
  },
  "meta": object | null
}