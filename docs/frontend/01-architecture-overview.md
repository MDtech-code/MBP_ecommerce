# Frontend Architecture Overview

**Project:** MBP E-Commerce (BikeExpress)
**Stack:** React 19, Vite 8, React Router 7, Tailwind v4, DaisyUI v5
**State Management:** TanStack Query v5 (Server), Zustand v5 (Client)

This document outlines the core architectural philosophy of the BikeExpress frontend. To maintain a clean, scalable, and bug-free codebase, this project strictly adheres to a **4-Layer Architecture**. 

---

## The 4-Layer Architecture

The codebase is divided into four distinct layers. Data and imports flow strictly *downward*. UI components should never directly interact with the infrastructure layer.

### Layer 1: Infrastructure (`src/api/`)
This is the foundational layer that talks to the outside world (the Django backend). It knows nothing about the UI or business logic.
* **`client.js`:** The core Axios instance with base URLs and default headers.
* **`auth.js` / `authSync.js`:** Manages the JWT access token in raw JS memory and syncs login/logout events across browser tabs.
* **`interceptors.js`:** The traffic cop. Automatically intercepts 401 Unauthorized errors to silently refresh tokens, and catches 429 Rate Limits or 500 Server Errors.
* **`transformers.js`:** Normalizes all incoming data and errors. It unwraps the strict backend envelope (`{ success, message, data, errors, meta }`) so the rest of the app doesn't have to.

### Layer 2: Endpoint Knowledge (`src/services/`)
This layer contains functions that map exactly to backend API endpoints. 
* **Rule:** Service functions (e.g., `accountService.js`) only take payloads, make the Axios call, pass the result through the transformer, and return the clean data. 
* **Rule:** Never catch errors here. Let them bubble up to the hooks.

### Layer 3: Business Logic (`src/hooks/`)
This is the brain of the frontend. It bridges the Services layer with the UI layer.
* **Mutation/Query Hooks (e.g., `useAuthMutations.js`):** Wraps TanStack React Query. This is where side effects happen (e.g., on a successful login, set the auth token and update the global store).
* **Form Hooks (e.g., `useLoginForm.js`):** Manages local form state, extracts field-specific errors from the normalized backend response, and handles post-submission navigation.

### Layer 4: Presentation / UI (`src/pages/`, `src/components/`)
The dumbest layer by design. 
* **Rule:** Pages and components should contain **zero** direct API calls and minimal business logic. 
* They import a hook (like `useLoginForm`), destructure what they need (`form`, `fieldErrors`, `handleSubmit`), and return pure JSX. 

---

## Strict Import Rules

To prevent circular dependencies and mental loops, follow these import rules:

✅ **Pages** can import from: `hooks/`, `stores/`, `components/`, `react-router-dom`
✅ **Hooks** can import from: `services/`, `api/transformers.js`, `stores/`
✅ **Services** can import from: `api/client.js`, `api/transformers.js`

❌ **NEVER** import a Service directly into a Page (always use a Hook).
❌ **NEVER** import `api/client.js` directly into a Page or Hook.
❌ **NEVER** import a Hook into a Service.

---

## State Management Philosophy

We maintain a strict boundary between server data and client data to prevent state synchronization bugs.

### 1. Server State (TanStack Query)
* **Used for:** Products, cart data, user profile data, orders.
* **Why:** Data that lives on the Django server. React Query handles caching, loading states, background refetching, and deduplication automatically. 

### 2. Global Client State (Zustand)
* **Used for:** `authStore` (Authentication state).
* **Why:** Data that the client strictly owns across the entire app session (e.g., "Is the user logged in right now?"). 
* **Rule:** Never duplicate React Query cache data into Zustand.

### 3. Local State (`useState`)
* **Used for:** Form inputs, modal toggles, dropdown open/closed states.
* **Why:** Ephemeral data that only matters to a single component and doesn't need to survive navigation.