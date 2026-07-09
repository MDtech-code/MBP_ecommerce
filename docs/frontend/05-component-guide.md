# Component Architecture & UI Guide

This document maps out the entire presentation layer of the BikeExpress frontend. It outlines how layout shells, route pages, and domain-specific sub-components collaborate to build the user interface.

---

## The UI Hierarchy Pattern

To prevent components from becoming bloated and deeply nested, the UI follows a strict three-tier structural chain:

```text
[ 1. Layout Shell ] ──► Establishes global grids, navbars, sidebars, and route guarding.
        │
        ▼ Houses via <Outlet /> or {children}
[ 2. Page View ]    ──► Acts as the route entry point. Consumes data hooks and passes props.
        │
        ▼ Houses
[ 3. Sub-Component] ──► Isolated UI pieces (Forms, Modals, Product Cards).
```

---

## 1. Global & Common Components (`src/components/`)

These are the highly reusable building blocks that span across multiple domains.

### Common (`src/components/common/`)
* **`Container.jsx`:** A max-width constraint wrapper (`max-w-360 px-4 sm:px-6 lg:px-10`) used to keep content aligned globally.
* **`FormInput.jsx`:** The standardized input field used everywhere. Handles its own password visibility toggle (`Eye`/`EyeOff`) and displays validation errors.
* **`SearchBar.jsx`:** A responsive search component. Renders as a full bar on desktop and collapses into a clickable icon/dropdown on mobile.
* **`Pagination.jsx`:** Standardized pagination controls for product listings.
* **`Portal.jsx`:** Wraps React's `createPortal` to render modals (like `AvatarModal`) at the root DOM level to prevent z-index clipping issues.

### Layout (`src/components/layout/`)
* **`MainLayout.jsx`:** The wrapper for public-facing storefront pages. Renders the global `Navbar` and `Footer`.
* **`Navbar.jsx`:** Orchestrates the top navigation by combining `TopBar` (trust signals), `MainNavbar` (links, search, user dropdown, cart), and `MobileMenu` (hamburger drawer).
* **`ProtectedRoute.jsx`:** A React Router wrapper that checks `useAuthStore`. If the user lacks an auth token or fails the bootstrap check, it intercepts the route and forces a redirect to `/login`.

---

## 2. Storefront Domains (`src/pages/` & Domain Components)

### The Home Page (`src/pages/Home.jsx`)
* **`Hero.jsx` / `HeroBenefits.jsx`:** The top landing banner with the primary CTA and horizontal trust signals (Original parts, Cash on Delivery, etc.).
* **`CategorySlider.jsx` / `CategoryCard.jsx`:** An interactive horizontal scroll of bike part categories.

### Product Listing (`src/pages/products/ProductListing.jsx`)
* **`ProductSidebar.jsx`:** The left-hand filtering column (Categories, Brands, Price Range, Bike Model).
* **`ProductGrid.jsx` / `ProductCard.jsx`:** Iterates through product data to render individual cards showing price, discount badges, and "Add to Cart" actions.
* **`ProductToolbar.jsx`:** The top bar above the grid for sorting (Price Low to High, Newest, etc.).

### Product Detail (`src/pages/products/ProductDetail.jsx`)
* **`ProductGallery.jsx`:** Handles main product image viewing and thumbnail selection.
* **`ProductInfo.jsx`:** Displays title, brand, rating, pricing, and stock availability.
* **`ProductActions.jsx`:** Manages local quantity state (`+` / `-`) and dispatches "Add to Cart" actions.
* **`ProductTabs.jsx`:** Toggles between Description, Specifications, Reviews, and Compatibility views.

---

## 3. Cart & Checkout (`src/pages/cart/CartPage.jsx`)

The cart page is built from modular blocks inside `src/components/cart/`:
* **`CartList.jsx` / `CartItem.jsx`:** Renders the table of selected products. Handles quantity increases/decreases and line-item removals.
* **`CartSummary.jsx`:** Calculates and displays the subtotal, shipping, discounts, and final total, alongside the "Proceed to Checkout" button.
* **`CartTrust.jsx`:** Horizontal grid of trust badges specifically placed below the cart to reduce cart abandonment.
* **`YouMayAlsoLike.jsx`:** A localized product grid suggesting related items based on cart contents.

---

## 4. Authentication & Account (`src/pages/account/`)

This domain handles user identity, security, and profile management.

### Layout Shells (`src/components/account/`)
* **`AuthLayout.jsx`:** Visual shell for public auth pages (Login/Register). Features a dark background and a split-screen layout on desktop.
* **`DashboardLayout.jsx`:** The secure wrapper for user pages. Renders `AccountHeader` and `AccountSidebar`.

### Auth Pages (Public)
* **`Login.jsx` & `Register.jsx`:** Consume their respective form hooks, capture credentials, and map errors.
* **`VerifyEmail.jsx`:** Consumes `useVerifyEmailPage`. Checks URL parameters for tokens to auto-verify, or allows the user to resend the email manually.
* **`ForgotPassword.jsx` & `ResetPassword.jsx`:** Handle password recovery flows.

### Dashboard Pages (Secure)
* **`Profile.jsx`:** Acts as an orchestrator. Uses `useProfile` to fetch data, then uses local state to toggle between:
  * `<ProfileView />`: Read-only data display.
  * `<ProfileEditForm />`: Form to mutate phone, DOB, and gender.
  * `<AvatarModal />`: React Portal for uploading images.
  * `<AddressManager />`: Toggles the `<AddressCard />` grid and `<AddressForm />`.
* **`Security.jsx` & `ChangePassword.jsx`:** Houses the `<SecurityGrid />` navigation and the password update form, featuring the real-time `<PasswordStrength />` indicator.

---

## Core Rules for UI Development

To prevent architectural degradation, strictly follow these rules when editing or creating components:

1. ❌ **No Inline Axios Calls:** Never use `api.post` or `api.get` directly inside a component file. Data fetching and mutations must happen inside `src/hooks/`.
2. ❌ **No Context/Token Management in UI:** UI files should never import `setAuthToken` or directly read `localStorage` for security purposes. Rely entirely on `useAuthStore` and mutation hooks.
3. ✅ **Smart Pages, Dumb Components:** Keep business logic inside Page files or Custom Hooks. Pass data down to Sub-components (like `ProductCard` or `ProfileInfoRow`) purely via props.
4. ✅ **Use Common Components:** Do not rebuild inputs, buttons, or search bars from scratch. Always utilize the existing assets in `src/components/common/` to ensure visual consistency across the app.