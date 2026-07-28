# BikeExpress Frontend — Architecture Context for LLM Sessions

> Feed this file at the start of every new chat session.
> It covers the complete mental model of how this frontend works.
> Read everything before writing a single line of code or suggestion.

---

## Project Stack

- **React 18** + **Vite**
- **Tailwind CSS v4** — CSS-first config, `@import "tailwindcss"` + `@theme {}` in `index.css`, NO `tailwind.config.js`
- **Zustand** — client state (auth, UI)
- **React Query (@tanstack/react-query)** — server state (all API data)
- **Axios** — HTTP client with custom instance + interceptors
- **React Router v6** — nested layout routing
- **FSD (Feature-Sliced Design)** architecture

---

## Architecture — FSD Layer Rules

```
src/
├── app/           ← App entry, router, providers, layouts, guards
├── pages/         ← Route-level page components (thin, compose features)
├── widgets/       ← Self-contained UI blocks (Header, Sidebar, AuthBrand)
├── features/      ← User interactions (useLoginForm, SocialLogin)
├── entities/      ← Domain models + their stores (user/authStore)
├── shared/        ← Reusable primitives (ui/, api/, lib/)
```

**Import direction is strictly top-down:**
`app → pages → widgets → features → entities → shared`
No layer imports from a layer above it. Ever.

---

## Color System — Tailwind v4 (`index.css`)

```css
@theme {
  --color-primary: #DC2626;   /* red — buttons, active states, highlights */
  --color-dark:    #020202;   /* near-black — text, dark backgrounds */
  --color-surface: #F8FAFC;   /* off-white — page backgrounds */
  --color-muted:   #64748B;   /* gray — secondary text, placeholders */
  --font-sans: Inter, Arial, sans-serif;
}
```

**Rules:**
- Use only these custom colors + standard Tailwind gray/white/black scale
- No hardcoded hex values in components except `bg-[#070707]` in AuthLayout (intentional dark background)
- `dark:` variants used only where explicitly noted below

---

## Layout System — Three Layouts

### 1. `AuthLayout` — Guest-only auth pages
**Routes:** `/login`, `/register`, `/verify-email`, `/forgot-password`, `/forgot-password/sent`, `/reset-password`

**Structure:**
- Wrapped in `GuestRoute` guard → authenticated users redirect to `/`
- Full-screen layout with motorcycle background image + gradient overlay
- **Desktop (lg+):** Split layout — left branding panel + right white card
- **Tablet (md–lg):** Centered floating card with dark header strip showing logo
- **Mobile (<md):** Dark top bar with logo + condensed brand line, white sheet rises from bottom with `rounded-t-3xl`
- Brand text per route driven by `authBrandConfig.js` keyed by `pathname`
- `<Outlet />` renders the actual form page inside the white card area

**Key files:**
```
src/app/layouts/AuthLayout.jsx
src/app/layouts/authBrandConfig.js
src/widgets/auth/ui/AuthBrand.jsx
```

### 2. `RootLayout` — Public + protected customer pages
**Routes:** `/`, `/product`, `/product/:slug`, `/cart`

**Structure:**
- Contains main `Header` (logo, search, user icon, cart badge, burger)
- Contains `Footer`
- `<Outlet />` renders page content between them
- Cart page is inside `ProtectedRoute` nested under this layout

### 3. `DashboardLayout` — Customer account pages
**Routes:** `/profile`, `/security`, `/security/*`

**Structure:**
- Nested under `ProtectedRoute` inside `RootLayout`
- **Desktop (lg+):** Permanent left sidebar (`w-64`) + main content area
- **Mobile (<lg):** Sidebar hidden, replaced by `MobileAccountNav` — horizontal scrollable pill tabs sticky below main header
- NO drawer, NO burger, NO duplicate header — this was intentionally removed
- `<Outlet />` renders account page content

**Key files:**
```
src/app/layouts/DashboardLayout.jsx
src/widgets/sidebar/ui/DashboardSidebar.jsx
src/widgets/sidebar/ui/MobileAccountNav.jsx
```

---

## Route Guards

### `ProtectedRoute`
```jsx
// Checks isBootstrapping first — never makes redirect while session is restoring
// If bootstrapping → return null (render nothing, wait)
// If not authenticated → Navigate to /login with { state: { from: location } }
// If authenticated → <Outlet />
```

