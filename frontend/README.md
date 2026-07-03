# MBP E-Commerce — Frontend Architecture Guide

> Version: 1.0
> Last Updated: During accounts app integration
> Purpose: Complete reference for any developer (or AI assistant) working
>          on this frontend. Read entirely before making any changes.

---

## Table of Contents

1. Project Overview
2. Tech Stack
3. Environment Setup
4. Folder Structure
5. The 4-Layer Architecture
6. Import Rules
7. State Management
8. API Response Contract
9. transformers.js Contract
10. Auth Architecture
11. Adding a New Feature — Step by Step
12. Testing
13. Routing
14. Naming Conventions
15. Development Workflow
16. Common Mistakes to Avoid
17. Current Progress

---

## 1. Project Overview

MBP is a full-stack e-commerce platform for bikes and bike accessories.

- Backend: Django + Django REST Framework (complete)
- Frontend: React 19 + Vite 8
- All backend APIs are REST, standardized, production-complete
- Frontend goal: integrate cleanly without breaking backend contract
- UI/UX design is ~90% complete — do not modify visual design without reason

---

## 2. Tech Stack

| Tool                    | Version | Purpose                              |
|-------------------------|---------|--------------------------------------|
| React                   | 19      | UI framework                         |
| Vite                    | 8       | Build tool + dev server              |
| React Router            | 7       | Client-side routing                  |
| TanStack Query          | 5       | Server state + async data management |
| Zustand                 | latest  | Client state (auth only currently)   |
| Axios                   | 1.x     | HTTP client                          |
| Tailwind CSS            | 4       | Utility-first styling                |
| DaisyUI                 | 5       | Component theme layer over Tailwind  |
| Apollo Client           | 4       | GraphQL (specific use only — not     |
|                         |         | used for general data fetching)      |
| Lucide React            | latest  | Icon library                         |
| Vitest                  | latest  | Unit + integration testing           |
| Testing Library         | latest  | Component testing utilities          |

---

## 3. Environment Setup

