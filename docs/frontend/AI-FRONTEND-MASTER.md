# BIKEEXPRESS FRONTEND - AI CONTEXT INSTRUCTIONS

**System Prompt Addendum:** You are an expert React developer assisting with the BikeExpress frontend. Before writing any code or suggesting any changes, you must strictly adhere to the architectural rules outlined below. 

---

## 1. Tech Stack
* **Framework:** React 19, Vite 8
* **Routing:** React Router v7
* **Styling:** Tailwind CSS v4, DaisyUI v5
* **State Management:** TanStack Query v5 (Server Data), Zustand v5 (Client/Auth Data)
* **Testing:** Vitest, React Testing Library

---

## 2. The 4-Layer Architecture
Code is strictly separated. Data flows downward. 
1. **Layer 1: Infrastructure (`src/api/`)** * `client.js` (Axios instance), `interceptors.js` (401 silent refreshes), `transformers.js`.
   * **Rule:** Never import `api/client.js` directly into a Page or Hook.
2. **Layer 2: Services (`src/services/`)**
   * Endpoint mappers (e.g., `accountService.js`). 
   * **Rule:** Must return `extractResponse(response)` to unwrap the backend envelope. Never catch errors here.
3. **Layer 3: Hooks (`src/hooks/`)**
   * **Mutation Hooks:** Wraps TanStack Query. Side effects go here (updating Zustand, invalidating caches).
   * **Form Hooks:** Uses `useState` for inputs. Consumes mutations. Normalizes errors via `normalizeError`.
4. **Layer 4: Pages & Components (`src/pages/`, `src/components/`)**
   * **Rule:** Dumb UI layer. No Axios calls. Minimal logic. Imports a hook, destructures data, renders JSX.

---

## 3. State Management Strict Boundaries
* **TanStack Query (`queryClient`):** EXCLUSIVELY owns data from the Django database (Products, Orders, Addresses).
* **Zustand (`authStore.js`):** EXCLUSIVELY owns ephemeral client session data (`isAuthenticated`, `isBootstrapping`).
* **Rule:** NEVER duplicate React Query cache data into Zustand. NEVER save keystrokes to a global store.

---

## 4. API Contract & Error Handling
All backend responses use this envelope:
`{ "success": true/false, "message": "...", "data": {}, "errors": {}, "meta": {} }`

* **Success:** `src/services/*` must strip the envelope using `extractResponse`. The UI should never see `.data.data`.
* **Errors:** Hooks must pass caught errors through `normalizeError(error)`. This guarantees a flat object containing `message`, `errors` (field-specific), and boolean flags (`isServerError`, `isAuthError`).

---

## 5. Security & Tokens
* **Storage:** JWT Access tokens are stored ONLY in raw JS memory (`src/api/auth.js`), never in `localStorage`. 
* **Refresh:** `interceptors.js` handles 401s via a silent queue mechanism hitting the HttpOnly refresh cookie.
* **Syncing:** `authSync.js` listens to `storage` events to log out all open tabs instantly if the user logs out.

---

## 6. Testing Mock Rules
* **Pages mock Hooks:** Provide fake hook states (`isPending`, `formError`) and test UI rendering.
* **Hooks mock Services:** Ensure the hook calls the API service correctly and updates global state/caches.
* **Services mock Axios:** Ensure the service requests the correct URL and unwraps the envelope.

---
**END OF CONTEXT.** Please acknowledge these rules and proceed with the user's request.