### `GuestRoute`
```jsx
// Checks isBootstrapping first — same reason
// If bootstrapping → return null
// If authenticated → Navigate to /
// If not authenticated → <Outlet />
```

**Critical rule:** Both guards check `isBootstrapping` before `isAuthenticated`.
Without this, guards make redirect decisions before the session is restored on page refresh — causing race conditions and false logouts.

---

## Auth State — Zustand Store

**File:** `src/entities/user/model/authStore.js`
**Slice file:** `src/entities/user/model/slices/authSlice.js`

### Store shape
```javascript
{
  user: null,             // full user object from backend profile response
  isAuthenticated: false, // boolean — single source of truth for auth status
  isBootstrapping: true,  // true while session restore is in progress
}
```

### Actions

**`login(data)`**
- Called after successful POST `/api/accounts/login/`
- `data.access` → token, `data.user` → user object
- Calls `setAuthToken(data.access)` — puts token in memory + sets axios header
- Calls `broadcastLogin()` — syncs other tabs
- Sets `user` and `isAuthenticated: true` in store

**`logout()`**
- **Order is critical — must follow this exact sequence:**
  1. `sessionStorage.setItem("logged_out", "true")` ← FIRST, before anything fires
  2. `queryClient.cancelQueries()` — cancel in-flight requests
  3. `queryClient.clear()` — wipe React Query cache
  4. `clearAuth()` — remove token from memory + axios header
  5. `broadcastLogout()` — notify other tabs
  6. `set({ user: null, isAuthenticated: false })`
- Deviation from this order causes the mystery refresh-after-logout bug

**`setUser(user)`**
- Called after profile fetch during bootstrap
- Sets `user` + `isAuthenticated: true` without touching token

**`setBootstrapping(value)`**
- Sets `isBootstrapping` to true or false
- Called by `useBootstrapAuth` when session restore completes

### Middleware stack
```javascript
create(
  devtools(
    subscribeWithSelector(
      immer((set, get) => ({ ...createAuthSlice(set, get) }))
    ),
    { name: "UserStore" }
  )
)
```

### Reading store in components — selector pattern
```javascript
// CORRECT — component only re-renders when this specific value changes
const user = useAuthStore((state) => state.user)
const isAuthenticated = useAuthStore((state) => state.isAuthenticated)

// WRONG — re-renders on any store change, kills performance
const { user, isAuthenticated } = useAuthStore()
```

### Reading store outside React (interceptors, utils)
```javascript
useAuthStore.getState().logout()   // call actions
useAuthStore.getState().user       // read state
```

---

## Token Management — `authToken.js`

**File:** `src/shared/lib/authToken.js`

```
accessToken  →  lives in module-level memory variable (NOT localStorage, NOT sessionStorage)
               cleared on page refresh — bootstrap restores it from HttpOnly cookie
```

**Functions:**
- `setAuthToken(token)` — stores token in memory + sets `Authorization: Bearer` header on axios instance
- `getAuthToken()` — returns raw token string
- `hasAuthToken()` → `!!accessToken` — boolean, used in guards
- `clearAuth()` — nulls memory token + removes Authorization header
- `broadcastLogin()` — writes `{ type: "LOGIN", time }` to localStorage `auth_event` key
- `broadcastLogout()` — writes `{ type: "LOGOUT", time }` to localStorage `auth_event` key

---

## Bootstrap — Session Restore on Page Refresh

**File:** `src/app/providers/useBootstrapAuth.js`