### Local Development
```bash
npm run dev
# Reads: .env
# VITE_API_ORIGIN=https://localhost:8000


frontend/
├── public/
├── src/
│   │
│   ├── api/                        # INFRASTRUCTURE LAYER
│   │   ├── client.js               # Axios instance — baseURL, default headers
│   │   ├── auth.js                 # Access token in memory — get/set/clear
│   │   ├── authSync.js             # Cross-tab login/logout sync
│   │   ├── interceptors.js         # 401 refresh, 429 rate limit, 500 logging
│   │   └── transformers.js         # Envelope unwrap + error normalize
│   │
│   ├── lib/
│   │   └── queryClient.js          # TanStack QueryClient — global config
│   │
│   ├── services/                   # ENDPOINT KNOWLEDGE LAYER
│   │   └── accountService.js       # All HTTP calls for /api/accounts/
│   │
│   ├── hooks/                      # BUSINESS LOGIC LAYER
│   │   └── account/
│   │       ├── useAuthMutations.js # TanStack mutations: useLogin, useRegister, useLogout
│   │       └── useRegisterForm.js  # Form state + errors + submit for Register page
│   │
│   ├── stores/                     # CLIENT STATE
│   │   └── authStore.js            # Zustand: { user, isAuthenticated, login, logout }
│   │
│   ├── components/                 # SHARED UI COMPONENTS
│   │   ├── account/                # Auth layout components
│   │   │   ├── AuthLayout.jsx      # Wrapper for all auth pages
│   │   │   └── AuthBrand.jsx       # Left column branding
│   │   ├── common/                 # Truly reusable across whole app
│   │   │   └── FormInput.jsx       # Input with icon, password toggle, error display
│   │   ├── home/                   # Home page specific components
│   │   └── layout/                 # Navbar, Footer, Logo
│   │
│   ├── pages/                      # UI LAYER — zero business logic
│   │   ├── account/
│   │   │   ├── Register.jsx
│   │   │   ├── Login.jsx
│   │   │   ├── VerifyEmail.jsx
│   │   │   ├── ForgotPassword.jsx
│   │   │   └── ResetPassword.jsx
│   │   ├── products/
│   │   │   ├── ProductListing.jsx
│   │   │   └── ProductDetail.jsx
│   │   └── cart/
│   │       └── CartPage.jsx
│   │
│   ├── routes/
│   │   └── index.jsx               # React Router config
│   │
│   ├── test/                       # All test files
│   │   ├── setup.js                # Vitest + Testing Library setup
│   │   ├── api/                    # Tests for transformers, interceptors
│   │   ├── hooks/                  # Tests for form hooks and mutations
│   │   └── pages/                  # Component integration tests
│   │
│   ├── assets/
│   │   └── images/
│   ├── index.css                   # Tailwind import + @theme tokens
│   └── main.jsx                    # App entry point
│
├── index.html
├── vite.config.js
├── tailwind.config.js
├── FRONTEND_ARCHITECTURE.md        # This file
└── package.json


USER ACTION
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 4 — src/pages/*           UI ONLY               │
│                                                         │
│  What the user sees and interacts with.                 │
│  Imports ONE form hook. Destructures. Renders JSX.      │
│  Zero business logic. Zero API calls. Zero token work.  │
└────────────────────────┬────────────────────────────────┘
                         │ imports
                         ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 3 — src/hooks/*           BUSINESS LOGIC        │
│                                                         │
│  Two types of hooks:                                    │
│                                                         │
│  Mutation hooks (useAuthMutations.js):                  │
│    Wraps TanStack useMutation                           │
│    onSuccess: setAuthToken, broadcastLogin,             │
│               queryClient.clear, update Zustand store   │
│    onError: force logout if needed                      │
│                                                         │
│  Form hooks (useRegisterForm.js):                       │
│    Owns form state (useState)                           │
│    Calls mutation hook internally                       │
│    Extracts field errors from normalizeError()          │
│    Handles navigation after success                     │
│    Returns clean object for component to destructure    │
└────────────────────────┬────────────────────────────────┘
                         │ imports
                         ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 2 — src/services/*        ENDPOINT KNOWLEDGE    │
│                                                         │
│  Knows exact URLs, HTTP methods, request body shape.    │
│  Calls api.post/get/put/delete from client.js           │
│  Always calls extractResponse() before returning        │
│  Never catches errors — bubbles to TanStack Query       │
│  Never imports hooks, components, or stores             │
└────────────────────────┬────────────────────────────────┘
                         │ imports
                         ▼
┌─────────────────────────────────────────────────────────┐
│  LAYER 1 — src/api/*             INFRASTRUCTURE        │
│                                                         │
│  client.js:       axios instance, baseURL, headers      │
│  auth.js:         access token in JS memory             │
│  authSync.js:     cross-tab sync via storage events     │
│  interceptors.js: 401 refresh queue, 429, 500 logging   │
│  transformers.js: extractResponse + normalizeError      │
│                                                         │
│  These files do not know about any feature.             │
│  They are never imported directly in components.        │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
                  DJANGO BACKEND
          { success, message, data, errors, meta }




pages         can import from:
                hooks/*, stores/*, components/*, react-router-dom
                api/transformers (normalizeError only if not in form hook)

hooks         can import from:
                services/*, api/auth.js, api/transformers.js,
                stores/*, lib/queryClient.js, react-router-dom

services      can import from:
                api/client.js, api/transformers.js

api/*         imports nothing from your own codebase
              (only axios, external libraries)

stores/*      can import from:
                api/auth.js, lib/queryClient.js



✗ Page imports from services directly     → skips hook, loses business logic
✗ Page imports from api/client directly   → bypasses interceptors
✗ Hook imports from pages                 → circular dependency
✗ Service imports from hooks              → circular dependency
✗ Store contains data from React Query    → two sources of truth
✗ Any file imports from api/interceptors  → interceptors self-register in main.jsx



┌──────────────────────────────────────────────────────────────┐
│  REACT QUERY — Server State                                  │
│                                                              │
│  Products, cart contents, orders, user profile, search       │
│  Anything that comes FROM the server                         │
│  Has loading / error / refetch lifecycle                     │
│  Automatically cached, deduplicated, synchronized            │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  ZUSTAND — Client State                                      │
│                                                              │
│  authStore:                                                  │
│    user object (name, email, avatar)                         │
│    isAuthenticated boolean                                   │
│    login() action                                            │
│    logout() action                                           │
│                                                              │
│  Only add new Zustand stores when you have state that:       │
│    - Is NOT from the server                                  │
│    - Is shared across 3+ unrelated components                │
│    - Needs to survive navigation                             │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  useState — Local State                                      │
│                                                              │
│  Form inputs, modal open/closed, accordion expanded          │
│  Anything local to ONE component only                        │
│  Does not need to survive navigation                         │
└──────────────────────────────────────────────────────────────┘


Never put server response data into Zustand
Never manage auth token in React Query
Never use useState for data shared across pages
Never duplicate React Query cache in any other state system



{
  "success": true,
  "message": "Human readable summary",
  "data": {},
  "errors": null,
  "meta": {
    "request_id": "uuid-here"
  }
}
src/test/
├── setup.js                # Vitest globals + Testing Library matchers
├── api/
│   ├── transformers.test.js # extractResponse and normalizeError unit tests
│   └── interceptors.test.js # 401 refresh flow tests
├── hooks/
│   └── account/
│       ├── useAuthMutations.test.js
│       └── useRegisterForm.test.js
└── pages/
    └── account/
        └── Register.test.jsx


✅ api/client.js                          Axios instance
✅ api/auth.js                            Token memory management
✅ api/authSync.js                        Cross-tab sync
✅ api/interceptors.js                    401 refresh + 429 + 500
✅ api/transformers.js                    extractResponse + normalizeError
✅ lib/queryClient.js                     Global QueryClient config
✅ services/accountService.js             register endpoint
✅ hooks/account/useAuthMutations.js      useRegister mutation
✅ hooks/account/useRegisterForm.js       Register form logic
✅ pages/account/Register.jsx             Fully connected to backend
✅ components/common/FormInput.jsx        name + error props added
✅ components/account/AuthLayout.jsx      Auth page wrapper
✅ routes/index.jsx                       Typo fixed (forgot-password)