**Purpose:** On every page load, access tokens are gone from memory (they don't persist). Bootstrap silently restores the session using the HttpOnly refresh cookie.

**Flow:**
```
App mounts → isBootstrapping: true → loading screen shown
  ↓
useBootstrapAuth runs (useEffect, empty deps, runs once)
  ↓
Check 1: isAuthenticated already? → setBootstrapping(false), return
Check 2: sessionStorage logged_out === "true"? → setBootstrapping(false), return (skip network)
Check 3: hasAttempted.current? → return (prevents StrictMode double-fire)
  ↓
POST /api/accounts/token/refresh/ (sends HttpOnly cookie automatically)
  ↓
Success: setAuthToken(newToken) → GET /api/accounts/profile/ → setUser(data)
Failure: silent catch — user stays unauthenticated (normal for guests)
  ↓
finally: setBootstrapping(false) → loading screen removed → router renders
```

**Why `sessionStorage.getItem("logged_out")`:**
- Set on logout to prevent bootstrap from firing a pointless refresh call
- Scoped to tab — each tab has its own flag
- Cleared by `initAuthSync` when a LOGIN event arrives from another tab

---

## Multi-Tab Sync — `initAuthSync.js`

**File:** `src/shared/lib/initAuthSync.js`

**How it works:**
- `window.addEventListener("storage", handler)` fires ONLY in OTHER tabs, not the originating tab
- On `LOGOUT` event: set `sessionStorage.logged_out=true` → `clearAuth()` → `window.location.href="/login"`
- On `LOGIN` event: `sessionStorage.removeItem("logged_out")` → `window.location.href="/"`

**Why sessionStorage flag must be set inside the LOGOUT handler:**
The flag is tab-scoped. When Tab A logs out, it sets its own flag. Tab B receives the storage event and must set ITS OWN flag before reloading — otherwise Tab B's bootstrap runs with no flag and fires the refresh endpoint against a blacklisted token.

---

## Axios Interceptors — `interceptors.js`

**File:** `src/shared/api/interceptors.js`

### Request interceptor
Reads `getAuthToken()` and attaches `Authorization: Bearer <token>` to every request.

### Response interceptor — 401 handling
When a 401 is received, the interceptor attempts silent token refresh UNLESS:
```javascript
// All conditions must be true to attempt refresh:
status === 401
&& !originalRequest._retry                          // not already retried
&& !url.includes("/api/accounts/token/refresh/")   // not the refresh endpoint itself
&& errorCode !== "invalid_credentials"              // not a bad login attempt
&& sessionStorage.getItem("logged_out") !== "true" // user didn't explicitly log out
```

**Queue pattern:** If a refresh is already in progress, subsequent 401s are queued and resolved/rejected when the refresh completes. This prevents multiple simultaneous refresh calls (race condition on token expiry).

**On refresh success:** New token set, queued requests retried with new token.

**On refresh failure:** `useAuthStore.getState().logout()` called — store cleared, user redirected.

### Other status handling
- **429** — logs retry-after header, rejects
- **500+** — logs server error, rejects

---

## Error Handling — `transformers.js`

**File:** `src/shared/api/transformers.js`

This is the single most important file for understanding how errors flow through the frontend.

### Backend envelope contract
Every response (success AND error) follows this shape:
```javascript
{
  success: boolean,
  message: string | null,
  data:    any,
  errors: {
    code:       string,        // top-level category (e.g. "validation_error")
    fields: {                  // field-level errors, null if none
      [fieldName]: { message: string, code: string }
    } | null,
    non_fields: {              // cross-field / domain / system errors
      category: "validation" | "domain" | "system" | "unexpected",
      message:  string,
      code:     string,        // specific code (e.g. "email_not_verified")
      extra:    object | null  // structured hints from backend (e.g. retry_after)
    } | null
  } | null,
  meta: { request_id: string, ...pagination } | null
}
```

### `ErrorCode` object
Mirror of backend `apps/core/error_codes.py`. **Never hardcode error code strings anywhere — always use this object.**

```javascript
ErrorCode.INVALID_CREDENTIALS       // "invalid_credentials"
ErrorCode.EMAIL_NOT_VERIFIED        // "email_not_verified"
ErrorCode.OTP_INVALID               // "otp_invalid"
ErrorCode.CONFLICT_ERROR            // "conflict_error"
// ... see full file for complete list
```

### `extractResponse(axiosResponse)` — success path
```javascript
// Use this in every service function on the happy path
const response = await api.post("/api/.../", payload)
return extractResponse(response)
// Returns: { data, message, meta }
```

### `normalizeError(rawAxiosError)` — error path
```javascript
const normalized = normalizeError(error)

// Always available:
normalized.message          // human-readable string, never undefined
normalized.status           // HTTP status code or null (network error)
normalized.errors           // full errors envelope or null
normalized.errors?.code     // top-level category code
normalized.errors?.fields   // field dict or null
normalized.errors?.non_fields // { category, message, code, extra } or null

// Convenience boolean flags:
normalized.isNetworkError   // no response at all
normalized.isServerError    // 5xx
normalized.isClientError    // 4xx
normalized.isAuthError      // 401
normalized.isForbidden      // 403
normalized.isNotFound       // 404
normalized.isConflict       // 409
normalized.isRateLimit      // 429
```

### Convenience helpers
```javascript
extractFieldErrors(normalized)    // → fields dict or null
extractNonFieldError(normalized)  // → non_fields object or null
isDomainError(normalized)         // → boolean (business rule violation)
isSystemError(normalized)         // → boolean (infrastructure failure)
```

### How errors flow in practice
```javascript
// In a custom hook (e.g. useLoginForm):
const mutation = useMutation({
  mutationFn: (data) => accountService.login(data),
  onError: (error) => {
    const normalized = normalizeError(error)
    const fields = extractFieldErrors(normalized)
    const nonField = extractNonFieldError(normalized)

    // Field errors → show under each input
    if (fields?.email) setFieldError("email", fields.email.message)

    // Non-field error → show banner
    if (nonField) {
      setFormError(nonField.message)
      setFormErrorCode(nonField.code)  // e.g. ErrorCode.EMAIL_NOT_VERIFIED
    }
  }
})
```

### UI branching decision guide
```
errors.code === VALIDATION_ERROR   → show field errors / inline messages
errors.code === CONFLICT_ERROR     → show informative message (state conflict)
errors.code === AUTHENTICATION_ERROR → redirect to login
non_fields.category === "domain"   → business rule blocked, show reason
non_fields.category === "system"   → "try again later"
non_fields.category === "unexpected" → "something went wrong, contact support"
isNetworkError                     → "check your connection"
isRateLimit                        → show retry countdown from non_fields.extra.retry_after
```

---

## Pagination — `Pagination.jsx`

**File:** `src/shared/ui/Pagination.jsx`

**Design:** Purely display component — owns zero state. All pagination state lives in the URL via `searchParams`.

**Props — driven entirely by backend `meta` object:**
```javascript
{
  currentPage:  meta.page,
  totalPages:   meta.total_pages,
  hasNext:      meta.has_next,
  hasPrevious:  meta.has_previous,
  onPageChange: (page) => void   // from useProductList.setPage or equivalent
}
```

**Page window logic:**
- Shows up to 5 page buttons centered around `currentPage`
- Shows ellipsis + last page button when pages exist beyond the window
- Prev/Next disabled at boundaries via `hasPrevious`/`hasNext`
- Returns `null` when `totalPages <= 1` — renders nothing

**Usage pattern:**
```jsx
<Pagination
  currentPage={meta.page}
  totalPages={meta.total_pages}
  hasNext={meta.has_next}
  hasPrevious={meta.has_previous}
  onPageChange={setPage}
/>
```

**Scroll behavior:** Automatically scrolls to top on page change via `window.scrollTo({ top: 0, behavior: "smooth" })`.

---

## React Query Configuration

**File:** `src/shared/lib/queryClient.js`

```javascript
defaultOptions: {
  queries: {
    staleTime: 1000 * 60 * 5,     // 5 min — no refetch if data is fresh
    gcTime:    1000 * 60 * 10,    // 10 min — keep inactive cache
    retry: (failureCount, error) => {
      if (normalized.isClientError) return false   // 4xx — never retry
      if (normalized.isNetworkError) return failureCount < 3
      return failureCount < 2                      // 5xx — retry twice
    },
    refetchOnWindowFocus: false,
    throwOnError: false,
  },
  mutations: {
    retry: false,  // never auto-retry mutations — side effects are dangerous
  }
}
```

---

## Critical Rules for Any LLM Working on This Codebase

1. **Never import from a higher FSD layer** — shared cannot import from features, entities cannot import from widgets, etc.



5. **Always use `ErrorCode.*` constants** — never hardcode error code strings like `"email_not_verified"` directly.

6. **Always use selector pattern with Zustand** — `useAuthStore((state) => state.user)` not `useAuthStore().user`.

7. **The logout action order is sacred** — sessionStorage flag first, cancel queries second, clear cache third, clearAuth fourth, broadcast fifth, set store last. Any deviation recreates the post-logout refresh bug.

8. **Tailwind v4 only** — no `tailwind.config.js` references, no `@tailwind base/components/utilities` directives, use `@theme {}` for custom values.

9. **`isBootstrapping` check before `isAuthenticated` in every guard** — without this, guards redirect before session is restored.

10. **`extractResponse()` on every successful API call, `normalizeError()` on every error** — never inspect raw axios responses or errors directly.